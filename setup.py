import setuptools

install_requires = []
dev_requires = install_requires + ["documenteer[pipelines]"]
scm_version_template = """# Generated by setuptools_scm
__all__ = ["__version__"]
__version__ = "{version}"
"""

setuptools.setup(
    name="dm_OCPS",
    description="LSST OCS-Controlled Pipeline System",
    use_scm_version={
        "write_to": "python/lsst/dm/OCPS/version.py",
        "write_to_template": scm_version_template,
    },
    setup_requires=["setuptools_scm"],
    install_requires=install_requires,
    package_dir={"": "python"},
    packages=setuptools.find_namespace_packages(where="python"),
    package_data={"": ["*.rst", "*.yaml"]},
    scripts=["bin/run_ocps.py"],
    extras_require={"dev": dev_requires},
    license="GPL",
    project_urls={
        "Bug Tracker": "https://jira.lsstcorp.org/secure/Dashboard.jspa",
        "Source Code": "https://github.com/lsst/dm_OCPS",
    },
)
