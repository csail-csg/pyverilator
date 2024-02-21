PyVerilator-mm
==============

This is a fork of the original pyverilator package, that manages a newer verilator syntax 
and works with WSL (by importing tclwraper only if gtkwave is required).
Below the original readme.

PyVerilator
===========

This package provides a wrapper to generate and use verilator
hardware models in python.


Installing Non-Development Version
----------------------------------

If you want to just install the `pyverilator` package, you should be able to
using the following command:


    $ pip3 install pyverilator

Installing Development Version
-------------------------------

    pip3 install git+https://github.com/bat52/pyverilator.git@master

Usage
-----

Assume you have the following verilog module stored in ``counter.v``.

.. code:: verilog

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
    endmodule

Then you can use ``pyverilator`` to simulate this module using verilator in
python.

.. code:: python

    sim = pyverilator.PyVerilator.build('counter.v')

    # start gtkwave to view the waveforms as they are made
    sim.start_gtkwave()

    # add all the io and internal signals to gtkwave
    sim.send_signals_to_gtkwave(sim.io)
    # sim.send_signals_to_gtkwave(sim.internals) # not working anymore

    # add all the io and internal signals to gtkwave
    sim.send_to_gtkwave(sim.io)
    # sim.send_to_gtkwave(sim.internals) # not working anymore

    # tick the automatically detected clock
    sim.clock.tick()

    # set rst back to 0
    sim.io.rst = 0

    # check out when en = 0
    sim.io.en = 0
    curr_out = sim.io.out
    # sim.io is a pyverilator.Collection, accessing signals by attribute or
    # dictionary syntax returns a SignalValue object which inherits from int.
    # sim.io.out can be used just like an int in most cases, and it has extra
    # features like being able to add it to gtkwave with
    # sim.io.out.send_to_gtkwave(). To just get the int value, you can call
    # sim.io.out.value
    print('sim.io.out = ' + str(curr_out))

    # check out when en = 1
    sim.io.en = 1
    curr_out = sim.io.out
    print('sim.io.out = ' + str(curr_out))

    sim.clock.tick()

    # check out after ticking clock
    curr_out = sim.io.out
    print('sim.io.out = ' + str(curr_out))

The full code for this and other examples can be found in the examples folder
of the git repository.

Installing for Development
--------------------------

To install this package for development, you should use a virtual environment,
and install the package in editable mode using pip.

To create a virtual environment for this project, run the command below.

    $ python3 -m venv path/to/new-venv-folder

To start using your new virtual environment, run the command below.
This needs to be run each time you open a new terminal.

    $ source path/to/new-venv-folder/bin/activate

At this point you are now using your new virtual environment.
Python packages you install in this environment will not be available outside
your virtual environment.
If you want to stop using the virtual environment, just run ``deactivate``.

To install the ``pyverilator`` package in editable mode, inside the
``pyverilator`` top git repository folder, run the command below.

    $ pip3 install -e .
