import ctypes
import os
import shutil
import subprocess
import json
import re
import warnings
import pyverilator.verilatorcpp as template_cpp
import tclwrapper

class Collection:
    def __init__(self, items):
        self._item_dict = items
        self._item_dict_keys = list(items.keys())
        self._item_dict_keys.sort()

    def __dir__(self):
        return self._item_dict_keys

    def __getattr__(self, name):
        obj = self._item_dict.get(name)
        if obj is not None:
            return obj
        raise AttributeError("'Collection' object has no attribute '%s'" % name)

    def __getitem__(self, name):
        obj = self._item_dict.get(name)
        if obj is not None:
            return obj
        raise ValueError("'Collection' object has no item '%s'" % name)

    def __setitem__(self, name, value):
        obj = self._item_dict.get(name)
        if obj is not None:
            obj.write(value)
        else:
            raise ValueError('signal "%s" does not exist' % name)

    def __setattr__(self, name, value):
        if name == '_item_dict' or name == '_item_dict_keys':
            super().__setattr__(name, value)
        else:
            obj = self._item_dict.get(name)
            if obj is not None:
                obj.write(value)
            else:
                raise ValueError('signal "%s" does not exist' % name)

    def __iter__(self):
        return iter(self._item_dict.values())

    def __repr__(self):
        num_items = len(self._item_dict_keys)
        if num_items == 0:
            return '<empty Collection object>'
        truncated = num_items > 25
        if truncated:
            keys_to_show = [self._item_dict_keys[i] for i in range(10)]
            keys_to_show = [self._item_dict_keys[i] for i in range(num_items-10, num_items)]
        else:
            keys_to_show = [self._item_dict_keys[i] for i in range(num_items)]
        items_to_show = [self._item_dict[key] for key in keys_to_show]
        column_one = [item.__class__.__name__ for item in items_to_show]
        column_two = keys_to_show
        column_three = [repr(item).split()[-1] if not isinstance(item, Collection) else '' for item in items_to_show]
        column_one_width = max(map(len, column_one))
        column_two_width = max(map(len, column_two))
        column_three_width = max(map(len, column_three))
        ret = ''
        for i in range(num_items):
            if i != 0:
                ret += '\n'
            if truncated and i == 10:
                ret += '    ... %d objects in total ...\n' % num_items
            fmt_string = '{:<' + str(column_one_width) + '}  {:<' + str(column_two_width) + '}  {:>' + str(column_three_width) + '}'
            ret += fmt_string.format(column_one[i], column_two[i], column_three[i])
        return ret

