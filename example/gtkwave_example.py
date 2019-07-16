import os
import tempfile
import pyverilator
import warnings

# open up a temporary directory and change the current directory to it
with tempfile.TemporaryDirectory() as tempdir:
    os.chdir(tempdir)

    test_verilog = '''
        module pipelined_mac (
                CLK,
                rst_n,
                in_a,
                in_b,
                enable,
                clear,
                out);
            input        CLK;
            input        rst_n;
            input [15:0] in_a;
            input [15:0] in_b;
            input        enable;
            input        clear;
            output [31:0] out;

            reg [15:0] operand_a;
            reg [15:0] operand_b;
            reg        operands_valid;

            reg [31:0] mul_result;
            reg        mul_result_valid;

            reg [31:0] accumulator;

            always @(posedge CLK) begin
                if (rst_n == 0) begin
                    operands_valid <= 0;
                    mul_result_valid <= 0;
                    accumulator <= 0;
                end else begin
                    if (clear) begin
                        operands_valid <= 0;
                        mul_result_valid <= 0;
                        accumulator <= 0;
                    end else begin
                        operands_valid <= enable;
                        mul_result_valid <= operands_valid;

                        if (enable) begin
                            operand_a <= in_a;
                            operand_b <= in_b;
                            operands_valid <= 1;
                        end else begin
                            operands_valid <= 0;
                        end

                        if (operands_valid) begin
                            mul_result <= operand_a * operand_b;
                            mul_result_valid <= 1;
                        end else begin
                            mul_result_valid <= 0;
                        end

                        if (mul_result_valid) begin
                            accumulator <= accumulator + mul_result;
                        end
                    end
                end
            end

            assign out = accumulator;
        endmodule'''
    # write test verilog file
    with open('pipelined_mac.v', 'w') as f:
        f.write(test_verilog)
    sim = pyverilator.PyVerilator.build('pipelined_mac.v')

    # get the full signal names for registers of interest
    signals_of_interest = ['operand_a', 'operand_b', 'operands_valid', 'mul_result', 'mul_result_valid', 'accumulator']
    signals_of_interest_verilator_names = []
    for interesting_sig in signals_of_interest:
        for internal_sig, width in sim.internal_signals:
            if interesting_sig in internal_sig:
                signals_of_interest_verilator_names.append(internal_sig)
                break
    io_of_interest = [x[0] for x in sim.inputs + sim.outputs]

    # setup a few functions
    def tick_clock():
        sim['CLK'] = 0
        sim['CLK'] = 1

    def reset():
        sim['rst_n'] = 0
        tick_clock()
        sim['rst_n'] = 1
        sim['enable'] = 0
        sim['clear'] = 0

    def input_and_tick_clock( a, b ):
        sim['in_a'] = a
        sim['in_b'] = b
        sim['enable'] = 1
        sim['clear'] = 0
        tick_clock()
        sim['enable'] = 0

    def clear_and_tick_clock():
        sim['enable'] = 0
        sim['clear'] = 1
        tick_clock()
        sim['clear'] = 0

    sim.start_vcd_trace('test.vcd')

    sim.start_gtkwave()
    sim.send_signals_to_gtkwave(signals_of_interest_verilator_names + io_of_interest)

    reset()

    commands = ['tick_clock()',
                'tick_clock()',
                'tick_clock()',
                'input_and_tick_clock(1, 1)',
                'tick_clock()',
                'tick_clock()',
                'input_and_tick_clock(1, 1)',
                'tick_clock()',
                'tick_clock()',
                'input_and_tick_clock(1, 1)',
                'input_and_tick_clock(1, 1)',
                'input_and_tick_clock(1, 1)',
                'tick_clock()',
                'tick_clock()',
                'clear_and_tick_clock()',
                'input_and_tick_clock(2, 2)',
                'input_and_tick_clock(3, -1)',
                'input_and_tick_clock(3, 3)',
                'input_and_tick_clock(-2, 2)',
                'input_and_tick_clock(4, 3)',
                'input_and_tick_clock(-2, -1)',
                'input_and_tick_clock(-3, -2)',
                'input_and_tick_clock(3, -7)',
                'tick_clock()',
                'tick_clock()']

    # gtkwave writes to stderr when vcd files are reloaded, so this ignores the
    # corresponding warning from tclwrapper
    warnings.filterwarnings('ignore', r'.*\[[0-9]*\] start time.*')

    print('Press enter to simulate entering a command (there are %d commands in this demo)' % len(commands))
    for c in commands:
        # wait for enter
        input()
        print('>> ' + c, end = '')
        eval(c)
    # wait for enter one last time
    input()
    print('Done! Closing GTKWave...')

    sim.stop_gtkwave()

    sim.stop_vcd_trace()
