import argparse
import IPython
import pyverilator

prog_name = 'python3 -m pyverilator'
parser = argparse.ArgumentParser(prog = prog_name, description='Construct a PyVerilator object and open an IPython shell')
parser.add_argument('verilogfile', help = 'top level verilog file to simulate')

args = parser.parse_args()

sim = pyverilator.PyVerilator.build(args.verilogfile)

IPython.start_ipython( argv = [], user_ns = {'sim' : sim} )
