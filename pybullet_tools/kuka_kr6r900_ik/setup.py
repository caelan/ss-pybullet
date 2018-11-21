#!/usr/bin/env python

import os, shutil, sys

from distutils.dir_util import copy_tree
from distutils.core import setup, Extension
import fnmatch

# Build C++ extension by running: 'python setup.py build'
# see: https://docs.python.org/3/extending/building.html

# lib name template: 'ikfast_<robot name>'
IKFAST = 'ikfast_kuka_kr6r900'

ikfast_module = Extension(IKFAST,
                          sources=['ikfast.cpp'])

setup(name=IKFAST,
      version='1.0',
      description="ikfast module for KUKA kr6r900.",
      ext_modules=[ikfast_module])

build_lib_path = None

for root, dirnames, filenames in os.walk(os.getcwd()):
    if fnmatch.fnmatch(root, os.path.join(os.getcwd(),"*build","lib*")):
        build_lib_path = root
        break

assert(build_lib_path)

copy_tree(build_lib_path, os.getcwd())
shutil.rmtree(os.path.join(os.getcwd(), 'build'))

try:
    import ikfast_kuka_kr6r900
    print('\nikfast module %s imported successful'%(IKFAST))
except ImportError as e:
    print('\nikfast module %s imported failed'%(IKFAST))
    raise e
