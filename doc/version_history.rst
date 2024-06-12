.. py:currentmodule:: lsst.dm.OCPS

.. _lsst.dm.OCPS.version_history:

###############
Version History
###############

v1.0.0
======

* Initial release.

Requires:

* ts_salobj 6.3
* ts_idl
* IDL file for OCPS from ts_xml 8

v2.0.9
======

* Update UWS backend API.

v3.0.2
======

* Change CSC to be indexed.

v4.0.1
======

* Update to salobj 7.

v4.1.0
======

* Use pyproject.toml.


v4.2.0
======

* Add features for prerequisite jobs and output dataset type override.

v4.2.1
======

* Fix an asyncio usage bug.

v4.2.2
======

* Fix a status URL handling bug.

v4.3.0
======

* Add support for an index based implementation that uses Rapid Analysis as the backend.
  This is done via a Redis server, by setting specific key/values.
  The index based implementation means that the CSC will run in Rapid Analysis mode only if it is running with a specific set of indices.
  For now, this is only index=101.

