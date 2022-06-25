"""Sphinx configuration file for an LSST stack package.

This configuration only affects single-package Sphinx documentation builds.
"""

import lsst.dm.OCPS
from documenteer.sphinxconfig.stackconf import build_package_configs

_g = globals()
_g.update(
    build_package_configs(
        project_name="dm_OCPS", version=lsst.dm.OCPS.version.__version__
    )
)
