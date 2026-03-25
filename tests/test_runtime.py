# -*- coding: UTF-8 -*-
"""
Author:  Jacek 'Szumak' Kotlarski --<szumak@virthost.pl>
Created: 2026-03-24

Purpose: Provide regression coverage for the standalone pinger plugin runtime.
"""

import importlib.util
import sys
import unittest

from pathlib import Path
from queue import Queue
from threading import Event
from types import ModuleType
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock

from jsktoolbox.configtool import Config as ConfigTool
from jsktoolbox.logstool import LoggerClient, LoggerQueue

from libs import AppName
from libs.com.message import ThDispatcher
from libs.plugins import DispatcherAdapter, PluginContext


def _load_plugin_spec():
    """Load `get_plugin_spec()` using the same package semantics as the host."""
    repo_root = Path(__file__).resolve().parents[1]
    package_name = "aasd_plugin_pinger"
    package_module = ModuleType(package_name)
    package_module.__file__ = str((repo_root / "__init__.py").resolve())
    package_module.__package__ = package_name
    package_module.__path__ = [str(repo_root)]
    sys.modules[package_name] = package_module

    module_name = f"{package_name}.load"
    spec = importlib.util.spec_from_file_location(module_name, repo_root / "load.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot build plugin spec loader.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.get_plugin_spec


class _RecordingLogger:
    """Collect assigned log messages for assertion-friendly tests."""

    # #[CONSTRUCTOR]##################################################################
    def __init__(self) -> None:
        """Initialize empty log-message buffers."""
        self.debug_messages: List[str] = []
        self.info_messages: List[str] = []
        self.warning_messages: List[str] = []

    # #[PUBLIC PROPERTIES]############################################################
    @property
    def message_debug(self) -> str:
        """Return the most recent debug message.

        ### Returns:
        str - Most recent debug message or empty string.
        """
        if not self.debug_messages:
            return ""
        return self.debug_messages[-1]

    @message_debug.setter
    def message_debug(self, value: str) -> None:
        """Store one debug log message.

        ### Arguments:
        * value: str - Debug message.
        """
        self.debug_messages.append(value)

    @property
    def message_info(self) -> str:
        """Return the most recent info message.

        ### Returns:
        str - Most recent info message or empty string.
        """
        if not self.info_messages:
            return ""
        return self.info_messages[-1]

    @message_info.setter
    def message_info(self, value: str) -> None:
        """Store one info log message.

        ### Arguments:
        * value: str - Info message.
        """
        self.info_messages.append(value)

    @property
    def message_warning(self) -> str:
        """Return the most recent warning message.

        ### Returns:
        str - Most recent warning message or empty string.
        """
        if not self.warning_messages:
            return ""
        return self.warning_messages[-1]

    @message_warning.setter
    def message_warning(self, value: str) -> None:
        """Store one warning log message.

        ### Arguments:
        * value: str - Warning message.
        """
        self.warning_messages.append(value)


class _SinglePassStopEvent(Event):
    """Stop the runtime after one loop iteration."""

    # #[CONSTRUCTOR]##################################################################
    def __init__(self) -> None:
        """Initialize the stop flag in the running state."""
        Event.__init__(self)

    # #[PUBLIC METHODS]################################################################
    def wait(self, timeout: Optional[float] = None) -> bool:
        """Set the stop flag after the current loop cycle.

        ### Arguments:
        * timeout: Optional[float] - Unused compatibility argument.

        ### Returns:
        bool - Always `True`.
        """
        del timeout
        self.set()
        return True


class _FakePinger:
    """Provide deterministic ICMP answers for plugin runtime tests."""

    RESPONSES: Dict[str, List[bool]] = {}

    # #[CONSTRUCTOR]##################################################################
    def __init__(self, timeout: int = 1) -> None:
        """Store compatibility arguments expected by the real helper.

        ### Arguments:
        * timeout: int - Unused compatibility argument.
        """
        del timeout

    # #[PUBLIC METHODS]################################################################
    def is_alive(self, ip: str) -> bool:
        """Return the next canned response for the selected host.

        ### Arguments:
        * ip: str - Monitored host address.

        ### Returns:
        bool - Next canned ICMP result.
        """
        values = self.RESPONSES.get(ip, [])
        if not values:
            return False
        if len(values) == 1:
            return values[0]
        return values.pop(0)


class _InterruptingPinger:
    """Set the stop flag during the first ICMP probe."""

    # #[CONSTRUCTOR]##################################################################
    def __init__(self, stop_event: Event) -> None:
        """Store the stop event used by the runtime.

        ### Arguments:
        * stop_event: Event - Runtime stop event.
        """
        self.call_count = 0
        self._stop_event = stop_event

    # #[PUBLIC METHODS]################################################################
    def is_alive(self, ip: str) -> bool:
        """Interrupt the runtime after the first ICMP probe.

        ### Arguments:
        * ip: str - Monitored host address.

        ### Returns:
        bool - Always `False`.
        """
        del ip
        self.call_count += 1
        self._stop_event.set()
        return False


class TestPingerRuntime(unittest.TestCase):
    """Cover the standalone pinger runtime behavior."""

    # #[PRIVATE METHODS]###############################################################
    def __build_context(self, instance_name: str) -> PluginContext:
        """Build a minimal plugin context for runtime tests.

        ### Arguments:
        * instance_name: str - Runtime instance name.

        ### Returns:
        PluginContext - Minimal context object accepted by the runtime factory.
        """
        qlog = LoggerQueue()
        qcom: Queue = Queue()
        dispatcher = ThDispatcher(
            qlog=qlog,
            qcom=qcom,
            debug=False,
            verbose=False,
        )
        adapter = DispatcherAdapter(qcom=qcom, dispatcher=dispatcher)
        return PluginContext(
            app_meta=AppName(app_name="AASd", app_version="2.4.2-DEV"),
            config={},
            config_handler=ConfigTool("/tmp/unused.conf", "AASd", auto_create=True),
            debug=False,
            dispatcher=adapter,
            instance_name=instance_name,
            logger=LoggerClient(queue=qlog, name=instance_name),
            plugin_id=f"test.{instance_name}",
            plugin_kind="worker",
            qlog=qlog,
            verbose=False,
        )

    # #[PUBLIC METHODS]################################################################
    def test_01_should_import_plugin_spec_from_load_module(self) -> None:
        """Load the plugin spec through the entry-point module."""
        get_plugin_spec = _load_plugin_spec()
        plugin_spec = get_plugin_spec()

        self.assertEqual(plugin_spec.plugin_id, "pinger.worker")
        self.assertEqual(plugin_spec.plugin_name, "plugin_worker_pinger")

    def test_02_should_log_state_changes_without_dispatch_channels(self) -> None:
        """Log down and up transitions even when dispatcher targets are absent."""
        context = self.__build_context("pinger_transitions")
        logger = _RecordingLogger()
        context.logger = logger  # type: ignore[assignment]
        context.dispatcher.publish = MagicMock()
        context.config = {
            "at_channel": [],
            "hosts": ["192.0.2.1"],
            "inform_on_alive": False,
            "inform_on_down": True,
            "inform_on_still_down": False,
            "inform_on_up": True,
            "message_channel": [],
            "message_on_alive": "Host {host} is alive for {status_time}.",
            "message_on_down": "Host {host} is down for {status_time}.",
            "message_on_still_down": "Host {host} is still down for {status_time}.",
            "message_on_up": "Host {host} is up for {status_time}.",
            "ping_count": 1,
            "ping_interval": 1,
        }

        runtime = _load_plugin_spec()().runtime_factory(context)
        runtime._pinger = _FakePinger()  # type: ignore[assignment]

        _FakePinger.RESPONSES = {"192.0.2.1": [False]}
        runtime._stop_event = _SinglePassStopEvent()
        runtime.run()

        _FakePinger.RESPONSES = {"192.0.2.1": [True]}
        runtime._stop_event = _SinglePassStopEvent()
        runtime.run()

        self.assertTrue(
            any("Host 192.0.2.1 is down" in item for item in logger.warning_messages)
        )
        self.assertTrue(
            any("Host 192.0.2.1 is up" in item for item in logger.info_messages)
        )
        context.dispatcher.publish.assert_not_called()

    def test_03_should_emit_alive_on_every_cycle_when_enabled(self) -> None:
        """Log repeated alive messages when `inform_on_alive` is enabled."""
        context = self.__build_context("pinger_alive")
        logger = _RecordingLogger()
        context.logger = logger  # type: ignore[assignment]
        context.dispatcher.publish = MagicMock()
        context.config = {
            "at_channel": [],
            "hosts": ["192.0.2.2"],
            "inform_on_alive": True,
            "inform_on_down": False,
            "inform_on_still_down": False,
            "inform_on_up": False,
            "message_channel": [],
            "message_on_alive": "Host {host} is alive for {status_time}.",
            "message_on_down": "Host {host} is down for {status_time}.",
            "message_on_still_down": "Host {host} is still down for {status_time}.",
            "message_on_up": "Host {host} is up for {status_time}.",
            "ping_count": 1,
            "ping_interval": 1,
        }

        runtime = _load_plugin_spec()().runtime_factory(context)
        runtime._pinger = _FakePinger()  # type: ignore[assignment]

        _FakePinger.RESPONSES = {"192.0.2.2": [True]}
        runtime._stop_event = _SinglePassStopEvent()
        runtime.run()

        _FakePinger.RESPONSES = {"192.0.2.2": [True]}
        runtime._stop_event = _SinglePassStopEvent()
        runtime.run()

        alive_messages = [
            item for item in logger.info_messages if "Host 192.0.2.2 is alive" in item
        ]
        self.assertEqual(len(alive_messages), 2)
        context.dispatcher.publish.assert_not_called()

    def test_04_should_emit_still_down_on_repeated_failures(self) -> None:
        """Log repeated down notifications when `inform_on_still_down` is enabled."""
        context = self.__build_context("pinger_still_down")
        logger = _RecordingLogger()
        context.logger = logger  # type: ignore[assignment]
        context.dispatcher.publish = MagicMock()
        context.config = {
            "at_channel": [],
            "hosts": ["192.0.2.3"],
            "inform_on_alive": False,
            "inform_on_down": True,
            "inform_on_still_down": True,
            "inform_on_up": False,
            "message_channel": [],
            "message_on_alive": "Host {host} is alive for {status_time}.",
            "message_on_down": "Host {host} is down for {status_time}.",
            "message_on_still_down": "Host {host} is still down for {status_time}.",
            "message_on_up": "Host {host} is up for {status_time}.",
            "ping_count": 1,
            "ping_interval": 1,
        }

        runtime = _load_plugin_spec()().runtime_factory(context)
        runtime._pinger = _FakePinger()  # type: ignore[assignment]

        _FakePinger.RESPONSES = {"192.0.2.3": [False]}
        runtime._stop_event = _SinglePassStopEvent()
        runtime.run()

        _FakePinger.RESPONSES = {"192.0.2.3": [False]}
        runtime._stop_event = _SinglePassStopEvent()
        runtime.run()

        self.assertTrue(
            any(
                "Host 192.0.2.3 is still down" in item
                for item in logger.warning_messages
            )
        )
        context.dispatcher.publish.assert_not_called()

    def test_05_should_stop_without_checking_remaining_hosts(self) -> None:
        """Exit the loop promptly after the stop flag is set."""
        context = self.__build_context("pinger_interrupt")
        logger = _RecordingLogger()
        context.logger = logger  # type: ignore[assignment]
        context.dispatcher.publish = MagicMock()
        context.debug = True
        context.config = {
            "at_channel": [],
            "hosts": ["192.0.2.10", "192.0.2.11"],
            "inform_on_alive": False,
            "inform_on_down": True,
            "inform_on_still_down": False,
            "inform_on_up": False,
            "message_channel": [],
            "message_on_alive": "Host {host} is alive for {status_time}.",
            "message_on_down": "Host {host} is down for {status_time}.",
            "message_on_still_down": "Host {host} is still down for {status_time}.",
            "message_on_up": "Host {host} is up for {status_time}.",
            "ping_count": 3,
            "ping_interval": 1,
        }

        runtime = _load_plugin_spec()().runtime_factory(context)
        stop_event = Event()
        runtime._stop_event = stop_event
        runtime._pinger = _InterruptingPinger(stop_event=stop_event)  # type: ignore[assignment]

        runtime.run()

        self.assertEqual(runtime._pinger.call_count, 1)  # type: ignore[union-attr]
        self.assertFalse(
            any("192.0.2.11" in item for item in logger.debug_messages)
        )
        context.dispatcher.publish.assert_not_called()


# #[EOF]#######################################################################
