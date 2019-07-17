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

    # setup a few functions
    def tick_clock():
        sim.io.CLK = 0
        sim.io.CLK = 1

    def reset():
        sim.io.rst_n = 0
        tick_clock()
        sim.io.rst_n = 1
        sim.io.enable = 0
        sim.io.clear = 0

    def input_and_tick_clock( a, b ):
        sim.io.in_a = a
        sim.io.in_b = b
        sim.io.enable = 1
        sim.io.clear = 0
        tick_clock()
        sim.io.enable = 0

    def clear_and_tick_clock():
        sim.io.enable = 0
        sim.io.clear = 1
        tick_clock()
        sim.io.clear = 0

    sim.start_vcd_trace('test.vcd')

    sim.start_gtkwave()
    sim.send_signals_to_gtkwave(sim.io)
    sim.send_signals_to_gtkwave(sim.internals)

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
