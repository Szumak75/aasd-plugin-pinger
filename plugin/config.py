# -*- coding: UTF-8 -*-
"""
Worker pinger plugin configuration keys.

Author:  Jacek 'Szumak' Kotlarski --<szumak@virthost.pl>
Created: 2026-03-24

Purpose: Provide plugin-specific config keys for the worker pinger plugin.
"""

from jsktoolbox.attribtool import ReadOnlyClass


class Keys(object, metaclass=ReadOnlyClass):
    """Define plugin-specific configuration keys."""

    # #[CONSTANTS]####################################################################
    HOSTS: str = "hosts"
    PING_INTERVAL: str = "ping_interval"


# #[EOF]#######################################################################
