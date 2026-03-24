# -*- coding: UTF-8 -*-
"""
Worker pinger plugin runtime.

Author:  Jacek 'Szumak' Kotlarski --<szumak@virthost.pl>
Created: 2026-03-24

Purpose: Monitor configured hosts with ICMP checks and emit state notifications.
"""

from dataclasses import dataclass
from datetime import timedelta
from threading import Event, Thread
from time import time
from typing import ClassVar, Dict, List, Optional

from libs.com.message import Message
from libs.plugins import (
    NotificationScheduler,
    PluginCommonKeys,
    PluginContext,
    PluginHealth,
    PluginHealthSnapshot,
    PluginState,
    PluginStateSnapshot,
    ThPluginMixin,
)
from libs.tools import Pinger

from .config import Keys


@dataclass
class _HostStatus:
    """Store the current reachability state for one monitored host."""

    is_alive: bool
    status_since: int


class WorkerTemplateRuntime(Thread, ThPluginMixin):
    """Monitor configured hosts and emit state-dependent notifications."""

    _host_status_cache: ClassVar[Dict[str, Dict[str, _HostStatus]]] = {}
    _notifications: Optional[NotificationScheduler] = None
    _pinger: Optional[Pinger] = None

    # #[CONSTRUCTOR]##################################################################
    def __init__(self, context: PluginContext) -> None:
        """Initialize the worker pinger runtime.

        ### Arguments:
        * context: PluginContext - Plugin runtime context.
        """
        Thread.__init__(self, name=context.instance_name)
        self.daemon = True
        self._context = context
        self._health = PluginHealthSnapshot(health=PluginHealth.UNKNOWN)
        self._notifications = NotificationScheduler.from_config(context.config)
        self._pinger = Pinger(timeout=1)
        self._state = PluginStateSnapshot(state=PluginState.CREATED)
        self._stop_event = Event()

    # #[PUBLIC METHODS]################################################################
    def health(self) -> PluginHealthSnapshot:
        """Return the current health snapshot.

        ### Returns:
        PluginHealthSnapshot - Current plugin health snapshot.
        """
        health: Optional[PluginHealthSnapshot] = self._health
        if health is None:
            return PluginHealthSnapshot(
                health=PluginHealth.UNKNOWN,
                message="Health snapshot is not initialized.",
            )
        return health

    def initialize(self) -> None:
        """Prepare the runtime before startup."""
        self._state = PluginStateSnapshot(state=PluginState.INITIALIZED)

    def run(self) -> None:
        """Run periodic ICMP checks for all configured hosts."""
        stop_event: Optional[Event] = self._stop_event
        if stop_event is None:
            self._health = PluginHealthSnapshot(
                health=PluginHealth.UNHEALTHY,
                last_error_at=int(time()),
                message="Stop event is not initialized.",
            )
            self._state = PluginStateSnapshot(
                state=PluginState.FAILED,
                failure_count=1,
                message="Stop event is not initialized.",
                stopped_at=int(time()),
            )
            return None
        context: Optional[PluginContext] = self._context
        if context is None:
            self._health = PluginHealthSnapshot(
                health=PluginHealth.UNHEALTHY,
                last_error_at=int(time()),
                message="Plugin context is not initialized.",
            )
            self._state = PluginStateSnapshot(
                state=PluginState.FAILED,
                failure_count=1,
                message="Plugin context is not initialized.",
                stopped_at=int(time()),
            )
            return None
        notifications: Optional[NotificationScheduler] = self._notifications
        if notifications is None:
            self._health = PluginHealthSnapshot(
                health=PluginHealth.UNHEALTHY,
                last_error_at=int(time()),
                message="Notification scheduler is not initialized.",
            )
            self._state = PluginStateSnapshot(
                state=PluginState.FAILED,
                failure_count=1,
                message="Notification scheduler is not initialized.",
                stopped_at=int(time()),
            )
            return None
        pinger: Optional[Pinger] = self._pinger
        if pinger is None:
            self._health = PluginHealthSnapshot(
                health=PluginHealth.UNHEALTHY,
                last_error_at=int(time()),
                message="ICMP helper is not initialized.",
            )
            self._state = PluginStateSnapshot(
                state=PluginState.FAILED,
                failure_count=1,
                message="ICMP helper is not initialized.",
                stopped_at=int(time()),
            )
            return None

        self._state = PluginStateSnapshot(
            state=PluginState.RUNNING,
            started_at=int(time()),
        )
        while not stop_event.is_set():
            due_channels: List[int] = notifications.due_channels()
            hosts = [str(item) for item in list(context.config[Keys.HOSTS])]
            if not hosts:
                self.__update_health(
                    healthy=False,
                    message="No hosts configured for monitoring.",
                )
                if context.verbose:
                    context.logger.message_warning = "No hosts configured for monitoring."
                stop_event.wait(float(context.config[Keys.PING_INTERVAL]))
                continue
            host_states = self.__current_host_states()
            any_down = False
            for host in hosts:
                is_alive = self.__check_host_alive(
                    host=host,
                    ping_count=int(context.config[Keys.PING_COUNT]),
                    pinger=pinger,
                )
                if not is_alive:
                    any_down = True
                self.__process_host(
                    due_channels=due_channels,
                    host=host,
                    host_states=host_states,
                    is_alive=is_alive,
                )
            self.__update_health(
                healthy=not any_down,
                message=(
                    "All monitored hosts are reachable."
                    if not any_down
                    else "One or more monitored hosts are unreachable."
                ),
            )
            stop_event.wait(float(context.config[Keys.PING_INTERVAL]))

        state: Optional[PluginStateSnapshot] = self._state
        self._state = PluginStateSnapshot(
            state=PluginState.STOPPED,
            started_at=state.started_at if state is not None else None,
            stopped_at=int(time()),
        )

    def start(self) -> None:
        """Start the runtime thread."""
        self._state = PluginStateSnapshot(
            state=PluginState.STARTING,
            started_at=int(time()),
        )
        Thread.start(self)

    def state(self) -> PluginStateSnapshot:
        """Return the current lifecycle snapshot.

        ### Returns:
        PluginStateSnapshot - Current plugin lifecycle snapshot.
        """
        state: Optional[PluginStateSnapshot] = self._state
        if state is None:
            return PluginStateSnapshot(
                state=PluginState.FAILED,
                failure_count=1,
                message="Lifecycle snapshot is not initialized.",
            )
        if self.is_alive() and state.state == PluginState.STARTING:
            state = PluginStateSnapshot(
                state=PluginState.RUNNING,
                started_at=state.started_at,
            )
            self._state = state
        return state

    def stop(self, timeout: float | None = None) -> None:
        """Request plugin shutdown.

        ### Arguments:
        * timeout: float | None - Optional join timeout.
        """
        stop_event: Optional[Event] = self._stop_event
        if stop_event is None:
            self._health = PluginHealthSnapshot(
                health=PluginHealth.UNHEALTHY,
                last_error_at=int(time()),
                message="Stop event is not initialized.",
            )
            self._state = PluginStateSnapshot(
                state=PluginState.FAILED,
                failure_count=1,
                message="Stop event is not initialized.",
                stopped_at=int(time()),
            )
            return None
        state: Optional[PluginStateSnapshot] = self._state
        if state is None:
            self._state = PluginStateSnapshot(
                state=PluginState.FAILED,
                failure_count=1,
                message="Lifecycle snapshot is not initialized.",
                stopped_at=int(time()),
            )
            return None
        if state.state not in (PluginState.STOPPED, PluginState.FAILED):
            self._state = PluginStateSnapshot(
                state=PluginState.STOPPING,
                started_at=state.started_at,
            )
        stop_event.set()
        if self.is_alive():
            self.join(timeout=timeout)
        state = self._state
        self._state = PluginStateSnapshot(
            state=PluginState.STOPPED,
            started_at=state.started_at if state is not None else None,
            stopped_at=int(time()),
        )

    # #[PRIVATE METHODS]###############################################################
    def __build_message(self, host: str, template: str, status_time: int) -> str:
        """Render one notification message from a configured template.

        ### Arguments:
        * host: str - Monitored host address.
        * template: str - Message template.
        * status_time: int - Duration of the current state in seconds.

        ### Returns:
        str - Rendered notification message.
        """
        return template.format(
            host=host,
            status_time=self.__format_duration(status_time),
        )

    def __check_host_alive(self, host: str, ping_count: int, pinger: Pinger) -> bool:
        """Check whether the host is reachable within the configured retries.

        ### Arguments:
        * host: str - Monitored host address.
        * ping_count: int - Number of ICMP attempts.
        * pinger: Pinger - ICMP helper instance.

        ### Returns:
        bool - `True` when any ICMP attempt succeeds.
        """
        attempts = max(1, ping_count)
        for _ in range(attempts):
            if pinger.is_alive(host):
                return True
        return False

    def __current_host_states(self) -> Dict[str, _HostStatus]:
        """Return the per-instance host-state cache.

        ### Returns:
        Dict[str, _HostStatus] - Cached host states for this runtime instance.
        """
        context: Optional[PluginContext] = self._context
        if context is None:
            raise ValueError("Plugin context is not initialized.")
        instance_name = context.instance_name
        if instance_name not in self._host_status_cache:
            self._host_status_cache[instance_name] = {}
        return self._host_status_cache[instance_name]

    def __emit_message(
        self,
        due_channels: List[int],
        host: str,
        is_alive: bool,
        message_text: str,
    ) -> None:
        """Log one message and optionally publish it through the dispatcher.

        ### Arguments:
        * due_channels: List[int] - Dispatcher channels currently due.
        * host: str - Monitored host address.
        * is_alive: bool - Current host state.
        * message_text: str - Rendered notification text.
        """
        context: Optional[PluginContext] = self._context
        if context is None:
            raise ValueError("Plugin context is not initialized.")
        if is_alive:
            context.logger.message_info = message_text
        else:
            context.logger.message_warning = message_text

        for channel in due_channels:
            message = Message()
            message.channel = channel
            message.subject = f"[{context.instance_name}:{host}] reachability update"
            message.messages = [message_text]
            context.dispatcher.publish(message)

    def __format_duration(self, status_time: int) -> str:
        """Format the duration of the current host state.

        ### Arguments:
        * status_time: int - Duration in seconds.

        ### Returns:
        str - Human-readable duration string.
        """
        return str(timedelta(seconds=max(0, status_time)))

    def __process_host(
        self,
        due_channels: List[int],
        host: str,
        host_states: Dict[str, _HostStatus],
        is_alive: bool,
    ) -> None:
        """Update one host state and emit required notifications.

        ### Arguments:
        * due_channels: List[int] - Dispatcher channels currently due.
        * host: str - Monitored host address.
        * host_states: Dict[str, _HostStatus] - Per-instance host-state cache.
        * is_alive: bool - Current reachability state.
        """
        context: Optional[PluginContext] = self._context
        if context is None:
            raise ValueError("Plugin context is not initialized.")
        now = int(time())
        previous = host_states.get(host)

        if context.debug:
            context.logger.message_debug = f"Host '{host}' alive={is_alive}"

        if previous is None:
            host_states[host] = _HostStatus(is_alive=is_alive, status_since=now)
            if is_alive and bool(context.config[Keys.INFORM_ON_ALIVE]):
                self.__emit_message(
                    due_channels=due_channels,
                    host=host,
                    is_alive=True,
                    message_text=self.__build_message(
                        host=host,
                        status_time=0,
                        template=str(context.config[Keys.MESSAGE_ON_ALIVE]),
                    ),
                )
            elif not is_alive and bool(context.config[Keys.INFORM_ON_DOWN]):
                self.__emit_message(
                    due_channels=due_channels,
                    host=host,
                    is_alive=False,
                    message_text=self.__build_message(
                        host=host,
                        status_time=0,
                        template=str(context.config[Keys.MESSAGE_ON_DOWN]),
                    ),
                )
            return None

        if previous.is_alive != is_alive:
            previous.is_alive = is_alive
            previous.status_since = now
            if is_alive and bool(context.config[Keys.INFORM_ON_UP]):
                self.__emit_message(
                    due_channels=due_channels,
                    host=host,
                    is_alive=True,
                    message_text=self.__build_message(
                        host=host,
                        status_time=0,
                        template=str(context.config[Keys.MESSAGE_ON_UP]),
                    ),
                )
            elif not is_alive and bool(context.config[Keys.INFORM_ON_DOWN]):
                self.__emit_message(
                    due_channels=due_channels,
                    host=host,
                    is_alive=False,
                    message_text=self.__build_message(
                        host=host,
                        status_time=0,
                        template=str(context.config[Keys.MESSAGE_ON_DOWN]),
                    ),
                )
            return None

        status_time = now - previous.status_since
        if is_alive and bool(context.config[Keys.INFORM_ON_ALIVE]):
            self.__emit_message(
                due_channels=due_channels,
                host=host,
                is_alive=True,
                message_text=self.__build_message(
                    host=host,
                    status_time=status_time,
                    template=str(context.config[Keys.MESSAGE_ON_ALIVE]),
                ),
            )
        elif not is_alive and bool(context.config[Keys.INFORM_ON_STILL_DOWN]):
            self.__emit_message(
                due_channels=due_channels,
                host=host,
                is_alive=False,
                message_text=self.__build_message(
                    host=host,
                    status_time=status_time,
                    template=str(context.config[Keys.MESSAGE_ON_STILL_DOWN]),
                ),
            )

    def __update_health(self, healthy: bool, message: str) -> None:
        """Store the current runtime health based on host reachability.

        ### Arguments:
        * healthy: bool - `True` when all monitored hosts are reachable.
        * message: str - Human-readable health summary.
        """
        now = int(time())
        self._health = PluginHealthSnapshot(
            health=PluginHealth.HEALTHY if healthy else PluginHealth.DEGRADED,
            last_ok_at=now if healthy else None,
            last_error_at=None if healthy else now,
            message=message,
        )


# #[EOF]#######################################################################
