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
      version="0.56-5", # Filled in automatically.
      description='A simple unit testing framework',
      long_description='See https://github.com/bro/btest',
      author='Robin Sommer',
      author_email='robin@icir.org',
      url='https://github.com/bro/btest',
      scripts=scripts,
      package_dir={"": "sphinx"},
      py_modules=py_modules,
      license='3-clause BSD License',
      keywords='unit tests testing framework baselines',
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
      ],
     )
