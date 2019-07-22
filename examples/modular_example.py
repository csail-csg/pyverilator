import os
import pyverilator

# setup build directory and cd to it
build_dir = os.path.join(os.path.dirname(__file__), 'build', os.path.basename(__file__))
os.makedirs(build_dir, exist_ok = True)
os.chdir(build_dir)

test_verilog = '''
    module parent_module (
            clk,
            rst,
            in,
            out);
        input clk;
        input rst;
        input [7:0] in;
        output [7:0] out;

        wire [7:0] child_2_out;
        wire [7:0] child_1_to_child_2;

        reg [7:0] in_reg;
        reg [7:0] out_reg;

        assign out = out_reg;

        child_module child_1 (clk, rst, in_reg, child_1_to_child_2);
        child_module child_2 (clk, rst, child_1_to_child_2, child_2_out);

        always @(posedge clk) begin
            if (rst == 1) begin
                in_reg <= 0;
                out_reg <= 0;
            end else begin
                in_reg <= in;
                out_reg <= child_2_out;
            end
        end
    endmodule'''
with open('parent_module.v', 'w') as f:
    f.write(test_verilog)

test_verilog = '''
    module child_module (
            clk,
            rst,
            in,
            out);
        input clk;
        input rst;
        input [7:0] in;
        output [7:0] out;

        reg [7:0] in_reg;
        reg [7:0] out_reg;

        assign out = out_reg;

        always @(posedge clk) begin
            if (rst == 1) begin
                in_reg <= 0;
                out_reg <= 0;
            end else begin
                in_reg <= in;
                out_reg <= in_reg + 1;
            end
        end
    endmodule'''
with open('child_module.v', 'w') as f:
    f.write(test_verilog)

sim = pyverilator.PyVerilator.build('parent_module.v')

sim.io.rst = 1
sim.io.clk = 0
sim.io.clk = 1
sim.io.rst = 0

# in is a reserved keyword :(
sim.io['in'] = 7

sim.clock.tick()
sim.clock.tick()
sim.clock.tick()

collections = ['sim.io', 'sim.internals', 'sim.internals.child_1', 'sim.internals.child_2']

print('')
for collection in collections:
    print('>> ' + collection)
    print(eval('repr(' + collection + ')'))
    print('')
