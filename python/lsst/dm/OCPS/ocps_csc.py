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

__all__ = ["OcpsCsc", "CONFIG_SCHEMA"]

import asyncio
import json
import random
import requests
import types
import yaml

from lsst.ts import salobj
from . import __version__

CONFIG_SCHEMA = yaml.safe_load(
    """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst/dm_OCPS/blob/master/schema/OCPS.yaml
# title must end with one or more spaces followed by the schema version, which must begin with "v"
title: OCPS v2
description: Schema for OCPS configuration files
type: object
properties:
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
  triggers:
    description: Events and the pipelines they should trigger
    type: array
    items:
      type: object
      properties:
        csc:
          description: CSC from which the event will arrive
          type: string
        event:
          description: Name of the event that should be waited for
          type: string
        version:
          description: EUPS tag to setup
          type: string
        pipeline:
          description: Pipeline to execute upon receipt
          type: string
        data_query_expr:
          description: Expression to determine data query
          type: string
      required: ["csc", "event", "pipeline", "data_query_expr"]
      additionalProperties: false
required:
  - url
  - poll_interval
  - butler
  - output_glob
additionalProperties: false
"""
)


class OcpsCsc(salobj.ConfigurableCsc):
    """CSC for the OCS-Controlled Pipeline Service.

    This CSC executes pipelines on specified data.

    Parameters
    ----------
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
        config_dir=None,
        initial_state=salobj.State.STANDBY,
        settings_to_apply="",
        simulation_mode=0,
    ):
        self.config = None
        self.simulated_jobs = set()
        super().__init__(
            "OCPS",
            index=0,
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            initial_state=initial_state,
            settings_to_apply=settings_to_apply,
            simulation_mode=simulation_mode,
        )
        self.cmd_execute.allow_multiple_callbacks = True
        if hasattr(self.config, "triggers"):
            self.trigger_remotes = []
            for trigger in self.config.triggers:
                remote = salobj.Remote(
                    domain=self.domain,
                    name=trigger.csc,
                    include=[trigger.event],
                )
                event = remote.getattr(trigger.event)
                event.callback = self.gen_event_callback(trigger)
                self.trigger_remotes.append(remote)

    def gen_event_callback(self, trigger):
        """Return a callback that triggers a pipeline on an event.

        Parameters
        ----------
        trigger: types.SimpleNamespace
            Must contain version, pipeline, data_query_expr attributes

        Notes
        -----
        version: str
            Science Pipelines version as an EUPS tag
        pipeline: str
            URL of pipeline YAML
        data_query_expr: str
            String to generate a data query expression for "pipetask run",
            formatted with ``.format(data=data)`` so ``{data.attr}``
            substitutions can be used
        """
        async def event_callback(self, data):
            self.log.info(f"Event {trigger.event} occurred: {data}")
            data.version = trigger.version
            data.pipeline = trigger.pipeline
            data.config = ""
            data.data_query = trigger.data_query_expr.format(event=data)
            self.log.info(f"Calling _execute with {data}")
            # TODO DM-30032: complete event-triggered execution
            # self._execute(data)

        return event_callback

    async def do_execute(self, data):
        """Implement the ``execute`` command.

        Parameters
        ----------
        data: types.SimpleNamespace
            Must contain version, pipeline, config, and data_query attributes
        """
        self.assert_enabled("execute")
        self.log.info(f"execute command with {data}")
        await self._execute(data)

    async def _execute(self, data):
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
        if self.simulation_mode == 0:
            # Real command.
            run_options = ""
            if hasattr(self.config, "input_collection"):
                run_options = f"-i {self.config.input_collection}"
            payload_env = dict(
                EUPS_TAG=data.version,
                PIPELINE_URL=data.pipeline,
                BUTLER_REPO=self.config.butler,
                RUN_OPTIONS=" ".join(run_options, data.config),
                OUTPUT_GLOB=self.config.output_glob,
                DATA_QUERY=data.data_query,
            )
            payload = dict(
                command="pipetask.sh",
                url="https://github.com/uws_scripts",
                commit_ref="master",
                run_id=data.private_seqNum,
                replicas=1,
                environment=[dict(key=k, val=v) for k, v in payload_env]
            )
            self.log.info(f"PUT: {payload}")
            result = self.connection.put(f"{self.config.url}/job", json=payload)
            result.raise_for_status()
            self.log.info(f"PUT result: {result.data}")
            job_id = result.json().job_id
            status_url = f"{self.config.url}/job/{job_id}"
        else:
            # Simulation mode.
            # Rather than prepare a PUT request, simulate one with a special
            # URL scheme.
            if data.pipeline not in ("true.yaml", "false.yaml", "fault.yaml"):
                raise salobj.ExpectedError(
                    f"Unknown (simulated) pipeline: {data.pipeline}"
                )
            job_id = f"{data.pipeline}-{salobj.current_tai()}"
            status_url = f"ocps://{job_id}"
            self.log.info(f"Simulated PUT result: {status_url}")
            self.simulated_jobs.add(job_id)

        payload = json.dumps(dict(job_id=job_id))
        # TODO DM-30032: change to a custom event
        self.cmd_execute.ack_in_progress(data, timeout=600.0, result=payload)
        self.log.info(f"Ack in progress: {payload}")
        self.log.info(f"Starting async wait: {status_url}")

        while True:
            if self.simulation_mode != 0:
                # Simulation mode.
                # Rather than poll for pipeline status, simulate an appropriate
                # response.
                if not status_url.startswith("ocps://"):
                    raise salobj.ExpectedError(f"Invalid simulation URL: {status_url}")
                await asyncio.sleep(abs(random.normalvariate(10, 4)))
                self.log.info(f"Simulating result for {job_id}")
                if job_id not in self.simulated_jobs:
                    raise salobj.ExpectedError(f"No such job id: {job_id}")
                self.simulated_jobs.remove(job_id)
                if job_id.startswith("true.yaml-"):
                    payload = json.dumps(dict(result=True))
                    self.evt_job_result.set_put(
                        job_id=job_id, exit_code=0, result=payload
                    )
                elif job_id.startswith("false.yaml-"):
                    payload = json.dumps(dict(result=False))
                    self.evt_job_result.set_put(
                        job_id=job_id, exit_code=0, result=payload
                    )
                elif job_id.startswith("fault.yaml-"):
                    self.fault(
                        code=2, report="404 Simulation cannot contact execution service"
                    )
                    raise salobj.ExpectedError("Failed to connect (simulated)")
                else:
                    raise salobj.ExpectedError(
                        f"Unknown (simulated) pipeline: {job_id}"
                    )
                return

            self.log.info(f"GET: {status_url}")
            result = self.connection.get(status_url)
            result.raise_for_status()
            response = result.json()
            if response.status != "ok":
                raise salobj.ExpectedError(f"GET {status_url} failed: {response}")
            job_id = status_url[-status_url.rindex("/") :]
            if response.job.state == "running":
                self.log.debug(f"{status_url} sleeping for {self.config.poll_interval}")
                await asyncio.sleep(self.config.poll_interval)
            else:
                self.log.info(f"{status_url} result: {response}")
                self.evt_job_result.set_put(
                    job_id=job_id, exit_code=0, result=response.job
                )
                return

    async def do_abort_job(self, data):
        """Implement the ``abort_job`` command.

        Parameters
        ----------
        data: types.SimpleNamespace
            Must contain job_id attribute.
        """
        self.assert_enabled("abort_job")
        self.log.info(f"abort_job command with {data}")
        if self.simulation_mode == 0:
            self.log.info(f"DELETE: {data.job_id}")
            result = self.connection.delete(f"{self.config.url}/job/{data.job_id}")
            result.raise_for_status()
            self.evt_job_result.set_put(
                job_id=data.job_id, exit_code=255, result=result.data
            )
            self.log.info(f"Abort result: {result.data}")
        else:
            if data.job_id in self.simulated_jobs:
                self.simulated_jobs.remove(data.job_id)
                payload = json.dumps(dict(abort_time=salobj.current_tai()))
                self.evt_job_result.set_put(
                    job_id=data.job_id, exit_code=255, result=payload
                )
                self.log.info(f"Abort result: {payload}")
            else:
                raise salobj.ExpectedError("No such job id: {data.job_id}")

    @staticmethod
    def get_config_pkg():
        return "dm_config_ocps"

    async def configure(self, config: types.SimpleNamespace):
        self.log.info(f"Configuring with {config}")
        self.config = config
        if self.simulation_mode == 0:
            self.connection = requests.Session()
