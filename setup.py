# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pyverilator-mm',
    version='0.7.5',
    description='Python interface to Verilator models',
    long_description=long_description,
    url='https://github.com/bat52/pyverilator',
    author='CSAIL CSG, Marco Merlin',
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
    packages=find_packages(exclude=['examples']),
    include_package_data=True,
    install_requires=[],
    setup_requires=['pytest-runner'],
    tests_require=['pytest',
                   'tclwrapper>=0.0.1',
                    'packaging'],
    entry_points={
        # If we ever want to add an executable script, this is where it goes
    },
    project_urls={
        'Bug Reports': 'https://github.com/bat52/pyverilator/issues',
        'Source': 'https://github.com/bat52/pyverilator',
    },
)
