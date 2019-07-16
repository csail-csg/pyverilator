# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='PyVerilator',
    version='0.1.0',
    description='Python interface to Verilator models',
    long_description=long_description,
    url='https://github.com/csail-csg/pyverilator',
    author='CSAIL CSG',
    author_email='acwright@mit.edu, bthom@mit.edu',
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Hardware',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='Verilator Wrapper Verilog',
    packages=find_packages(exclude=['example']),
    include_package_data=True,
    install_requires=['tclwrapper>=0.0.1'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    entry_points={
        # If we ever want to add an executable script, this is where it goes
    },
    project_urls={
        'Bug Reports': 'https://github.com/csail-csg/pyverilator/issues',
        'Source': 'https://github.com/csail-csg/pyverilator',
    },
)
