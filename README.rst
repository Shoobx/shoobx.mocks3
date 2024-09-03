Shoobx Mock S3 Server
=====================

.. image:: https://github.com/Shoobx/shoobx.mocks3/actions/workflows/test.yml/badge.svg
   :target: https://github.com/Shoobx/shoobx.mocks3/actions

.. image:: https://coveralls.io/repos/github/Shoobx/shoobx.mocks3/badge.svg?branch=master
   :target: https://coveralls.io/github/Shoobx/shoobx.mocks3?branch=master

.. image:: https://img.shields.io/pypi/v/shoobx.mocks3.svg
   :target: https://pypi.python.org/pypi/shoobx.mocks3

.. image:: https://img.shields.io/pypi/pyversions/shoobx.mocks3.svg
   :target: https://pypi.python.org/pypi/shoobx.mocks3/

.. image:: https://api.codeclimate.com/v1/badges/74a6e72efcd89c5a702b/maintainability
   :target: https://codeclimate.com/github/Shoobx/shoobx.mocks3/maintainability
   :alt: Maintainability

This package implements a mock S3 server including bucket shadowing
support. The code is based on the ``moto`` package by implementing a custom
service.

Configure Docker image with environment variables
-------------------------------------------------

If you want to change variable from config use next patter ``{section}_{name}_{variable}.`` For example you want to change directory for ``shoobx:mocks3`` section::

   [shoobx:mocks3]
   log-level = INFO
   directory = ./data

   [bar:boo]
   baz = foo

To change it use ``SHOOBX_MOCKS3_DIRECTORY=/some/path/to/folder``.

For ``baz`` accordingly ``BAR_BOO_BAZ=MyValue``
