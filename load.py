# -*- coding: UTF-8 -*-
"""
Worker pinger plugin entry point.

Author:  Jacek 'Szumak' Kotlarski --<szumak@virthost.pl>
Created: 2026-03-24

Purpose: Provide a starter `load.py` for standalone AASd worker plugins.
"""

from libs.plugins import PluginCommonKeys, PluginKind, PluginSpec
from libs.templates import PluginConfigField, PluginConfigSchema

from plugin.config import Keys
from plugin.runtime import WorkerTemplateRuntime


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
                default=[1],
                required=True,
                description="Dispatcher channel used for the startup message.",
            ),
            PluginConfigField(
                name=Keys.PING_INTERVAL,
                field_type=int,
                default=5,
                required=True,
                description="Interval in seconds between pings.",
            ),
            PluginConfigField(
                name=Keys.HOSTS,
                field_type=list,
                default=[],
                required=True,
                description="List of hosts to ping.",
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
    )


# #[EOF]#######################################################################
