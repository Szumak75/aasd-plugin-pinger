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
    INFORM_ON_ALIVE: str = "inform_on_alive"
    INFORM_ON_DOWN: str = "inform_on_down"
    INFORM_ON_STILL_DOWN: str = "inform_on_still_down"
    INFORM_ON_UP: str = "inform_on_up"
    MESSAGE_ON_ALIVE: str = "message_on_alive"
    MESSAGE_ON_DOWN: str = "message_on_down"
    MESSAGE_ON_STILL_DOWN: str = "message_on_still_down"
    MESSAGE_ON_UP: str = "message_on_up"
    PING_COUNT: str = "ping_count"
    PING_INTERVAL: str = "ping_interval"


# #[EOF]#######################################################################
