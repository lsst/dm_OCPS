#!/usr/bin/env python
# This file is part of dm_OCPS
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
import asyncio
import shlex
from lsst.ts.salobj import CscCommander
from lsst.dm.OCPS import OcpsIndex


class OcpsCscCommander(CscCommander):
    def __init__(self, *args, **kwargs):
        super().__init__(name="OCPS", *args, **kwargs)
        for command in ("abort", "enterControl", "setValue"):
            del self.command_dict[command]

    async def do_execute(self, args):
        # Re-parse to handle quotes
        await self.run_command_topic("execute", shlex.split(" ".join(args)))


asyncio.run(OcpsCscCommander.amain(index=OcpsIndex))
