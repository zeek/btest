#! /usr/bin/env python

from distutils.core import setup, Extension

scripts = [
    "btest",
    "btest-ask-update",
    "btest-bg-run",
    "btest-bg-run-helper",
    "btest-bg-wait",
    "btest-diff",
    "btest-setsid",
    "sphinx/btest-diff-rst",
    "sphinx/btest-rst-cmd",
    "sphinx/btest-rst-include",
    "sphinx/btest-rst-pipe",
]

py_modules = [
    "btest-sphinx"
]

setup(name='btest',
      version="0.54", # Filled in automatically.
      description='A simple unit testing framework',
      author='Robin Sommer',
      author_email='robin@icir.org',
      url='http://www.icir.org/robin/btest',
      scripts=scripts,
      package_dir={"": "sphinx"},
      py_modules=py_modules
     )
