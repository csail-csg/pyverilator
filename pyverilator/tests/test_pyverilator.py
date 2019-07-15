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
        test_pyverilator = pyverilator.PyVerilator.from_verilog('width_test.v')

        test_pyverilator.start_vcd_trace('test.vcd')
        test_pyverilator['input_a'] = 0xaa
        test_pyverilator['input_b'] = 0x1bbb
        test_pyverilator['input_c'] = 0x3ccccccc
        test_pyverilator['input_d'] = 0x7ddddddddddddddd
        test_pyverilator['input_e'] = 0xfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee

        self.assertEqual(test_pyverilator['output_concat'], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)

        test_pyverilator.stop_vcd_trace()

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
        test_pyverilator = pyverilator.PyVerilator.from_verilog('internal_test.v')

        # get the full signal name for internal_concat_1 and internal_concat_2
        internal_concat_1_sig_name = None
        internal_concat_2_sig_name = None
        for sig_name, sig_width in test_pyverilator.internal_signals:
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

        self.assertIsNotNone(internal_concat_1_sig_name)
        self.assertIsNotNone(internal_concat_2_sig_name)

        self.assertEqual(test_pyverilator[internal_concat_1_sig_name], 0)
        self.assertEqual(test_pyverilator[internal_concat_2_sig_name], 0)
        self.assertEqual(test_pyverilator['output_concat'], 0)

        test_pyverilator['clk'] = 0
        test_pyverilator['clk'] = 1

        self.assertEqual(test_pyverilator[internal_concat_1_sig_name], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)
        self.assertEqual(test_pyverilator[internal_concat_2_sig_name], 0)
        self.assertEqual(test_pyverilator['output_concat'], 0)

        test_pyverilator['clk'] = 0
        test_pyverilator['clk'] = 1

        self.assertEqual(test_pyverilator[internal_concat_1_sig_name], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)
        self.assertEqual(test_pyverilator[internal_concat_2_sig_name], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)
        self.assertEqual(test_pyverilator['output_concat'], 0xaa1bbb3ccccccc7dddddddddddddddfeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee)

        test_pyverilator['clk'] = 0
        test_pyverilator['clk'] = 1

        test_pyverilator.stop_vcd_trace()

    def test_pyverilator_array_tracing2(self):
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
        test_pyverilator = pyverilator.PyVerilator.from_verilog('reg_file.v')

        test_pyverilator.start_vcd_trace('test.vcd')

        def write_reg( idx, data ):
            test_pyverilator.io.wr_idx = idx
            test_pyverilator.io.wr_data = data
            test_pyverilator.io.clk = 0
            test_pyverilator.io.clk = 1

        def read_reg( idx ):
            test_pyverilator['rd_idx'] = idx
            return test_pyverilator['rd_data']

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


