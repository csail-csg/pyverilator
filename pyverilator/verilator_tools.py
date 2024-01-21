#!/usr/bin/env python3
""" verilator helping functions """

import subprocess
from packaging import version

def verilator_version():
    """ Returns verilator version """
    result = subprocess.run(['verilator', '--version'], stdout=subprocess.PIPE)
    ver = result.stdout.split()[1]
    return ver.decode("utf-8")

def verilator_flushcall_ok():
    """ check Verilated::flushCall() exist """
    # https://github.com/chipsalliance/chisel3/issues/1565
    ver = verilator_version()
    # print(ver)
    if ( version.parse(ver) < version.parse("4.036") or
         version.parse(ver) > version.parse("4.102")):
        return True
    else:
        return False

def verilator_verilog_tb_ok():
    """ check verilator supports verilog testbench """
    # https://www.reddit.com/r/FPGA/comments/14w95s2/verilator_do_i_need_to_maintain_two_testbench/
    ver = verilator_version()
    return version.parse(ver) > version.parse("5.002")

def test_verilator_tools():
    """ test function """
    print('Testing verilator tools...')
    assert isinstance(verilator_version(),str)
    assert isinstance(verilator_flushcall_ok(),bool)
    assert isinstance(verilator_verilog_tb_ok(),bool)
    print('OK!\n')

if __name__ == '__main__':
    test_verilator_tools()   
