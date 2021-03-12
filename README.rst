#######
dm_OCPS
#######

dm_OCPS is a Commandable SAL Component (CSC) for the OCS-Controlled Pipeline System for the Vera C. Rubin Observatory, as described in `DMTN-133 <https://dmtn-133.lsst.io/>`_.

The package is compatible with Vera Rubin LSST DM's ``scons`` build system, and the `eups <https://github.com/RobertLuptonTheGood/eups>`_ package management system. Assuming you have the basic DM stack installed you can do the following, from within the package directory:

* ``setup -r .`` to setup the package and dependencies.
* ``scons`` to build the package and run unit tests.
* ``scons install declare`` to install the package and declare it to eups.
* ``package-docs build`` to build the documentation.
    This requires ``documenteer``; see `building single package docs <https://developer.lsst.io/stack/building-single-package-docs.html>`_ for installation instructions.

This code uses ``pre-commit`` to maintain ``black`` formatting and ``flake8`` compliance.
To enable this, run the following command once::

    pre-commit install
