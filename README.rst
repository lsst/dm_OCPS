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

1. Clone dm_config_ocps and dm_OCPS into ``./develop``.
2. Build and test in the TSSW devel container (https://tssw-developer.lsst.io/docker/docker.html#csc-development).

   .. code-block:: sh

      docker pull lsstts/develop-env:develop
      docker run -it --rm -v `pwd`/develop:/home/saluser/develop lsstts/develop-env:develop
      setup -r develop/dm_config_ocps
      cd develop/dm_OCPS
      setup -k -r .
      scons

3. Update the version history in ``doc/version_history.rst`` using an appropriate semantic version number.
4. When ready, merge to main and tag with the version number.
5. Use the TSSW conda-build container to build using the conda recipe (https://tssw-developer.lsst.io/conda/conda.html).

   .. code-block:: sh

      docker pull lsstts/conda_package_builder:latest
      docker run -it -e DM_CONFIG_OCPS_DIR=/home/saluser/develop/dm_config_ocps -v `pwd`/develop:/home/saluser/develop --rm ts-dockerhub.lsst.org/conda_package_builder:latest
      cd develop/dm_OCPS
      conda build --variants "{salobj_version: '', idl_version: ''}" --prefix-length=100 .

6. Publish to the ``lsst-dm`` conda channel on Anaconda using the ``anaconda login`` command with the ``dm-admin`` user (credentials in the Architecture vault in 1Password) and the ``anaconda upload`` command printed by ``conda build`` with the ``--user lsst-dm`` option.
7. Update the version of ``dm_OCPS`` (and ``dm_config_ocps``, if necessary) in ``lsst-ts/ts_cycle_build`` ``cycle/cycle.env`` on a ticket branch.
8. Use the `TSSW Jenkins <https://tssw-ci.lsst.org/view/CycleBuild/job/cycleBuild/>`__ to build and publish the container using that ticket branch.
9. Request merge of the ticket branch and deployment of the container from the TTS manager.
