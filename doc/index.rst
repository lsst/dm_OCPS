.. py:currentmodule:: lsst.dm.OCPS

.. _lsst.dm.OCPS:

############
lsst.dm.OCPS
############

.. image:: https://img.shields.io/badge/SAL\ Interface-gray.svg
    :target: https://ts-xml.lsst.io/sal_interfaces/OCPS.html
.. image:: https://img.shields.io/badge/GitHub-gray.svg
    :target: https://github.com/lsst/dm_OCPS
.. image:: https://img.shields.io/badge/Jira-gray.svg
    :target: https://jira.lsstcorp.org/issues/?jql=labels+%3D+dm_OCPS

.. _lsst.dm.OCPS.overview:

Overview
========

OCPS is the Vera C. Rubin Observatory OCS-Controlled Pipeline System.

It allows the Script Queue to explicitly and flexibly command processing of data obtained from the Gen3 Butler repository in the Observatory Operations Data Service.


.. _lsst.dm.OCPS.user_guide:

User Guide
==========

Start the OCPS CSC as follows:

.. prompt:: bash

    run_OCPS.py

Stop the CSC by sending it to the OFFLINE state.

See OCPS `SAL communication interface <https://ts-xml.lsst.io/sal_interfaces/OCPS.html>`_ for commands, events, and telemetry.

.. _lsst.dm.OCPS.configuration:

Configuration
-------------

Configuration is defined by a schema in the code.
It consists of two required values:

* ``url``: a URL pointing to the REST API endpoint for the back-end execution service
* ``poll_interval``: the interval in seconds between polls for status of executing pipelines

Configuration files live in `dm_config_ocps/OCPS <https://github.com/lsst/dm_config_ocps/tree/develop/OCPS>`_.

.. _lsst.dm.OCPS.simulation:

Simulator
---------

The CSC includes a simulation mode.  To run using simulation:

.. prompt:: bash

  run_OCPS.py --simulate

The simulation bypasses the need for a back-end execution service, so it ignores any configuration.
It instead accepts ``execute`` commands with a ``pipeline`` parameter of ``true.yaml`` (always succeeding), ``false.yaml`` (always failing), or ``fault.yaml`` (always causing a transition to FAULT state).
All other ``execute`` parameters are ignored.

Developer Guide
===============

.. toctree::
    developer-guide
    :maxdepth: 1

Version History
===============

.. toctree::
    version_history
    :maxdepth: 1
