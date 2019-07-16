#!/usr/bin/env python3

import ctypes
import os
import shutil
import subprocess
import json
import re
import pyverilator.verilatorcpp as template_cpp
import tclwrapper


class IO:
    """ Exposes the io of the verilator model with standard python syntax:

    sim.io.en_enq
    sim.io.en_enq = 1

    Note: We assume that there is no wires named sim_object
    """
    def __init__(self, pyverilator_sim):
        self.sim_object = pyverilator_sim

    def __dir__(self):
        return map(lambda x: x[0], self.sim_object.inputs + self.sim_object.outputs)
        # Update the dic to show up all the signals

    def __getattr__(self, item):
        if item in map(lambda x: x[0], self.sim_object.inputs + self.sim_object.outputs):
            return self.sim_object[item]
        else:
            raise ValueError('cannot read port "%s" because it is not a bound io' % item)

    def __setattr__(self, key, value):
        if key == 'sim_object':
            super().__setattr__(key, value)
        else:
            if key in map(lambda x: x[0], self.sim_object.inputs):
                self.sim_object[key] = value
            else:
                raise ValueError('cannot write port "%s" because it is not a bound input' % key)


class Internals:
    """ Exposes the internal signals of the verilator model with standard python syntax:

    sim.internals.__T243
    Note: We assume that there is no wires named sim_object
    """
    def __init__(self, pyverilator_sim):
        self.sim_object = pyverilator_sim

    def __dir__(self):
        return map(lambda x: x[0], self.sim_object.internal_signals)

    def __getattr__(self, item):
        if item in map(lambda x: x[0], self.sim_object.internal_signals):
            return self.sim_object[item]
        else:
            raise ValueError('cannot read port "%s" because it is not an internal signal' % item)


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
        # Allow access to the fields directly from
        self.io = IO(self)
        self.internals = Internals(self)

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
        if self.auto_eval:
            self.eval()
        if self.auto_tracing_mode == 'CLK' and port_name == 'CLK':
            self.add_to_vcd_trace()

    def _write_32(self, port_name, value):
        fn = getattr(self.lib, 'set_' + port_name)
        fn.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        fn( self.model, ctypes.c_uint32(value) )

    def _write_64(self, port_name, value):
        fn = getattr(self.lib, 'set_' + port_name)
        fn.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        fn( self.model, ctypes.c_uint64(value) )

    def _write_words(self, port_name, num_words, value):
        fn = getattr(self.lib, 'set_' + port_name)
        fn.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint32]
        for i in range(num_words):
            word = ctypes.c_uint32(value >> (i * 32))
            fn( self.model, i, word )

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
        elif 'CLK' in self:
            self.auto_tracing_mode = 'CLK'
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
        self.gtkwave_active = True
        self.gtkwave_tcl = tclwrapper.TCLWrapper('gtkwave', '-W')
        self.gtkwave_tcl.start()
        self.gtkwave_tcl.eval('gtkwave::loadFile %s' % self.vcd_filename)
        # adjust the screen to show more of the trace
        zf = float(self.gtkwave_tcl.eval('gtkwave::getZoomFactor'))
        # this seems to work well
        new_zf = zf - 5
        self.gtkwave_tcl.eval('gtkwave::setZoomFactor %f' % (new_zf))

    def send_signals_to_gtkwave(self, signal_names):
        if not self.gtkwave_active:
            raise ValueError('send_signals_to_gtkwave() requires GTKWave to be started using start_gtkwave()')
        if not isinstance(signal_names, list):
            signal_names = [signal_names]

        signal_names_gtkwave = list(map( lambda x: 'TOP.' + x.replace('__DOT__','.'), signal_names ))
        signal_names_tclstring = '{%s}' % (' '.join(signal_names_gtkwave))

        # find the signals
        num_found_signals = int(self.gtkwave_tcl.eval('''
        set nfacs [gtkwave::getNumFacs]
        set found_signals [list]
        set target_signals %s
        for {set i 0} {$i < $nfacs} {incr i} {
            set facname [gtkwave::getFacName $i]
            foreach target_sig $target_signals {
                if {[string first [string tolower $target_sig] [string tolower $facname]] != -1} {

                    lappend found_signals "$facname"
                }
            }
        }
        gtkwave::addSignalsFromList $found_signals
        ''' % signal_names_tclstring))

        if num_found_signals < len(signal_names):
            raise ValueError('send_signals_to_gtkwave was only able to send %d of %d signals' % (num_found_signals, len(signal_names)))

    def send_signal_to_gtkwave(self, signal_name):
        if not self.gtkwave_active:
            raise ValueError('send_signal_to_gtkwave() requires GTKWave to be started using start_gtkwave()')
        self.send_signals_to_gtkwave(signal_name)

    def stop_gtkwave(self):
        if not self.gtkwave_active:
            raise ValueError('stop_gtkwave() requires GTKWave to be started using start_gtkwave()')
        self.gtkwave_tcl.stop()
        self.gtkwave_active = False
        if self.vcd_filename == PyVerilator.default_vcd_filename:
            self.stop_vcd_trace()
