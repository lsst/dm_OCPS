# This file is part of dm_OCPS.
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
# You should have received a copy of the GNU General Public License

import glob
import os
import pathlib
import unittest

import asynctest
import yaml

from lsst.ts import salobj
from lsst.dm import OCPS

STD_TIMEOUT = 2    # standard command timeout (sec)
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


class CscTestCase(salobj.BaseCscTestCase, asynctest.TestCase):
    def basic_make_csc(self, initial_state, config_dir, simulation_mode,
                       **kwargs):
        return OCPS.OcpsCsc(
            initial_state=initial_state,
            config_dir=config_dir,
            simulation_mode=simulation_mode,
        )

    async def test_default_config_dir(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=1
        ):
            self.assertEqual(self.csc.summary_state, salobj.State.STANDBY)
            await self.assert_next_summary_state(salobj.State.STANDBY)

            desired_config_pkg_name = "dm_config_ocps"
            desired_config_env_name = desired_config_pkg_name.upper() + "_DIR"
            desired_config_pkg_dir = os.environ[desired_config_env_name]
            desired_config_dir = pathlib.Path(desired_config_pkg_dir) / "OCPS/v1"
            self.assertEqual(self.csc.get_config_pkg(), desired_config_pkg_name)
            self.assertEqual(self.csc.config_dir, desired_config_dir)

    async def test_configuration(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY,
            config_dir=TEST_CONFIG_DIR,
            simulation_mode=1,
        ):
            self.assertEqual(self.csc.summary_state, salobj.State.STANDBY)
            await self.assert_next_summary_state(salobj.State.STANDBY)

            invalid_files = glob.glob(os.path.join(TEST_CONFIG_DIR, "invalid_*.yaml"))
            bad_config_names = [os.path.basename(name) for name in invalid_files]
            bad_config_names.append("no_such_file.yaml")
            for bad_config_name in bad_config_names:
                with self.subTest(bad_config_name=bad_config_name):
                    with salobj.assertRaisesAckError():
                        await self.remote.cmd_start.set_start(
                            settingsToApply=bad_config_name, timeout=STD_TIMEOUT
                        )

            await self.remote.cmd_start.set_start(
                settingsToApply="all_fields", timeout=STD_TIMEOUT
            )
            self.assertEqual(self.csc.summary_state, salobj.State.DISABLED)
            await self.assert_next_summary_state(salobj.State.DISABLED)
            all_fields_path = os.path.join(TEST_CONFIG_DIR, "all_fields.yaml")
            with open(all_fields_path, "r") as f:
                all_fields_raw = f.read()
            all_fields_data = yaml.safe_load(all_fields_raw)
            for field, value in all_fields_data.items():
                self.assertEqual(getattr(self.csc.config, field), value)

    async def test_bin_script(self):
        await self.check_bin_script(name="OCPS", index=None, exe_name="run_ocps.py")

    async def test_standard_state_transitions(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=1
        ):
            await self.check_standard_state_transitions(
                settingsToApply="default",
                enabled_commands=(
                    "execute",
                    "abort_job",
                )
            )


if __name__ == "__main__":
    unittest.main()
