"""API Client for InvisaGig."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import socket
from typing import Any

import aiohttp
import async_timeout

from .const import TIMEOUT

_LOGGER = logging.getLogger(__name__)


class InvisaGigApiClientError(Exception):
    """Exception to indicate a general API error."""


class InvisaGigApiClientCommunicationError(InvisaGigApiClientError):
    """Exception to indicate a communication error."""


class InvisaGigApiClientAuthenticationError(InvisaGigApiClientError):
    """Exception to indicate an authentication error."""


class InvisaGigApiClient:
    """Sample API Client."""

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
        use_ssl: bool = False,
    ) -> None:
        """Sample API Client."""
        self._host = host
        self._port = port
        self._session = session
        self._use_ssl = use_ssl
        self._protocol = "https" if use_ssl else "http"

    async def async_get_data(self) -> dict[str, Any]:
        """Get data from the API."""
        url = f"{self._protocol}://{self._host}:{self._port}/telemetry/info.json"
        
        try:
            async with async_timeout.timeout(TIMEOUT):
                response = await self._session.get(url)
                response.raise_for_status()
                text = await response.text()
                
                # Sanitize JSON
                sanitized_text = self._sanitize_json(text)
                
                # Parse JSON
                data = json.loads(sanitized_text)
                
                # Normalize data (recurse through and fix "null" strings, trim strings)
                return self._normalize_data(data)

        except asyncio.TimeoutError as exception:
            raise InvisaGigApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise InvisaGigApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except json.JSONDecodeError as exception:
            print(f"FAILED JSON: {text}")  # For debug
            raise InvisaGigApiClientError("Could not parse JSON response") from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise InvisaGigApiClientError(
                f"Something really wrong happened: {exception}"
            ) from exception

    def _sanitize_json(self, text: str) -> str:
        """Sanitize JSON string from InvisaGig."""
        # 1. replace ": ," with ": null,"
        text = text.replace(": ,", ": null,")
        
        # 2. replace ":\n}" with ": null\n}"
        text = text.replace(":\n}", ": null\n}")
        
        # 3. replace ": }" with ": null}"
        text = text.replace(": }", ": null}")
        
        # 4. replace ": ]" with ": null]"
        text = text.replace(": ]", ": null]")

        return text

    def _normalize_data(self, data: Any) -> Any:
        """Recursively normalize data."""
        if isinstance(data, dict):
            return {k: self._normalize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._normalize_data(item) for item in data]
        elif isinstance(data, str):
            # Check for "null" string
            if data.lower() == "null" or data.strip() == "":
                return None
            return data.strip()
        return data
