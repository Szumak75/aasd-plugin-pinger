# Changelog

## 0.0.3

- fix: populate `Message.diagnostic_source` with the runtime class name for dispatcher diagnostics
- docs: documented the dispatcher diagnostic source attached to emitted notifications
- chore: bumped local plugin version to `0.0.3`

## 0.0.2

- style: aligned the local pinger plugin repository with the preferred
  `Optional[...]`, `List[...]`, `Tuple[...]`, and `Dict[...]` typing style

## 0.0.1

- fix: reduced shutdown latency by interrupting the runtime loop between hosts and configured retry attempts
- fix: aligned host probing with one system-level ICMP attempt per runtime retry
- test: added regression coverage for prompt stop handling

## 0.0.0

- feat: created the initial `pinger` worker plugin repository skeleton
- feat: added reachability monitoring configuration and runtime state tracking
- feat: added local logging plus optional dispatcher delivery through `message_channel` and `at_channel`
- test: added plugin-local runtime regression coverage
