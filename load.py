# -*- coding: UTF-8 -*-
"""
Worker pinger plugin entry point.

Author:  Jacek 'Szumak' Kotlarski --<szumak@virthost.pl>
Created: 2026-03-24

Purpose: Provide a starter `load.py` for standalone AASd worker plugins.
"""

from libs.plugins import PluginCommonKeys, PluginKind, PluginSpec
from libs.templates import PluginConfigField, PluginConfigSchema

from .plugin import __version__
from .plugin.config import Keys
from .plugin.runtime import WorkerTemplateRuntime


def get_plugin_spec() -> PluginSpec:
    """Return the plugin spec for the worker pinger plugin.

    ### Returns:
    PluginSpec - Plugin manifest.
    """
    schema = PluginConfigSchema(
        title="Worker pinger plugin.",
        description=(
            "Starter worker pinger plugin showing the recommended "
            "AASd plugin layout."
        ),
        fields=[
            PluginConfigField(
                name=PluginCommonKeys.MESSAGE_CHANNEL,
                field_type=list,
                default=[],
                required=True,
                description=(
                    "Interval-based notification targets used for emitted "
                    "reachability events."
                ),
            ),
            PluginConfigField(
                name=PluginCommonKeys.AT_CHANNEL,
                field_type=list,
                default=[],
                required=False,
                description=(
                    "Cron-like notification targets used for emitted "
                    "reachability events."
                ),
            ),
            PluginConfigField(
                name=Keys.PING_INTERVAL,
                field_type=int,
                default=5,
                required=True,
                description="Interval in seconds between pings.",
            ),
            PluginConfigField(
                name=Keys.PING_COUNT,
                field_type=int,
                default=3,
                required=True,
                description="Number of ping attempts per host.",
            ),
            PluginConfigField(
                name=Keys.HOSTS,
                field_type=list,
                default=[],
                required=True,
                description="List of IP hosts to ping.",
            ),
            PluginConfigField(
                name=Keys.INFORM_ON_ALIVE,
                field_type=bool,
                default=False,
                required=False,
                description="Whether to inform when a host is alive.",
            ),
            PluginConfigField(
                name=Keys.MESSAGE_ON_ALIVE,
                field_type=str,
                default="Host {host} is alive for {status_time}.",
                required=False,
                description="Message template for alive hosts.",
            ),
            PluginConfigField(
                name=Keys.INFORM_ON_UP,
                field_type=bool,
                default=True,
                required=False,
                description="Whether to inform when a host goes up.",
            ),
            PluginConfigField(
                name=Keys.MESSAGE_ON_UP,
                field_type=str,
                default="Host {host} is up for {status_time}.",
                required=False,
                description="Message template for hosts that went up.",
            ),
            PluginConfigField(
                name=Keys.INFORM_ON_DOWN,
                field_type=bool,
                default=True,
                required=False,
                description="Whether to inform when a host goes down.",
            ),
            PluginConfigField(
                name=Keys.MESSAGE_ON_DOWN,
                field_type=str,
                default="Host {host} is down for {status_time}.",
                required=False,
                description="Message template for hosts that went down.",
            ),
            PluginConfigField(
                name=Keys.INFORM_ON_STILL_DOWN,
                field_type=bool,
                default=False,
                required=False,
                description="Whether to inform when a host remains down.",
            ),
            PluginConfigField(
                name=Keys.MESSAGE_ON_STILL_DOWN,
                field_type=str,
                default="Host {host} is still down for {status_time}.",
                required=False,
                description="Message template for hosts that remain down.",
            ),
        ],
    )
    return PluginSpec(
        api_version=1,
        config_schema=schema,
        plugin_id="pinger.worker",
        plugin_kind=PluginKind.WORKER,
        plugin_name="plugin_worker_pinger",
        runtime_factory=WorkerTemplateRuntime,
        description="Starter AASd worker pinger plugin.",
        plugin_version=__version__,
    )




# #[EOF]#######################################################################
