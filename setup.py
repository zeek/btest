#! /usr/bin/env python

from distutils.core import setup, Extension

scripts = ["btest", "btest-diff", "btest-bg-run",
           "btest-bg-run-helper", "btest-bg-wait", "btest-setsid",
           "sphinx/btest-rst-cmd", "sphinx/btest-rst-pipe", "sphinx/btest-rst-include",
           ]

setup(name='btest',
      version="0.51-14", # Filled in automatically.
      description='A simple unit testing framework',
      author='Robin Sommer',
      author_email='robin@icir.org',
      url='http://www.icir.org/robin/btest',
      scripts=scripts,
      include_dirs=["examples", "Baseline"],
      package_dir={"": "sphinx"},
      py_modules=["btest-sphinx"]
     )
