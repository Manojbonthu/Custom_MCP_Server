"""
registry.py — Dynamically loads and registers tools for all enabled channels.

Design contract:
  - registry.py NEVER hardcodes channel names
  - Each channel must have a tools.py with a register(mcp, channel_cfg) function
  - Adding a new channel = create channels/<name>/tools.py + add to config.yaml
  - server.py calls register_all(mcp) once at startup — that's the only coupling

To add Teams (Phase 2):
  1. Create src/channels/teams/tools.py with def register(mcp, cfg)
  2. Add 'teams' to enabled_channels in config.yaml
  3. Done — server.py and registry.py need no changes
"""

import importlib
import logging

logger = logging.getLogger(__name__)


def register_all(mcp) -> None:
    """
    Import each enabled channel's tools module and call its register() function.

    Reads enabled_channels from config.yaml via load_config().
    Skips channels whose module is missing with a clear error log.
    """
    from src.config import load_config
    cfg = load_config()

    if not cfg.enabled_channels:
        logger.warning("No channels enabled in config.yaml — server has no tools.")
        return

    for channel_name in cfg.enabled_channels:
        module_path = f"src.channels.{channel_name}.tools"
        try:
            module = importlib.import_module(module_path)

            if not hasattr(module, "register"):
                logger.error(
                    f"Channel '{channel_name}': tools.py is missing a register() function. "
                    "Skipping."
                )
                continue

            channel_cfg = cfg.channels.get(channel_name)
            module.register(mcp, channel_cfg)
            logger.info(f"Channel '{channel_name}' registered successfully.")

        except ModuleNotFoundError:
            logger.error(
                f"Channel '{channel_name}' is listed in enabled_channels but "
                f"'{module_path}' does not exist. Skipping."
            )
        except Exception as e:
            logger.error(
                f"Failed to register channel '{channel_name}': {type(e).__name__}: {e}"
            )
