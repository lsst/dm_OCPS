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
# You should have received a copy of the GNU General Public License

__all__ = ["OcpsCsc", "run_ocps", "CONFIG_SCHEMA"]

import asyncio
import json
import logging
import random
import types
from typing import Optional, Set

import requests  # type: ignore
import yaml
from lsst.ts import salobj
from lsst.ts.idl.enums.OCPS import SalIndex
from lsst.ts.utils import current_tai

from . import __version__

CONFIG_SCHEMA = yaml.safe_load(
    """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst/dm_OCPS/blob/main/schema/OCPS.yaml
# title must end with one or more spaces followed by the schema version, which must begin with "v"
title: OCPS v4
description: Schema for OCPS configuration files
type: object
properties:
  instances:
    type: array
    description: Configuration for each OCPS instance
    minItem: 1
    items:
      type: object
      properties:
        sal_index:
          type: integer
          description: SAL index of OCPS instance
        instance:
          description: >
            Name of the OCPS instance this configuration is for.
            Primarily for documentation purposes, as the sal_index determines
            which configuration is loaded.
          type: string
        url:
          description: URL of the REST API endpoint of the execution service
          type: string
          format: url
        poll_interval:
          description: Time between polls for status of executing pipelines (sec)
          type: number
          exclusiveMinimum: 0
        butler:
          description: Path/URI of Butler repo
          type: string
        input_collection:
          description: Name of default input collection (optional)
          type: string
        output_glob:
          description: Glob pattern for output dataset types
          type: string
      required:
        - sal_index
        - instance
        - url
        - poll_interval
        - butler
        - output_glob
      additionalProperties: false
required:
  - instances
additionalProperties: false
"""
)

DONE_PHASES = ["completed", "error", "aborted", "unknown"]


