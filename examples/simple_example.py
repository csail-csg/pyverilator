import os
import pyverilator

# setup build directory and cd to it
build_dir = os.path.join(os.path.dirname(__file__), 'build', os.path.basename(__file__))
os.makedirs(build_dir, exist_ok = True)
os.chdir(build_dir)

test_verilog = '''
    module counter (
            input        clk,
            input        rst,
            input        en,
            output [7:0] out
        );
        reg [7:0] count_reg;
        wire [7:0] next_count_reg;
        assign next_count_reg = (en == 1) ? count_reg + 1 : count_reg;
        assign out = next_count_reg;
        always @(posedge clk) begin
            if (rst == 1) count_reg <= 0;
            else          count_reg <= next_count_reg;
        end
    endmodule'''

with open('counter.v', 'w') as f:
    f.write(test_verilog)


dump_fst = True
if dump_fst:
    dump_filename = 'dump.fst'
else:
    dump_filename = 'dump.vcd'
sim = pyverilator.PyVerilator.build('counter.v',dump_fst=dump_fst)

# start gtkwave to view the waveforms as they are made
# sim.start_gtkwave() # moved at the bottom... updating gtkwave during simulation is slow
sim.start_vcd_trace(dump_filename)

# add all the io and internal signals to gtkwave
# sim.send_to_gtkwave(sim.io)        # this still works
# sim.send_to_gtkwave(sim.internals) # not working anymore

# set the rst input to 1
sim.io.rst = 1

# tick the automatically detected clock
sim.clock.tick()

sim.io.rst = 0

sim.io.en = 0

curr_out = sim.io.out.value
print('sim.io.out = ' + str(curr_out))

sim.io.en = 1

curr_out = sim.io.out.value
print('sim.io.out = ' + str(curr_out))

sim.clock.tick()

curr_out = sim.io.out.value
print('sim.io.out = ' + str(curr_out))

sim.stop_vcd_trace()
sim.start_gtkwave() # moved at the bottom works both with fst and vcd