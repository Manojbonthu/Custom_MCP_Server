"""
config.py — Loads config.yaml into typed Python dataclasses.

No pydantic-settings needed — pure PyYAML + dataclasses.
Singleton pattern: load_config() returns the same object after first call.
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8100


@dataclass
class MailChannelConfig:
    credentials_path: str = "credentials/google_credentials.json"
    token_path: str = "credentials/gmail_token.json"
    scopes: list = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.send"
    ])
    oauth_redirect_uri: str = "http://localhost:8100/auth/gmail/callback"


@dataclass
class Config:
    server: ServerConfig
    enabled_channels: list[str]
    channels: dict  # channel name → channel config object (e.g. MailChannelConfig)


_config: Optional[Config] = None


def load_config(path: str = "config.yaml") -> Config:
    """Load and cache config from config.yaml. Subsequent calls return cached object."""
    global _config
    if _config is not None:
        return _config

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path.resolve()}\n"
            "Make sure to run the server from the project root directory."
        )

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    # Build channel configs
    channel_configs: dict = {}
    raw_channels = raw.get("channels", {})

    if "mail" in raw_channels:
        channel_configs["mail"] = MailChannelConfig(**raw_channels["mail"])

    _config = Config(
        server=ServerConfig(**raw.get("server", {})),
        enabled_channels=raw.get("enabled_channels", []),
        channels=channel_configs,
    )
    return _config


def reset_config() -> None:
    """Reset cached config — useful for testing."""
    global _config
    _config = None
