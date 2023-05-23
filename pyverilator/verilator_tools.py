import subprocess

def verilator_version():
    result = subprocess.run(['verilator', '--version'], stdout=subprocess.PIPE)
    ver = result.stdout.split()[1]
    return ver.decode("utf-8") 

def verilator_flushcall_ok():
    # check Verilated::flushCall() exist
    # https://github.com/chipsalliance/chisel3/issues/1565
    from packaging import version
    ver = verilator_version()
    # print(ver)
    if ( version.parse(ver) < version.parse("4.036") or
         version.parse(ver) > version.parse("4.102")):
        return True
    else:
        return False
