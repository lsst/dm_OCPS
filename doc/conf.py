"""Sphinx configuration file for an LSST stack package.

This configuration only affects single-package Sphinx documentation builds.
"""

from documenteer.sphinxconfig.stackconf import build_package_configs
import lsst.dm.OCPS


_g = globals()
_g.update(
    build_package_configs(
        project_name='dm_OCPS',
        version=lsst.dm.OCPS.version.__version__
    )
)