class OcpsCsc(salobj.ConfigurableCsc):
    """CSC for the OCS-Controlled Pipeline Service.

    This CSC executes pipelines on specified data.

    Parameters
    ----------
    index: `int` or `lsst.ts.idl.enums.OCPS.SalIndex`
        CSC SAL index.
    simulation_mode: `int` (optional)
        Simulation mode.

    Raises
    ------
    salobj.ExpectedError
        If simulation_mode is invalid.

    Notes
    -----
    **Simulation Modes**

    Supported simulation modes:

    * 0: regular operation
    * 1: simulation mode accepts execute commands with these pipeline names:
      * true.yaml always succeeds
      * false.yaml always fails
      * fault.yaml causes a fault

    ** Error Codes**

    * 1: could not connect to the execution service endpoint
    * 2: pipeline failed in synchronous mode
    """

    valid_simulation_modes = (0, 1)
    version = __version__

    def __init__(
        self,
        index: int,
        config_dir: Optional[str] = None,
        initial_state: salobj.State = salobj.State.STANDBY,
        override: str = "",
        simulation_mode: int = 0,
    ):
        self.config: Optional[types.SimpleNamespace] = None
        self.simulated_jobs: Set[str] = set()
        super().__init__(
            "OCPS",
            index=index,
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            initial_state=initial_state,
            override=override,
            simulation_mode=simulation_mode,
        )
        self.cmd_execute.allow_multiple_callbacks = True
        self.log.addHandler(logging.StreamHandler())

    async def do_execute(self, data: types.SimpleNamespace) -> None:
        """Implement the ``execute`` command.

        Parameters
        ----------
        data: types.SimpleNamespace
            Must contain version, pipeline, config, and data_query attributes
        """
        self.assert_enabled("execute")
        self.log.info(f"execute command with {data}")
        await self._execute(data)

    async def _execute(self, data: types.SimpleNamespace) -> None:
        """Submit a request for execution to the back-end REST API.

        Parameters
        ----------
        data: types.SimpleNamespace
            Must contain version, pipeline, config, data_query attributes

        Notes
        -----
        version: str
            Science Pipelines version as an EUPS tag
        pipeline: str
            URL of pipeline YAML
        config: str
            Command line options for "pipetask run"
        data_query: str
            Data query expression for "pipetask run"

        The ``data.config`` attribute is expected to contain ``-i`` options
        beyond the default OODS input collection and ``-c`` options to
        override configuration values.
        """
        if self.config is None:
            raise salobj.ExpectedError("Configuration not set")
        if self.simulation_mode == 0:
            # Real command.
            if hasattr(data, "prereq_jobs") and data.prereq_jobs:
                await self._wait_for_prereqs(data.prereq_jobs.split(","))

            run_options = ""
            if hasattr(self.config, "input_collection"):
                run_options = f"-i {self.config.input_collection}"
            payload_env = dict(
                IMAGE_TAG=data.version,
                PIPELINE_URL=data.pipeline,
                BUTLER_REPO=self.config.butler,
                RUN_OPTIONS=" ".join((run_options, data.config)),
                OUTPUT_GLOB=self.config.output_glob,
                DATA_QUERY=data.data_query,
            )
            if hasattr(data, "output_dataset_types") and data.output_dataset_types:
                payload_env["OUTPUT_GLOB"] = data.output_dataset_types

            run_id = str(data.private_seqNum)
            json_payload = dict(
                run_id=run_id,
                command="cd $JOB_SOURCE_DIR && bash bin/pipetask.sh",
                url="https://github.com/lsst-dm/uws_scripts",
                commit_ref="tickets/DM-44197",
                environment=[dict(name=k, value=v) for k, v in payload_env.items()],
            )
            self.log.info(f"PUT {self.config.url}/job: {json_payload}")
            result = self.connection.put(f"{self.config.url}/job", json=json_payload)
            result.raise_for_status()
            self.log.info(f"PUT {result.status_code} result: {result.text}")
            response = result.json()
            job_id = response["jobId"]
        else:
            # Simulation mode.
            # Rather than prepare a PUT request, simulate one with a special
            # URL scheme.
            if data.pipeline not in ("true.yaml", "false.yaml", "fault.yaml"):
                raise salobj.ExpectedError(
                    f"Unknown (simulated) pipeline: {data.pipeline}"
                )
            job_id = f"{data.pipeline}-{current_tai()}"
            self.log.info(f"Simulated PUT result: {job_id}")
            self.simulated_jobs.add(job_id)

        payload = json.dumps(dict(job_id=job_id))
        # TODO DM-30032: change to a custom event
        await self.cmd_execute.ack_in_progress(data, timeout=600.0, result=payload)
        self.log.info(f"Ack in progress: {payload}")
        self.log.info(f"Starting async wait: {job_id}")

        while True:
            if self.simulation_mode != 0:
                # Simulation mode.
                # Rather than poll for pipeline status, simulate an appropriate
                # response.
                await asyncio.sleep(abs(random.normalvariate(10, 4)))
                self.log.info(f"Simulating result for {job_id}")
                if job_id not in self.simulated_jobs:
                    raise salobj.ExpectedError(f"No such job id: {job_id}")
                self.simulated_jobs.remove(job_id)
                if job_id.startswith("true.yaml-"):
                    payload = json.dumps(dict(result=True))
                    await self.evt_job_result.set_write(
                        job_id=job_id, exit_code=0, result=payload
                    )
                elif job_id.startswith("false.yaml-"):
                    payload = json.dumps(dict(result=False))
                    await self.evt_job_result.set_write(
                        job_id=job_id, exit_code=0, result=payload
                    )
                elif job_id.startswith("fault.yaml-"):
                    await self.fault(
                        code=2, report="404 Simulation cannot contact execution service"
                    )
                    raise salobj.ExpectedError("Failed to connect (simulated)")
                else:
                    raise salobj.ExpectedError(
                        f"Unknown (simulated) pipeline: {job_id}"
                    )
                return

            response = await self.get_job_status(job_id)
            if response["jobId"] != job_id:
                raise salobj.ExpectedError(
                    f"Job ID mismatch: got {response['jobId']} instead of {job_id}"
                )
            if response["runId"] != run_id:
                raise salobj.ExpectedError(
                    f"Run ID mismatch: got {response['runId']} instead of {run_id}"
                )
            if response["phase"] in DONE_PHASES:
                exit_code = 1 if response["phase"] != "completed" else 0
                await self.evt_job_result.set_write(
                    job_id=job_id, exit_code=exit_code, result=result.text
                )
                return
            else:
                self.log.debug(
                    f"{job_id} phase {response['phase']}"
                    f" sleeping for {self.config.poll_interval}"
                )
                await asyncio.sleep(self.config.poll_interval)

    async def get_job_status(self, job_id: str) -> dict:
        """Retrieve the status of a job submitted to the UWS backend.

        Parameters
        ----------
        job_id: str
            The job id returned from a submission to the UWS.

        Returns
        -------
        response: `dict`-like
            The status response, decoded from JSON.

        Raises
        ------
        requests.exceptions.HTTPError
            On any failure.
        """
        if self.config is None:
            raise salobj.ExpectedError("Configuration not set")
        status_url = f"{self.config.url}/job/{job_id}"
        self.log.info(f"GET: {status_url}")
        result = self.connection.get(status_url)
        result.raise_for_status()
        self.log.info(f"{status_url} result: {result.text}")
        response = result.json()
        return response

    async def _wait_for_prereqs(self, jobs_list: list[str]) -> None:
        """Wait for completion of a given list of prerequisite jobs.

        Note that completion does not require success.

        Parameters
        ----------
        jobs_list: `list` [`str`]
            A list of job ids to wait for.
        """
        if self.config is None:
            raise salobj.ExpectedError("Configuration not set")
        for job_id in jobs_list:
            while True:
                try:
                    response = await self.get_job_status(job_id)
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        # This job doesn't exist, stop waiting for it
                        self.log.warn(f"Prerequisite job {job_id} does not exist")
                        break
                    else:
                        raise
                if response["jobId"] != job_id:
                    raise salobj.ExpectedError(
                        f"Job ID mismatch: got {response['jobId']} instead of {job_id}"
                    )
                if response["phase"] in DONE_PHASES:
                    # Job is done, stop waiting for it
                    break
                else:
                    self.log.debug(
                        f"Prereq job {job_id} phase {response['phase']}"
                        f" sleeping for {self.config.poll_interval}"
                    )
                    await asyncio.sleep(self.config.poll_interval)

    async def do_abort_job(self, data: types.SimpleNamespace) -> None:
        """Implement the ``abort_job`` command.

        Parameters
        ----------
        data: types.SimpleNamespace
            Must contain job_id attribute.
        """
        if self.config is None:
            raise salobj.ExpectedError("Configuration not set")
        self.assert_enabled("abort_job")
        self.log.info(f"abort_job command with {data}")
        if self.simulation_mode == 0:
            self.log.info(f"DELETE: {data.job_id}")
            result = self.connection.delete(f"{self.config.url}/job/{data.job_id}")
            result.raise_for_status()
            self.log.info(f"Abort result: {result.text}")
            await self.evt_job_result.set_write(
                job_id=data.job_id, exit_code=255, result=result.text
            )
        else:
            if data.job_id in self.simulated_jobs:
                self.simulated_jobs.remove(data.job_id)
                payload = json.dumps(dict(abort_time=current_tai()))
                await self.evt_job_result.set_write(
                    job_id=data.job_id, exit_code=255, result=payload
                )
                self.log.info(f"Abort result: {payload}")
            else:
                raise salobj.ExpectedError("No such job id: {data.job_id}")

    @staticmethod
    def get_config_pkg() -> str:
        return "dm_config_ocps"

    async def configure(self, config: types.SimpleNamespace) -> None:
        self.config = None
        for c in config.instances:
            if SalIndex(c["sal_index"]) == self.salinfo.index:
                if self.config is not None:
                    raise salobj.ExpectedError(
                        f"Configuration instance {self.config} already"
                        f" exists when {c} is seen"
                    )
                else:
                    self.config = types.SimpleNamespace(**c)
        if self.config is None:
            raise salobj.ExpectedError(
                f"No configuration found for {self.salinfo.index}"
            )
        index = SalIndex(self.salinfo.index)
        if index != SalIndex[self.config.instance]:
            raise salobj.ExpectedError(
                f"Configuration instance '{self.config.instance}'"
                f" does not match CSC index '{index!r}'"
            )
        self.log.info(f"Configuring with {self.config}")
        if self.simulation_mode == 0:
            self.connection = requests.Session()


def run_ocps() -> None:
    """Run the OCPS CSC."""
    asyncio.run(OcpsCsc.amain(index=SalIndex))
