# AASd v2 Worker Plugin Pinger

This directory provides a recommended starting point for a new AASd worker
plugin repository.

## Included Files

- `load.py` - required daemon entry point exposing `get_plugin_spec()`
- `plugin/__init__.py` - plugin package marker
- `plugin/config.py` - plugin-specific configuration keys
- `plugin/runtime.py` - thread-based worker runtime implementation
- `requirements.txt` - plugin-local runtime dependencies placeholder

## How To Use

1. Copy this directory to a new repository, for example
   `aasd-plugin-pinger/`.
2. Rename identifiers in:
   - `plugin_id`
   - `plugin_name`
   - `Keys`
   - config field names and descriptions
3. Replace the placeholder runtime behavior in `plugin/runtime.py` with the
   real plugin logic.
4. Mount the plugin repository into AASd through `plugins_dir`, preferably by a
   symbolic link.
5. Install plugin dependencies into the same Python environment used by AASd.

## Design Notes

The template follows the current recommended pattern:

- `PluginSpec` and `PluginContext` from the public runtime API
- `ThPluginMixin` for typed runtime-owned storage
- local private key constants based on `ReadOnlyClass`
- explicit narrowing of `Optional[...]` runtime properties
- `PluginStateSnapshot` and `PluginHealthSnapshot` fallbacks for guard paths

The current `pinger` runtime applies `ping_count` as the number of plugin-side
retries per host. Each `Pinger.is_alive(...)` call performs one system-level
ICMP attempt, which keeps retry behavior explicit and improves shutdown
responsiveness.

For broader project guidance, see:

- `docs/PluginAPI.md`
- `docs/PluginChecklist.md`
- `docs/PluginRepositoryModel.md`