class Signal:
    def __init__(self, pyverilator_sim, verilator_name, width):
        self.sim_object = pyverilator_sim
        self.verilator_name = verilator_name
        self.width = width
        # construct gtkwave_name
        self.gtkwave_name = '.'.join(['TOP'] + verilator_name.split('__DOT__'))
        if width > 1:
            self.gtkwave_name += '[%d:0]' % (width-1)
        # get the function and arguments required for getting the signal's value
        if width <= 32:
            self.value_function_and_args = (self.sim_object._read_32, self.verilator_name)
        elif width <= 64:
            self.value_function_and_args = (self.sim_object._read_64, self.verilator_name)
        else:
            self.value_function_and_args = (self.sim_object._read_words, self.verilator_name, (width + 31) // 32)

    @property
    def value(self):
        # this calls the value function (the 0th element of self.value_function_and_args)
        # with the necessary arguments (the rest of self.value_function_and_args)
        return self.value_function_and_args[0](*self.value_function_and_args[1:])

    def send_to_gtkwave(self):
        self.sim_object.send_signal_to_gtkwave(self.gtkwave_name)

    def __repr__(self):
        # build a sized verilog hex literal
        return self.gtkwave_name.split('.')[-1] + ' = ' + str(self.width) + "'h" + hex(self.value)[2:]

# These classes help improve python error messages
class Output(Signal):
    pass

class InternalSignal(Signal):
    pass

class Input(Signal):
    def __init__(self, pyverilator_sim, verilator_name, width):
        super().__init__(pyverilator_sim, verilator_name, width)
        if width <= 32:
            self.write_function_and_args = (self.sim_object._write_32, self.verilator_name)
        elif width <= 64:
            self.write_function_and_args = (self.sim_object._write_64, self.verilator_name)
        else:
            self.write_function_and_args = (self.sim_object._write_words, self.verilator_name, (width + 31) // 32)

    def write(self, value):
        self.write_function_and_args[0](*self.write_function_and_args[1:], value)

    def __le__(self, rhs):
        self.write(rhs)

class Clock(Input):
    def __init__(self, input_):
        if not isinstance(input_, Input):
            raise TypeError('Clock must be made from an Input')
        if input_.width != 1:
            raise ValueError('Clock must be a 1-bit signal')
        super().__init__(input_.sim_object, input_.verilator_name, input_.width)

    def tick(self):
        self.write(0)
        self.write(1)

class PyVerilator:
    """Python wrapper for verilator model.

        Usage:
            sim = PyVerilator.build('my_verilator_file.v')
            sim.io.a = 2
            sim.io.b = 3
            print('c = ' + sim.io.c)

        By default the object created propagates the signal changes every time the input changes.
        So a clock cycle will be:
            sim.clock = 1
            sim.clock = 0


        Alternatively using the dictionary syntax:
            sim = PyVerilator.build('my_verilator_file.v')
            sim['a'] = 2
            sim['b'] = 3
            print('c = ' + sim['c'])
    """

    default_vcd_filename = 'gtkwave.vcd'

    @classmethod
    def build(cls, top_verilog_file, verilog_path = [], build_dir = 'obj_dir', json_data = None, gen_only = False):
        """ Build an object file from verilog and load it into python.

        Creates a folder build_dir in which it puts all the files necessary to create
        a model of top_verilog_file using verilator and the C compiler. All the files are created in build_dir.

        If the project is made of more than one verilog file, all the files used by the top_verilog_file will be searched
        for in the verilog_path list.

        json_data is a payload than can be used to add a json as a string in the object file compiled by verilator.

        This allow to keep the object file a standalone model even when extra information iis useful to describe the
        model.

        For example a model coming from bluespec will carry the list of rules of the model in this payload.

        gen_only stops the process before compiling the cpp into object.
        """
        # get the module name from the verilog file name
        top_verilog_file_base = os.path.basename(top_verilog_file)
        verilog_module_name, extension = os.path.splitext(top_verilog_file_base)
        if extension != '.v':
            raise ValueError('PyVerilator() expects top_verilog_file to be a verilog file ending in .v')

        # prepare the path for the C++ wrapper file
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)
        verilator_cpp_wrapper_path = os.path.join(build_dir, 'pyverilator_wrapper.cpp')

        # call verilator executable to generate the verilator C++ files
        verilog_path_args = []
        for verilog_dir in verilog_path:
            verilog_path_args += ['-y', verilog_dir]

        # Verilator is a perl program that is run as an executable
        # Old versions of Verilator are interpreted as a perl script by the shell,
        # while more recent versions are interpreted as a bash script that calls perl on itself
        which_verilator = shutil.which('verilator')
        if which_verilator is None:
            raise Exception("'verilator' executable not found")
        # tracing (--trace) is required in order to see internal signals
        verilator_args = ['perl', which_verilator, '-Wno-fatal', '-Mdir', build_dir] \
                         + verilog_path_args \
                         + ['--CFLAGS',
                           '-fPIC --std=c++11',
                            '--trace',
                            '--cc',
                            top_verilog_file,
                            '--exe',
                            verilator_cpp_wrapper_path]
        subprocess.call(verilator_args)

        # get inputs, outputs, and internal signals by parsing the generated verilator output
        inputs = []
        outputs = []
        internal_signals = []
        verilator_h_file = os.path.join(build_dir, 'V' + verilog_module_name + '.h')

        def search_for_signal_decl(signal_type, line):
            # looks for VL_IN*, VL_OUT*, or VL_SIG* macros
            result = re.search('(VL_' + signal_type + r'[^(]*)\(([^,]+),([0-9]+),([0-9]+)(?:,[0-9]+)?\);', line)
            if result:
                signal_name = result.group(2)
                if signal_type == 'SIG':
                    if signal_name.startswith(verilog_module_name) and '[' not in signal_name and int(
                            result.group(4)) == 0:
                        # this is an internal signal
                        signal_width = int(result.group(3)) - int(result.group(4)) + 1
                        return (signal_name, signal_width)
                    else:
                        return None
                else:
                    # this is an input or an output
                    signal_width = int(result.group(3)) - int(result.group(4)) + 1
                    return (signal_name, signal_width)
            else:
                return None

        with open(verilator_h_file) as f:
            for line in f:
                result = search_for_signal_decl('IN', line)
                if result:
                    inputs.append(result)
                result = search_for_signal_decl('OUT', line)
                if result:
                    outputs.append(result)
                result = search_for_signal_decl('SIG', line)
                if result:
                    internal_signals.append(result)

        # generate the C++ wrapper file
        verilator_cpp_wrapper_code = template_cpp.template_cpp(verilog_module_name, inputs, outputs, internal_signals,
                                                               json.dumps(json.dumps(json_data)))
        with open(verilator_cpp_wrapper_path, 'w') as f:
            f.write(verilator_cpp_wrapper_code)

        # if only generating verilator C++ files, stop here
        if gen_only:
            return None

        # call make to build the pyverilator shared object
        make_args = ['make', '-C', build_dir, '-f', 'V%s.mk' % verilog_module_name, 'CFLAGS=-fPIC -shared',
                     'LDFLAGS=-fPIC -shared']
        subprocess.call(make_args)
        so_file = os.path.join(build_dir, 'V' + verilog_module_name)
        return cls(so_file)

    def __init__(self, so_file, auto_eval=True):
        # initialize lib and model first so if __init__ fails, __del__ will
        # not fail.
        self.lib = None
        self.model = None
        self.auto_eval = auto_eval
        # initialize vcd variables
        self.vcd_filename = None
        self.vcd_trace = None
        self.auto_tracing_mode = None
        self.curr_time = 0
        self.vcd_reader = None
        self.gtkwave_active = False
        self.lib = ctypes.CDLL(so_file)
        construct = self.lib.construct
        construct.restype = ctypes.c_void_p
        self.model = construct()
        # get inputs, outputs, internal_signals, and json_data
        self._read_embedded_data()
        self._sim_init()
        # constructor helpers
        self.io = self._construct_io_collection()
        self.internals = self._construct_internal_signal_collection()
        # try to autodetect the clock
        self.clock = None
        # first look for an io with the name clock or clk (ignoring case)
        for sig in self.io:
            if sig.verilator_name.lower() == 'clock' or sig.verilator_name.lower() == 'clk':
                self.clock = Clock(sig)
                break
        # if neither are found, look for names that start with clock or clk
        if self.clock is None:
            for sig in self.io:
                if sig.verilator_name.lower().startswith('clock') or sig.verilator_name.lower().startswith('clk'):
                    self.clock = Clock(sig)
                    break

    def __del__(self):
        if self.model is not None:
            fn = self.lib.destruct
            fn.argtypes = [ctypes.c_void_p]
            fn(self.model)
        if self.lib is not None:
            del self.lib

    def _read_embedded_data(self):
        self.module_name = ctypes.c_char_p.in_dll(self.lib, '_pyverilator_module_name').value.decode('ascii')

        # inputs
        num_inputs = ctypes.c_uint32.in_dll(self.lib, '_pyverilator_num_inputs').value
        input_names = (ctypes.c_char_p * num_inputs).in_dll(self.lib, '_pyverilator_inputs')
        input_widths = (ctypes.c_uint32 * num_inputs).in_dll(self.lib, '_pyverilator_input_widths')
        self.inputs = []
        for i in range(num_inputs):
            self.inputs.append((input_names[i].decode('ascii'), input_widths[i]))

        # outputs
        num_outputs = ctypes.c_uint32.in_dll(self.lib, '_pyverilator_num_outputs').value
        output_names = (ctypes.c_char_p * num_outputs).in_dll(self.lib, '_pyverilator_outputs')
        output_widths = (ctypes.c_uint32 * num_outputs).in_dll(self.lib, '_pyverilator_output_widths')
        self.outputs = []
        for i in range(num_outputs):
            self.outputs.append((output_names[i].decode('ascii'), output_widths[i]))

        # internal signals
        num_internal_signals = ctypes.c_uint32.in_dll(self.lib, '_pyverilator_num_internal_signals').value
        internal_signal_names = (ctypes.c_char_p * num_internal_signals).in_dll(self.lib, '_pyverilator_internal_signals')
        internal_signal_widths = (ctypes.c_uint32 * num_internal_signals).in_dll(self.lib, '_pyverilator_internal_signal_widths')
        self.internal_signals = []
        for i in range(num_internal_signals):
            self.internal_signals.append((internal_signal_names[i].decode('ascii'), internal_signal_widths[i]))

        # json_data
        json_string = ctypes.c_char_p.in_dll(self.lib, '_pyverilator_json_data').value.decode('ascii')
        self.json_data = json.loads(json_string)

    def _construct_io_collection(self):
        signals = {}
        for sig_name, width in self.inputs:
            signals[sig_name] = Input(self, sig_name, width)
        for sig_name, width in self.outputs:
            signals[sig_name] = Output(self, sig_name, width)
        return Collection(signals)

    def _construct_internal_signal_collection(self):
        internal_signal_hierarchy = {}
        for verilator_signal_name, width in self.internal_signals:
            path = verilator_signal_name.split('__DOT__')[1:-1]
            short_name = verilator_signal_name.split('__DOT__')[-1]
            curr_node = internal_signal_hierarchy
            for module in path:
                if module not in curr_node:
                    curr_node[module] = {}
                curr_node = curr_node[module]
            curr_node[short_name] = InternalSignal(self, verilator_signal_name, width)
        def construct_collection(curr_node):
            for key in curr_node:
                if isinstance(curr_node[key], dict):
                    curr_node[key] = construct_collection(curr_node[key])
            return Collection(curr_node)
        return construct_collection(internal_signal_hierarchy)


    def _read(self, port_name):
        port_width = None
        for name, width in self.inputs + self.outputs + self.internal_signals:
            if port_name == name:
                port_width = width
        if port_width is None:
            raise ValueError('cannot read port "%s" because it does not exist' % port_name)
        if port_width > 64:
            num_words = (port_width + 31) // 32
            return self._read_words(port_name, num_words)
        elif port_width > 32:
            return self._read_64(port_name)
        else:
            return self._read_32(port_name)

    def _read_32(self, port_name):
        fn = getattr(self.lib, 'get_' + port_name)
        fn.argtypes = [ctypes.c_void_p]
        fn.restype = ctypes.c_uint32
        return int(fn(self.model))

    def _read_64(self, port_name):
        fn = getattr(self.lib, 'get_' + port_name)
        fn.argtypes = [ctypes.c_void_p]
        fn.restype = ctypes.c_uint64
        return int(fn(self.model))

    def _read_words(self, port_name, num_words):
        fn = getattr(self.lib, 'get_' + port_name)
        fn.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        fn.restype = ctypes.c_uint32
        words = [0] * num_words
        for i in range(num_words):
            words[i] = int(fn(self.model, i))
        out = 0
        for i in range(num_words):
            out |= words[i] << (i * 32)
        return out

    def _write(self, port_name, value):
        port_width = None
        for name, width in self.inputs:
            if port_name == name:
                port_width = width
        if port_width is None:
            raise ValueError('cannot write port "%s" because it does not exist (or it is an output)' % port_name)
        if port_width > 64:
            num_words = (port_width + 31) // 32
            self._write_words(port_name, num_words, value)
        elif port_width > 32:
            self._write_64(port_name, value)
        else:
            self._write_32(port_name, value)

    def _write_32(self, port_name, value):
        fn = getattr(self.lib, 'set_' + port_name)
        fn.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        fn( self.model, ctypes.c_uint32(value) )
        self._post_write_hook(port_name, value)

    def _write_64(self, port_name, value):
        fn = getattr(self.lib, 'set_' + port_name)
        fn.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        fn( self.model, ctypes.c_uint64(value) )
        self._post_write_hook(port_name, value)

    def _write_words(self, port_name, num_words, value):
        fn = getattr(self.lib, 'set_' + port_name)
        fn.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint32]
        for i in range(num_words):
            word = ctypes.c_uint32(value >> (i * 32))
            fn( self.model, i, word )
        self._post_write_hook(port_name, value)

    def _post_write_hook(self, port_name, value):
        if self.auto_eval:
            self.eval()
        if self.auto_tracing_mode == 'clock' and port_name == self.clock.verilator_name:
            self.add_to_vcd_trace()

    def _sim_init(self):
        # initialize all the inputs to 0
        input_names = [name for name, _ in self.inputs]
        for name in input_names:
            self._write(name, 0)

    def __getitem__(self, signal_name):
        return self._read(signal_name)

    def __setitem__(self, signal_name, value):
        self._write(signal_name, value)

    def __contains__(self, signal_name):
        for name, _ in self.inputs + self.outputs + self.internal_signals:
            if name == signal_name:
                return True
        return False

    def eval(self):
        fn = self.lib.eval
        fn.argtypes = [ctypes.c_void_p]
        fn(self.model)
        if self.auto_tracing_mode == 'eval':
            self.add_to_vcd_trace()

    def start_vcd_trace(self, filename, auto_tracing = True):
        if self.vcd_trace is not None:
            raise ValueError('start_vcd_trace() called while VCD tracing is already active')
        start_vcd_trace = self.lib.start_vcd_trace
        start_vcd_trace.restype = ctypes.c_void_p
        self.vcd_trace = start_vcd_trace(self.model, ctypes.c_char_p(filename.encode('ascii')))
        self.vcd_filename = filename

        if not auto_tracing:
            self.auto_tracing_mode = None
        elif self.clock is not None:
            self.auto_tracing_mode = 'clock'
        else:
            self.auto_tracing_mode = 'eval'
        self.curr_time = 0
        # initial vcd data
        self.add_to_vcd_trace()

    def add_to_vcd_trace(self):
        if self.vcd_trace is None:
            raise ValueError('add_to_vcd_trace() requires VCD tracing to be active')
        # do two steps so the most recent value in GTKWave is more obvious
        self.curr_time += 5
        self.lib.add_to_vcd_trace(self.vcd_trace, self.curr_time)
        self.curr_time += 5
        self.lib.add_to_vcd_trace(self.vcd_trace, self.curr_time)
        # go ahead and flush on each vcd update
        self.flush_vcd_trace()

    def flush_vcd_trace(self):
        if self.vcd_trace is None:
            raise ValueError('flush_vcd_trace() requires VCD tracing to be active')
        self.lib.flush_vcd_trace(self.vcd_trace)
        if self.gtkwave_active:
            self.reload_dump_file()

    def stop_vcd_trace(self):
        if self.vcd_trace is None:
            raise ValueError('stop_vcd_trace() requires VCD tracing to be active')
        self.lib.stop_vcd_trace(self.vcd_trace)
        self.vcd_trace = None
        self.auto_tracing_mode = None
        self.vcd_filename = None

    def reload_dump_file(self):
        if self.gtkwave_active:
            # this gets the max time before and after the dump file is reloaded to see if it changed
            old_max_time = float(self.gtkwave_tcl.eval('gtkwave::getMaxTime'))
            self.gtkwave_tcl.eval('gtkwave::reLoadFile')
            new_max_time = float(self.gtkwave_tcl.eval('gtkwave::getMaxTime'))
            if new_max_time > old_max_time:
                # if it changed, see if the window could previously see the last data but not anymore
                window_end_time = float(self.gtkwave_tcl.eval('gtkwave::getWindowEndTime'))
                if window_end_time >= old_max_time and window_end_time < new_max_time:
                    # if so, shift the window start so the new data is shown
                    time_shift_amt = new_max_time - window_end_time
                    window_start_time = float(self.gtkwave_tcl.eval('gtkwave::getWindowStartTime'))
                    self.gtkwave_tcl.eval('gtkwave::setWindowStartTime %d' % (window_start_time + time_shift_amt))

    def start_gtkwave(self):
        if self.vcd_filename is None:
            self.start_vcd_trace(PyVerilator.default_vcd_filename)
        # in preparation for using tclwrapper with gtkwave, add a warning filter
        # to ignore expected messages written to stderr for certain commands
        warnings.filterwarnings('ignore', r".*generated stderr message '\[[0-9]*\] start time.\\n\[[0-9]*\] end time.\\n'")
        self.gtkwave_active = True
        self.gtkwave_tcl = tclwrapper.TCLWrapper('gtkwave', '-W')
        self.gtkwave_tcl.start()
        self.gtkwave_tcl.eval('gtkwave::loadFile %s' % self.vcd_filename)
        # adjust the screen to show more of the trace
        zf = float(self.gtkwave_tcl.eval('gtkwave::getZoomFactor'))
        # this seems to work well
        new_zf = zf - 5
        self.gtkwave_tcl.eval('gtkwave::setZoomFactor %f' % (new_zf))

    def send_signals_to_gtkwave(self, signals_to_add):
        if not self.gtkwave_active:
            raise ValueError('send_signals_to_gtkwave() requires GTKWave to be started using start_gtkwave()')

        # signals_to_add are either Signal objects, gtkwave names, or verilator names
        # they can be passed in as a single item or in an iterable container
        if isinstance(signals_to_add, str) or isinstance(signals_to_add, Signal):
            # only a single object is being added
            signals_to_add = [signals_to_add]
        if not isinstance(signals_to_add, list):
            # convert iterable container to list
            signals_to_add = list(signals_to_add)

        gtkwave_signal_names = []
        for sig in signals_to_add:
            if isinstance(sig, Signal):
                gtkwave_signal_names.append(sig.gtkwave_name)
            elif isinstance(sig, str):
                # assume if the signal name doesn't have a period in it, it is a verilator name
                if '.' not in sig:
                    sig = 'TOP.' + sig.replace('__DOT__','.')
                gtkwave_signal_names.append(sig)
            else:
                raise TypeError("Can't add type \"%s\" to gtkwave" % str(type(sig)))

        # to get all the signal names for debugging:
        # signal_names = tclstring_to_flat_list(self.gtkwave_tcl.eval('''
        # set nfacs [gtkwave::getNumFacs]
        # set signal_names []
        # for {set i 0} {$i < $nfacs} {incr i} {
        #     lappend signal_names [gtkwave::getFacName $i]
        # }
        # puts "$signal_names"
        # '''))

        # find the signals
        num_found_signals = int(self.gtkwave_tcl.eval('''
        set nfacs [gtkwave::getNumFacs]
        set found_signals [list]
        set target_signals {%s}
        for {set i 0} {$i < $nfacs} {incr i} {
            set facname [gtkwave::getFacName $i]
            foreach target_sig $target_signals {
                if {[string first [string tolower $target_sig] [string tolower $facname]] != -1} {

                    lappend found_signals "$facname"
                }
            }
        }
        gtkwave::addSignalsFromList $found_signals
        ''' % ' '.join(gtkwave_signal_names)))

        if num_found_signals < len(gtkwave_signal_names):
            raise ValueError('send_signals_to_gtkwave was only able to send %d of %d signals' % (num_found_signals, len(gtkwave_signal_names)))

    def send_signal_to_gtkwave(self, signal_name):
        if not self.gtkwave_active:
            raise ValueError('send_signal_to_gtkwave() requires GTKWave to be started using start_gtkwave()')
        self.send_signals_to_gtkwave([signal_name])

    def stop_gtkwave(self):
        if not self.gtkwave_active:
            raise ValueError('stop_gtkwave() requires GTKWave to be started using start_gtkwave()')
        self.gtkwave_tcl.stop()
        self.gtkwave_active = False
        if self.vcd_filename == PyVerilator.default_vcd_filename:
            self.stop_vcd_trace()
