.. BTest-Sphinx Demo documentation master file, created by
   sphinx-quickstart on Wed May  8 15:22:37 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to BTest-Sphinx Demo's documentation!
=============================================

Contents:

.. toctree::
   :maxdepth: 2

Testing
=======

.. btest:: hello-world

    @TEST-EXEC: btest-rst-cmd echo "Hello, world!"

.. btest:: hello-world

    @TEST-EXEC: btest-rst-cmd echo "Hello, world! Again."


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

