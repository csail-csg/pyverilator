import os
import IPython
import pyverilator

# setup build directory and cd to it
build_dir = os.path.join(os.path.dirname(__file__), 'build', os.path.basename(__file__))
os.makedirs(build_dir, exist_ok = True)
os.chdir(build_dir)

test_verilog = '''
    module pipelined_mac (
            clk,
            rst_n,
            in_a,
            in_b,
            enable,
            clear,
            out);
        input        clk;
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

        always @(posedge clk) begin
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

sim.start_gtkwave()

# adding signals to gtkwave:
# 1) signal.io.clk.send_to_gtkwave()
# 2) sim.send_to_gtkwave( signal.io.rst_n )
# 3) for signal in sim.io:
#        sim.io[signal].send_to_gtkwave()
# 4) sim.send_to_gtkwave( sim.io )

sim.send_to_gtkwave( sim.io )

sim.io.rst_n = 0
sim.clock.tick()
sim.io.rst_n = 1

sim.io.in_a = 1
sim.io.in_b = 1
sim.io.enable = 1
sim.io.clear = 0

# open an IPython repl
print('Opening up IPython shell. The PyVerilator object for this example is named "sim".')
IPython.embed()
