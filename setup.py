#! /usr/bin/env python

from setuptools import setup
import sys

# When making changes to the following list, remember to keep
# CMakeLists.txt in sync.
scripts = [
    "btest",
    "btest-ask-update",
    "btest-bg-run",
    "btest-bg-run-helper",
    "btest-bg-wait",
    "btest-diff",
    "btest-setsid",
    "btest-progress",
    "sphinx/btest-diff-rst",
    "sphinx/btest-rst-cmd",
    "sphinx/btest-rst-include",
    "sphinx/btest-rst-pipe",
]

py_modules = ["btest-sphinx"]

# We require the external multiprocess library on Windows due to pickling issues
# with the standard one.
if sys.platform == "win32":
    install_requires = ["multiprocess"]
else:
    install_requires = []

setup(
    name="btest",
    version="1.1",  # Filled in automatically.
    description="A powerful system testing framework",
    long_description="See https://github.com/zeek/btest",
    author="The Zeek Team",
    author_email="info@zeek.org",
    url="https://github.com/zeek/btest",
    scripts=scripts,
    package_dir={"": "sphinx"},
    py_modules=py_modules,
    license="3-clause BSD License",
    keywords="system tests testing framework baselines",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    install_requires=install_requires,
)
