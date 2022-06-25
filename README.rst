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

Build process sketch
====================

1. Build and test in the TSSW devel container (lsstts/develop-env) (https://tssw-developer.lsst.io/docker/docker.html#csc-development).
2. Use the TSSW conda-build container (lsstts/conda_package_builder) to build using the conda recipe (https://tssw-developer.lsst.io/conda/conda.html).
3. Publish to the ``lsst-dm`` conda channel on Anaconda using the ``anaconda login`` command with the ``dm-admin`` user (credentials in the Architecture vault in 1Password) and the ``anaconda upload`` command.
4. Update the version in lsst-ts/ts_cycle_build cycle/cycle.env.
5. Use the TSSW Jenkins (https://tssw-ci.lsst.org/view/CycleBuild/job/cycleBuild/) to build and publish the container.
