def header_cpp(top_module):
    s = """#include <cstddef>
#include "verilated.h"
#include "verilated_vcd_c.h"
#include "{module_filename}.h"
    """.format(module_filename='V' + top_module)
    return s


def var_declaration_cpp(top_module, inputs, outputs, internal_signals, json_data):
    s = """// pyverilator defined values
// first declare variables as extern
extern const char* _pyverilator_module_name;
extern const uint32_t _pyverilator_num_inputs;
extern const char* _pyverilator_inputs[];
extern const uint32_t _pyverilator_input_widths[];
extern const uint32_t _pyverilator_num_outputs;
extern const char* _pyverilator_outputs[];
extern const uint32_t _pyverilator_output_widths[];
extern const uint32_t _pyverilator_num_internal_signals;
extern const char* _pyverilator_internal_signals[];
extern const uint32_t _pyverilator_internal_signal_widths[];
extern const uint32_t _pyverilator_num_rules;
extern const char* _pyverilator_rules[];
extern const char* _pyverilator_json_data;
// now initialize the variables
const char* _pyverilator_module_name = "{module_filename}";
const uint32_t _pyverilator_num_inputs = {nb_inputs};
const char* _pyverilator_inputs[] = {{{name_inputs}}};
const uint32_t _pyverilator_input_widths[] = {{{size_inputs}}};

const uint32_t _pyverilator_num_outputs = {nb_outputs};
const char* _pyverilator_outputs[] = {{{name_outputs}}};
const uint32_t _pyverilator_output_widths[] = {{{size_outputs}}};

const uint32_t _pyverilator_num_internal_signals = {nb_internals};
const char* _pyverilator_internal_signals[] = {{{name_internals}}};
const uint32_t _pyverilator_internal_signal_widths[] = {{{size_internals}}};

const char* _pyverilator_json_data = {json_data};

// this is required by verilator for verilog designs using $time
// main_time is incremented in eval
double main_time = 0;
    """.format(
        module_filename='V' + top_module,
        nb_inputs=len(inputs),
        name_inputs=",".join(map(lambda input: '"' + input[0] + '"', inputs)),
        size_inputs=",".join(map(lambda input: str(input[1]), inputs)),
        nb_outputs=len(outputs),
        name_outputs=",".join(map(lambda output: '"' + output[0] + '"', outputs)),
        size_outputs=",".join(map(lambda output: str(output[1]), outputs)),
        nb_internals=len(internal_signals),
        name_internals=",".join(map(lambda internal: '"' + internal[0] + '"', internal_signals)),
        size_internals=",".join(map(lambda internal: str(internal[1]), internal_signals)),
        json_data=json_data if json_data else "null")
    return s


def function_definitions_cpp(top_module, inputs, outputs, internal_signals, json_data):
    constant_part = """double sc_time_stamp() {{
return main_time;
}}
// function definitions
// helper functions for basic verilator tasks
extern "C" {{ //Open an extern C closed in the footer
{module_filename}* construct() {{
    Verilated::commandArgs(0, (const char**) nullptr);
    Verilated::traceEverOn(true);
    {module_filename}* top = new {module_filename}();
    return top;
}}
int eval({module_filename}* top) {{
    top->eval();
    main_time++;
    return 0;
}}
int destruct({module_filename}* top) {{
    if (top != nullptr) {{
        delete top;
        top = nullptr;
    }}
    return 0;
}}
VerilatedVcdC* start_vcd_trace({module_filename}* top, const char* filename) {{
    VerilatedVcdC* tfp = new VerilatedVcdC;
    top->trace(tfp, 99);
    tfp->open(filename);
    return tfp;
}}
int add_to_vcd_trace(VerilatedVcdC* tfp, int time) {{
    tfp->dump(time);
    return 0;
}}
int flush_vcd_trace(VerilatedVcdC* tfp) {{
    tfp->flush();
    return 0;
}}
int stop_vcd_trace(VerilatedVcdC* tfp) {{
    tfp->close();
    return 0;
}}""".format(module_filename='V' + top_module)
    get_functions = "\n".join(map(lambda port: (
        "uint32_t get_{portname}({module_filename}* top, int word)"
        "{{ return top->{portname}[word];}}" if port[1] > 64 else (
            "uint64_t get_{portname}({module_filename}* top)"
            "{{return top->{portname};}}" if port[1] > 32 else
            "uint32_t get_{portname}({module_filename}* top)"
            "{{return top->{portname};}}")).format(module_filename='V' + top_module, portname=port[0]),
                                  outputs + inputs + internal_signals))
    set_functions = "\n".join(map(lambda port: (
        "int set_{portname}({module_filename}* top, int word, uint64_t new_value)"
        "{{ top->{portname}[word] = new_value; return 0;}}" if port[1] > 64 else (
            "int set_{portname}({module_filename}* top, uint64_t new_value)"
            "{{ top->{portname} = new_value; return 0;}}" if port[1] > 32 else
            "int set_{portname}({module_filename}* top, uint32_t new_value)"
            "{{ top->{portname} = new_value; return 0;}}")).format(module_filename='V' + top_module, portname=port[0])
                                  , inputs))
    footer = "}"
    return "\n".join([constant_part, get_functions, set_functions, footer])


def template_cpp(top_module, inputs, outputs, internal_signals, json_data):
    return "\n".join([header_cpp(top_module),
                      var_declaration_cpp(top_module, inputs, outputs, internal_signals, json_data),
                      function_definitions_cpp(top_module, inputs, outputs, internal_signals, json_data)])
