"""Configuration loading for Boltz-2 API.

This module handles loading and validating configuration for the Boltz-2 API
client, including API keys, base URLs, and timeout settings.

Configuration can be provided through:
    - Environment variables (BOLTZ2_API_KEY, BOLTZ2_API_URL)
    - A .env file in the current directory
    - Explicit parameters passed to load_config()

Example:
    >>> from boltz2.config import load_config
    >>> config = load_config()
    >>> print(config.base_url)
    'https://health.api.nvidia.com/v1/biology/mit/boltz2/predict'
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv


@dataclass
class Boltz2Config:
    """Configuration container for Boltz-2 API client.

    This dataclass holds all configuration needed to interact with the
    NVIDIA Boltz-2 API, including authentication and connection settings.

    Attributes:
        api_key: The NVIDIA API key for authentication. Required.
        base_url: The API endpoint URL. Defaults to the NVIDIA health API.
        timeout: Request timeout in seconds. Defaults to 600 (10 minutes).

    Example:
        >>> config = Boltz2Config(api_key="nvapi-xxx")
        >>> print(config.headers)
        {'accept': 'application/json', ...}
    """

    api_key: str
    base_url: str = "https://health.api.nvidia.com/v1/biology/mit/boltz2/predict"
    timeout: int = 600

    @property
    def headers(self) -> Dict[str, str]:
        """Generate HTTP headers for API requests.

        Returns:
            Dictionary containing required headers including Authorization.
        """
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }


def load_config(
    env_path: Optional[Path] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: int = 600,
) -> Boltz2Config:
    """Load Boltz-2 configuration from environment or explicit values.

    This function loads configuration with the following precedence:
        1. Explicit parameters passed to this function
        2. Environment variables (BOLTZ2_API_KEY, BOLTZ2_API_URL)
        3. Values from .env file

    Args:
        env_path: Path to a .env file. If not provided, searches for .env
            in the current directory and parent directories.
        api_key: Explicit API key. Overrides environment variable if provided.
        base_url: Explicit API URL. Overrides environment variable if provided.
        timeout: Request timeout in seconds. Defaults to 600.

    Returns:
        A Boltz2Config instance with resolved configuration values.

    Raises:
        ValueError: If no API key is found in any configuration source.
            The error message includes instructions for setting the API key.

    Example:
        >>> # Load from environment
        >>> config = load_config()
        >>>
        >>> # Load with explicit API key
        >>> config = load_config(api_key="nvapi-xxx")
        >>>
        >>> # Load from specific .env file
        >>> config = load_config(env_path=Path("/path/to/.env"))
    """
    # Load .env file
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    # Resolve API key with precedence: explicit > env var
    resolved_key = api_key or os.getenv("BOLTZ2_API_KEY")

    if not resolved_key:
        raise ValueError(
            "BOLTZ2_API_KEY not found. Please set it using one of:\n"
            "  1. Environment variable: export BOLTZ2_API_KEY='nvapi-xxx'\n"
            "  2. .env file: Add BOLTZ2_API_KEY='nvapi-xxx' to .env\n"
            "  3. Pass api_key parameter to Boltz2Client or load_config()\n"
            "\n"
            "Get your API key from: https://build.nvidia.com/mit/boltz-2"
        )

    # Resolve base URL with precedence: explicit > env var > default
    resolved_url = base_url or os.getenv(
        "BOLTZ2_API_URL",
        "https://health.api.nvidia.com/v1/biology/mit/boltz2/predict",
    )

    return Boltz2Config(
        api_key=resolved_key,
        base_url=resolved_url,
        timeout=timeout,
    )
