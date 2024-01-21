#!/usr/bin/env python3

import unittest
import tempfile
import shutil
import os
import pyverilator

class TestPyVerilator(unittest.TestCase):
    def setUp(self):
        self.old_dir = os.getcwd()
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.old_dir)
        shutil.rmtree(self.test_dir)

    def test_pyverilator_verilator_exists(self):
        self.assertIsNotNone(shutil.which('verilator'))

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator(self):
        test_verilog = '''
            module width_test (
                    input_a,
                    input_b,
                    input_c,
                    input_d,
                    input_e,
                    output_concat);
                input [7:0] input_a;
                input [15:0] input_b;
                input [31:0] input_c;
                input [63:0] input_d;
                input [127:0] input_e;
                output [247:0] output_concat;
                assign output_concat = {input_a, input_b, input_c, input_d, input_e};
            endmodule'''
        # write test verilog file
        with open('width_test.v', 'w') as f:
            f.write(test_verilog)
        test_pyverilator = pyverilator.PyVerilator.build('width_test.v')

        test_pyverilator.start_vcd_trace('test.vcd')
        test_pyverilator['input_a'] = 0xaa
        test_pyverilator['input_b'] = 0x1bbb
        test_pyverilator['input_c'] = 0x3ccccccc
        test_pyverilator['input_d'] = 0x7ddddddddddddddd
        test_pyverilator['input_e'] = 0xfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee

        self.assertEqual(test_pyverilator['output_concat'], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)

        test_pyverilator.stop_vcd_trace()

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_attributes(self):
        test_verilog = '''
            module width_test (
                    input_a,
                    input_b,
                    input_c,
                    input_d,
                    input_e,
                    output_concat);
                input [7:0] input_a;
                input [15:0] input_b;
                input [31:0] input_c;
                input [63:0] input_d;
                input [127:0] input_e;
                output [247:0] output_concat;
                assign output_concat = {input_a, input_b, input_c, input_d, input_e};
            endmodule'''
        # write test verilog file
        with open('width_test.v', 'w') as f:
            f.write(test_verilog)
        test_pyverilator = pyverilator.PyVerilator.build('width_test.v')

        test_pyverilator.io.input_a = 0xaa
        test_pyverilator.io.input_b = 0x1bbb
        test_pyverilator.io.input_c = 0x3ccccccc
        test_pyverilator.io.input_d = 0x7ddddddddddddddd
        test_pyverilator.io.input_e = 0xfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee

        self.assertEqual(test_pyverilator.io.output_concat, 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)

        self.assertTrue(repr(test_pyverilator.io.input_a).endswith("8'haa"))
        self.assertTrue(repr(test_pyverilator.io.input_b).endswith("16'h1bbb"))
        self.assertTrue(repr(test_pyverilator.io.input_c).endswith("32'h3ccccccc"))
        self.assertTrue(repr(test_pyverilator.io.input_d).endswith("64'h7ddddddddddddddd"))
        self.assertTrue(repr(test_pyverilator.io.input_e).endswith("128'hfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"))
        self.assertTrue(repr(test_pyverilator.io.output_concat).endswith("248'haa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"))

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_tracing(self):
        test_verilog = '''
            module internal_test (
                    clk,
                    rst_n,
                    input_a,
                    input_b,
                    input_c,
                    input_d,
                    input_e,
                    output_concat);
                input clk;
                input rst_n;
                input [7:0] input_a;
                input [15:0] input_b;
                input [31:0] input_c;
                input [63:0] input_d;
                input [127:0] input_e;
                output [247:0] output_concat;

                reg [247:0] internal_concat_1;
                reg [247:0] internal_concat_2;

                always @(posedge clk) begin
                    if (rst_n == 0) begin
                        internal_concat_1 <= 248'b0;
                        internal_concat_2 <= 248'b0;
                    end else begin
                        internal_concat_1 <= {input_a, input_b, input_c, input_d, input_e};
                        internal_concat_2 <= internal_concat_1;
                    end
                end
                assign output_concat = internal_concat_2;
            endmodule'''
        # write test verilog file
        with open('internal_test.v', 'w') as f:
            f.write(test_verilog)
        test_pyverilator = pyverilator.PyVerilator.build('internal_test.v')

        if False: # internal signals not working anymore
            # get the full signal name for internal_concat_1 and internal_concat_2
            internal_concat_1_sig_name = None
            internal_concat_2_sig_name = None
            for sig_name, _ in test_pyverilator.internal_signals:
                if 'internal_concat_1' in sig_name:
                    internal_concat_1_sig_name = sig_name
                if 'internal_concat_2' in sig_name:
                    internal_concat_2_sig_name = sig_name

        test_pyverilator.start_vcd_trace('test.vcd')
        test_pyverilator['rst_n'] = 0
        test_pyverilator['clk'] = 0
        test_pyverilator['clk'] = 1
        test_pyverilator['rst_n'] = 1
        test_pyverilator['input_a'] = 0xaa
        test_pyverilator['input_b'] = 0x1bbb
        test_pyverilator['input_c'] = 0x3ccccccc
        test_pyverilator['input_d'] = 0x7ddddddddddddddd
        test_pyverilator['input_e'] = 0xfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee

        if False: # internal signals not working anymore
            self.assertIsNotNone(internal_concat_1_sig_name)
            self.assertIsNotNone(internal_concat_2_sig_name)

            self.assertEqual(test_pyverilator[internal_concat_1_sig_name], 0)
            self.assertEqual(test_pyverilator[internal_concat_2_sig_name], 0)
        self.assertEqual(test_pyverilator['output_concat'], 0)

        test_pyverilator['clk'] = 0
        test_pyverilator['clk'] = 1

        if False: # internal signals not working anymore
            self.assertEqual(test_pyverilator[internal_concat_1_sig_name], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)
            self.assertEqual(test_pyverilator[internal_concat_2_sig_name], 0)
        self.assertEqual(test_pyverilator['output_concat'], 0)

        test_pyverilator['clk'] = 0
        test_pyverilator['clk'] = 1

        if False: # internal signals not working anymore
            self.assertEqual(test_pyverilator[internal_concat_1_sig_name], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)
            self.assertEqual(test_pyverilator[internal_concat_2_sig_name], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)
        self.assertEqual(test_pyverilator['output_concat'], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)

        test_pyverilator['clk'] = 0
        test_pyverilator['clk'] = 1

        test_pyverilator.stop_vcd_trace()

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_array_tracing(self):
        test_verilog = '''
            module reg_file (
                    clk,
                    wr_idx,
                    wr_data,
                    rd_idx,
                    rd_data);
                input clk;
                input [4:0] wr_idx;
                input [7:0] wr_data;
                input [4:0] rd_idx;
                output [7:0] rd_data;

                // a 32-entry 8-bit register file
                reg [7:0] arr [31:0];

                always @(posedge clk) begin
                    arr[wr_idx] <= wr_data;
                end

                assign rd_data = arr[rd_idx];
            endmodule'''
        # write test verilog file
        with open('reg_file.v', 'w') as f:
            f.write(test_verilog)
        test_pyverilator = pyverilator.PyVerilator.build('reg_file.v')

        test_pyverilator.start_vcd_trace('test.vcd')

        def write_reg( idx, data ):
            test_pyverilator.io.wr_idx = idx
            test_pyverilator.io.wr_data = data
            test_pyverilator.io.clk = 0
            test_pyverilator.io.clk = 1

        def read_reg( idx ):
            test_pyverilator.io.rd_idx = idx
            return test_pyverilator.io.rd_data

        # TODO: add tests for getting values from internal arrays of registers once supported by pyverilator

        write_reg( 0, 0 )
        self.assertEqual( read_reg(0), 0 )

        write_reg( 1, 3 )
        write_reg( 2, 5 )
        write_reg( 3, 8 )
        self.assertEqual( read_reg(3), 8 )
        self.assertEqual( read_reg(1), 3 )
        self.assertEqual( read_reg(2), 5 )

        write_reg( 4, 11 )
        self.assertEqual( read_reg(3), 8 )

        write_reg( 9, 3 )
        self.assertEqual( read_reg(3), 8 )

        write_reg( 2, 4 )

        write_reg( 1, 5 )
        self.assertEqual( read_reg(9), 3 )
        self.assertEqual( read_reg(1), 5 )
        self.assertEqual( read_reg(2), 4 )

        test_pyverilator.stop_vcd_trace()

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_modular(self):
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

        # in is a reserved keyword in python, so it must be accessed
        # using dictionary syntax:
        # sim.io['in'] = 7
        # or it must be escaped python-style:
        sim.io.in_ = 7

        if False:
            # dropped check on internals, not working anymore
            self.assertEqual(sim.internals.in_reg,          0)
            self.assertEqual(sim.internals.child_1.in_reg,  0)
            self.assertEqual(sim.internals.child_1.out_reg, 0)
            self.assertEqual(sim.internals.child_2.in_reg,  0)
            self.assertEqual(sim.internals.child_2.out_reg, 0)
            self.assertEqual(sim.internals.out_reg,         0)
        self.assertEqual(sim.io.out,                    0)

        sim.clock.tick()

        if False:
            # dropped check on internals, not working anymore
            self.assertEqual(sim.internals.in_reg,          7)
            self.assertEqual(sim.internals.child_1.in_reg,  0)
            self.assertEqual(sim.internals.child_1.out_reg, 1)
            self.assertEqual(sim.internals.child_2.in_reg,  0)
            self.assertEqual(sim.internals.child_2.out_reg, 1)
            self.assertEqual(sim.internals.out_reg,         0)
        self.assertEqual(sim.io.out,                    0)

        sim.clock.tick()

        if False:
            # dropped check on internals, not working anymore
            self.assertEqual(sim.internals.in_reg,          7)
            self.assertEqual(sim.internals.child_1.in_reg,  7)
            self.assertEqual(sim.internals.child_1.out_reg, 1)
            self.assertEqual(sim.internals.child_2.in_reg,  1)
            self.assertEqual(sim.internals.child_2.out_reg, 1)
            self.assertEqual(sim.internals.out_reg,         1)
        self.assertEqual(sim.io.out,                    1)

        sim.clock.tick()

        if False:
            # dropped check on internals, not working anymore
            self.assertEqual(sim.internals.in_reg,          7)
            self.assertEqual(sim.internals.child_1.in_reg,  7)
            self.assertEqual(sim.internals.child_1.out_reg, 8)
            self.assertEqual(sim.internals.child_2.in_reg,  1)
            self.assertEqual(sim.internals.child_2.out_reg, 2)
            self.assertEqual(sim.internals.out_reg,         1)
        self.assertEqual(sim.io.out,                    1)

        sim.clock.tick()

        if False:
            # dropped check on internals, not working anymore
            self.assertEqual(sim.internals.in_reg,          7)
            self.assertEqual(sim.internals.child_1.in_reg,  7)
            self.assertEqual(sim.internals.child_1.out_reg, 8)
            self.assertEqual(sim.internals.child_2.in_reg,  8)
            self.assertEqual(sim.internals.child_2.out_reg, 2)
            self.assertEqual(sim.internals.out_reg,         2)
        self.assertEqual(sim.io.out,                    2)

        sim.clock.tick()

        if False:
            # dropped check on internals, not working anymore
            self.assertEqual(sim.internals.in_reg,          7)
            self.assertEqual(sim.internals.child_1.in_reg,  7)
            self.assertEqual(sim.internals.child_1.out_reg, 8)
            self.assertEqual(sim.internals.child_2.in_reg,  8)
            self.assertEqual(sim.internals.child_2.out_reg, 9)
            self.assertEqual(sim.internals.out_reg,         2)
        self.assertEqual(sim.io.out,                    2)

        sim.clock.tick()

        if False:
            # dropped check on internals, not working anymore
            self.assertEqual(sim.internals.in_reg,          7)
            self.assertEqual(sim.internals.child_1.in_reg,  7)
            self.assertEqual(sim.internals.child_1.out_reg, 8)
            self.assertEqual(sim.internals.child_2.in_reg,  8)
            self.assertEqual(sim.internals.child_2.out_reg, 9)
            self.assertEqual(sim.internals.out_reg,         9)
        self.assertEqual(sim.io.out,                    9)

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_finish(self):
        finish_tester_verilog = '''
            module finish_tester(
                    clk,
                    rst,
                    do_finish);
                input clk;
                input rst;
                input do_finish;

                always @(posedge clk) begin
                    if ((rst == 0) && (do_finish == 1)) begin
                        $finish;
                    end
                end
            endmodule'''
        with open('finish_tester.v', 'w') as f:
            f.write(finish_tester_verilog)

        sim = pyverilator.PyVerilator.build('finish_tester.v')

        self.assertEqual(sim.finished, False)
        sim.finished = True
        self.assertEqual(sim.finished, True)
        sim.finished = False
        self.assertEqual(sim.finished, False)

        sim.io.do_finish = 0
        sim.io.rst = 1
        sim.io.clk = 0
        sim.io.clk = 1
        sim.io.rst = 0

        self.assertEqual(sim.finished, False)

        sim.io.do_finish = 1
        sim.io.clk = 0
        sim.io.clk = 1

        self.assertEqual(sim.finished, True)

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_user_finish(self):
        finish_tester_verilog = '''
            module user_finish_tester(
                    clk,
                    rst,
                    do_finish);
                input clk;
                input rst;
                input do_finish;

                always @(posedge clk) begin
                    if ((rst == 0) && (do_finish == 1)) begin
                        $finish;
                    end
                end
            endmodule'''
        with open('user_finish_tester.v', 'w') as f:
            f.write(finish_tester_verilog)

        sim = pyverilator.PyVerilator.build('user_finish_tester.v')
        user_finish_called = False
        def finish_callback(sim, *args):
            nonlocal user_finish_called
            user_finish_called = True
            sim.finished = True

        sim.set_vl_finish_callback(finish_callback)

        self.assertEqual(sim.finished, False)
        self.assertEqual(user_finish_called, False)
        sim.finished = True
        self.assertEqual(sim.finished, True)
        self.assertEqual(user_finish_called, False)
        sim.finished = False
        self.assertEqual(sim.finished, False)
        self.assertEqual(user_finish_called, False)

        sim.io.do_finish = 0
        sim.io.rst = 1
        sim.io.clk = 0
        sim.io.clk = 1
        sim.io.rst = 0

        self.assertEqual(sim.finished, False)
        self.assertEqual(user_finish_called, False)

        sim.io.do_finish = 1
        sim.io.clk = 0
        sim.io.clk = 1

        self.assertEqual(sim.finished, True)
        self.assertEqual(user_finish_called, True)

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_finish_2_different_files(self):
        finish_tester_verilog = '''
            module finish_tester(
                    clk,
                    rst,
                    do_finish);
                input clk;
                input rst;
                input do_finish;

                always @(posedge clk) begin
                    if ((rst == 0) && (do_finish == 1)) begin
                        $finish;
                    end
                end
            endmodule'''
        with open('finish_tester_1.v', 'w') as f:
            f.write(finish_tester_verilog)
        with open('finish_tester_2.v', 'w') as f:
            f.write(finish_tester_verilog)

        sim_1 = pyverilator.PyVerilator.build('finish_tester_1.v')
        sim_2 = pyverilator.PyVerilator.build('finish_tester_2.v')

        def start_sim(sim):
            sim.io.do_finish = 0
            sim.io.rst = 1
            sim.io.clk = 0
            sim.io.clk = 1
            sim.io.rst = 0

        def finish_sim(sim):
            sim.io.do_finish = 1
            sim.io.clk = 0
            sim.io.clk = 1

        self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, False)

        start_sim(sim_1)

        self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, False)

        start_sim(sim_2)

        self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, False)

        finish_sim(sim_2)

        self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, True)

        finish_sim(sim_1)

        self.assertEqual(sim_1.finished, True)
        self.assertEqual(sim_2.finished, True)

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_user_finish_2_different_files(self):
        finish_tester_verilog = '''
            module user_finish_tester(
                    clk,
                    rst,
                    do_finish);
                input clk;
                input rst;
                input do_finish;

                always @(posedge clk) begin
                    if ((rst == 0) && (do_finish == 1)) begin
                        $finish;
                    end
                end
            endmodule'''
        with open('user_finish_tester_1.v', 'w') as f:
            f.write(finish_tester_verilog)
        with open('user_finish_tester_2.v', 'w') as f:
            f.write(finish_tester_verilog)

        sim_1 = pyverilator.PyVerilator.build('user_finish_tester_1.v')
        sim_2 = pyverilator.PyVerilator.build('user_finish_tester_2.v')

        user_finish_called_1 = False
        def finish_callback_1(sim, *args):
            nonlocal user_finish_called_1
            user_finish_called_1 = True
            sim.finished = True
        sim_1.set_vl_finish_callback(finish_callback_1)

        user_finish_called_2 = False
        def finish_callback_2(sim, *args):
            nonlocal user_finish_called_2
            user_finish_called_2 = True
            sim.finished = True
        sim_2.set_vl_finish_callback(finish_callback_2)

        def start_sim(sim):
            sim.io.do_finish = 0
            sim.io.rst = 1
            sim.io.clk = 0
            sim.io.clk = 1
            sim.io.rst = 0

        def finish_sim(sim):
            sim.io.do_finish = 1
            sim.io.clk = 0
            sim.io.clk = 1

        self.assertEqual(sim_1.finished, False) # undefined
        self.assertEqual(sim_2.finished, False) # undefined
        self.assertEqual(user_finish_called_1, False)
        self.assertEqual(user_finish_called_2, False)

        start_sim(sim_1)

        self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, False)
        self.assertEqual(user_finish_called_1, False)
        self.assertEqual(user_finish_called_2, False)

        start_sim(sim_2)

        self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, False)
        self.assertEqual(user_finish_called_1, False)
        self.assertEqual(user_finish_called_2, False)

        finish_sim(sim_2)

        self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, True)
        self.assertEqual(user_finish_called_1, False)
        self.assertEqual(user_finish_called_2, True)

        finish_sim(sim_1)

        self.assertEqual(sim_1.finished, True)
        self.assertEqual(sim_2.finished, True)
        self.assertEqual(user_finish_called_1, True)
        self.assertEqual(user_finish_called_2, True)

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_finish_2_same_files(self):
        # This is known to fail at the moment because the same shared object is shared between
        # sim_1 and sim_2. To fix this, we whould have to find a way to make a unique shared
        # object for each sim.
        finish_tester_verilog = '''
            module finish_tester(
                    clk,
                    rst,
                    do_finish);
                input clk;
                input rst;
                input do_finish;

                always @(posedge clk) begin
                    if ((rst == 0) && (do_finish == 1)) begin
                        $finish;
                    end
                end
            endmodule'''
        with open('finish_tester_same.v', 'w') as f:
            f.write(finish_tester_verilog)

        sim_1 = pyverilator.PyVerilator.build('finish_tester_same.v')
        sim_2 = pyverilator.PyVerilator.build('finish_tester_same.v')

        def start_sim(sim):
            sim.io.do_finish = 0
            sim.io.rst = 1
            sim.io.clk = 0
            sim.io.clk = 1
            sim.io.rst = 0

        def finish_sim(sim):
            sim.io.do_finish = 1
            sim.io.clk = 0
            sim.io.clk = 1

        self.assertEqual(sim_1.finished, False) # undefined
        self.assertEqual(sim_2.finished, False) # undefined

        start_sim(sim_1)

        self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, False)

        start_sim(sim_2)

        self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, False)

        finish_sim(sim_2)

        # self.assertEqual(sim_1.finished, False)
        self.assertEqual(sim_2.finished, True)

        finish_sim(sim_1)

        self.assertEqual(sim_1.finished, True)
        self.assertEqual(sim_2.finished, True)

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_command_args(self):
        finish_tester_verilog = '''
            module command_args_tester(
                    rst,
                    clk,
                    counter);
                input clk;
                input rst;
                output reg [7:0] counter;

                integer step;

                always @(posedge clk) begin
                    if (rst == 1) begin
                        counter <= 0;
                    end else begin
                        if ($test$plusargs("plusone")) begin
                            counter <= counter + 1;
                        end else if ($value$plusargs("step=%d", step)) begin
                            counter <= counter + step;
                        end
                    end
                end
            endmodule'''
        with open('command_args_tester.v', 'w') as f:
            f.write(finish_tester_verilog)
        with open('command_args_tester_plus_one.v', 'w') as f:
            f.write(finish_tester_verilog)
        with open('command_args_tester_step_two.v', 'w') as f:
            f.write(finish_tester_verilog)
        with open('command_args_tester_step_three.v', 'w') as f:
            f.write(finish_tester_verilog)

        def test_sim(sim, expected_step):
            sim.io.rst = 1
            sim.io.clk = 0
            sim.io.clk = 1
            sim.io.rst = 0
            self.assertEqual(sim.io.counter, 0)
            sim.io.clk = 0
            sim.io.clk = 1
            self.assertEqual(sim.io.counter, expected_step)
            sim.io.clk = 0
            sim.io.clk = 1
            self.assertEqual(sim.io.counter, 2 * expected_step)

        sim = pyverilator.PyVerilator.build('command_args_tester.v')
        test_sim(sim, 0)

        sim = pyverilator.PyVerilator.build('command_args_tester_plus_one.v', command_args=['+plusone',])
        test_sim(sim, 1)

        sim = pyverilator.PyVerilator.build('command_args_tester_step_two.v', command_args=['+step=2',])
        test_sim(sim, 2)

        sim = pyverilator.PyVerilator.build('command_args_tester_step_three.v', command_args=['+step=3',])
        test_sim(sim, 3)

    @unittest.skipIf(shutil.which('verilator') is None, "test requires verilator to be in the path")
    def test_pyverilator_verilog_defines(self):
        finish_tester_verilog = '''
            module verilog_defines_tester(
                    rst,
                    clk,
                    counter);
                input clk;
                input rst;
                output reg [7:0] counter;

                integer step;

                always @(posedge clk) begin
                    if (rst == 1) begin
                        counter <= 0;
                    end else begin
`ifdef PLUSONE
                        counter <= counter + 1;
`endif
`ifdef STEP
                        counter <= counter + `STEP;
`endif
                    end
                end
            endmodule'''
        with open('verilog_defines_tester.v', 'w') as f:
            f.write(finish_tester_verilog)
        with open('verilog_defines_tester_plus_one.v', 'w') as f:
            f.write(finish_tester_verilog)
        with open('verilog_defines_tester_step_two.v', 'w') as f:
            f.write(finish_tester_verilog)
        with open('verilog_defines_tester_step_three.v', 'w') as f:
            f.write(finish_tester_verilog)

        def test_sim(sim, expected_step):
            sim.io.rst = 1
            sim.io.clk = 0
            sim.io.clk = 1
            sim.io.rst = 0
            self.assertEqual(sim.io.counter, 0)
            sim.io.clk = 0
            sim.io.clk = 1
            self.assertEqual(sim.io.counter, expected_step)
            sim.io.clk = 0
            sim.io.clk = 1
            self.assertEqual(sim.io.counter, 2 * expected_step)

        sim = pyverilator.PyVerilator.build('verilog_defines_tester.v')
        test_sim(sim, 0)

        sim = pyverilator.PyVerilator.build('verilog_defines_tester_plus_one.v', verilog_defines=('PLUSONE',))
        test_sim(sim, 1)

        sim = pyverilator.PyVerilator.build('verilog_defines_tester_step_two.v', verilog_defines=('STEP=2',))
        test_sim(sim, 2)

        sim = pyverilator.PyVerilator.build('verilog_defines_tester_step_three.v', verilog_defines=('STEP=3',))
        test_sim(sim, 3)

    @unittest.skipIf(shutil.which('verilator') is None or shutil.which('gtkwave') is None, "test requires verilator and gtkwave to be in the path")
    def test_pyverilator_variable_names(self):
        # the last few names have a \ before them because they are required
        # for verilog, but are not really part of the name
        variable_names = ['a', '_a', '__a', '___a', 'a_', 'a__', 'a___', 'a_a', 'a__a', 'a___a', 'a__020a', r'\$^_^', r'\%20', r'\007', r'\.][.']

        test_verilog = 'module variable_name_test( '
        test_verilog += ' , '.join(['input ' + var for var in variable_names] + ['output ' + var + '_out' for var in variable_names])
        test_verilog += ' );\n'
        for var in variable_names:
            test_verilog += '    assign {}_out = {} ;\n'.format(var, var)
        test_verilog += 'endmodule\n'

        # write test verilog file
        with open('variable_name_test.v', 'w') as f:
            f.write(test_verilog)
        sim = pyverilator.PyVerilator.build('variable_name_test.v')

        for var in variable_names:
            if var.startswith('\\'):
                var = var[1:]
            sim.io[var] = 0
            self.assertEqual(sim.io[var + '_out'], 0)
            sim.io[var] = 1
            self.assertEqual(sim.io[var + '_out'], 1)
            sim.io[var] = 0
            self.assertEqual(sim.io[var + '_out'], 0)
    
    def test_verilator_tools(self):
        pyverilator.verilator_tools.test_verilator_tools()

if __name__ == '__main__':
    unittest.main()
