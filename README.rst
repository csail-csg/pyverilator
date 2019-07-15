PyVerilator
===========

This package provides a wrapper to generate and use verilator
hardware models in python.


Installing Non-Development Version
----------------------------------

If you want to just install the `pyverilator` package, you should be able to using the following command:


    $ pip3 install https://github.com/csail-csg/pyverilator



Usage
-----

.. code:: python

    sim = PyVerilator.build('my_verilator_file.v')
    sim.io.a = 2
    sim.io.b = 3
    print('c = ' + sim.io.c)


Installing for Development
--------------------------

To install this package for development, you should use a virtual environment, and install the package in editable mode using pip.

To create a virtual environment for this project, run the command below.

    $ python3 -m venv path/to/new-venv-folder

To start using your new virtual environment, run the command below.
This needs to be run each time you open a new terminal.

    $ source path/to/new-venv-folder/bin/activate

At this point you are now using your new virtual environment.
Python packages you install in this environment will not be available outside your virtual environment.
If you want to stop using the virtual environment, just run `deactivate`.

To install the `pyverilator` package in editable mode, inside the `pyverilator` top git repository folder, run the command below.

    $ pip3 install -e .
