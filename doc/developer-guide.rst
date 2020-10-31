.. py:currentmodule:: lsst.dm.OCPS

.. _lsst.dm.OCPS.developer_guide:

###############
Developer Guide
###############

The ATDome CSC is implemented using `ts_salobj <https://github.com/lsst-ts/ts_salobj>`_.

.. _lsst.dm.OCPS.api:

API
===

The primary classes are:

* `OcpsCsc`: controller for the auxiliary telescope dome.

.. automodapi:: lsst.dm.OCPS
    :no-main-docstr:

.. _lsst.dm.OCPS.build:

Build and Test
==============

This is a pure python package. There is nothing to build except the documentation.

.. code-block:: bash

    make_idl_files.py OCPS
    setup -r .
    pytest -v  # to run tests
    package-docs clean; package-docs build  # to build the documentation

.. _lsst.dm.OCPS.contributing:

Contributing
============

``lsst.dm.OCPS`` is developed at https://github.com/lsst/dm_OCPS.
Bug reports and feature requests use `Jira with labels=dm_OCPS <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20labels%20%20%3D%20dm_OCPS>`_.

