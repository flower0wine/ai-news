"""
API client module for external services.

This module provides a unified interface for making HTTP requests to external APIs,
with proper error handling and timeout configuration.

Currently supports:
    - AlphaSignal API: Fetch latest AI news campaigns
"""

import json
import logging
from typing import Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from src.config import get_config

logger = logging.getLogger(__name__)


class ApiClientError(Exception):
    """Custom exception for API client errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
        """
        super().__init__(message)
        self.status_code = status_code


class AlphaSignalClient:
    """Client for AlphaSignal.ai API.

    AlphaSignal provides AI news and trends through their API.
    This client fetches the latest campaign data.

    API Endpoint:
        GET https://alphasignal.ai/api/last-campaign

    Response Format:
        {
            "_id": "...",
            "html": "...",
            "subject": "...",
            "timestamp": "..."
        }
    """

    BASE_URL = "https://alphasignal.ai/api"

    # Browser headers to mimic real browser requests
    DEFAULT_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Referer": "https://alphasignal.ai/last-email",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=1, i",
    }

    def __init__(self, timeout: Optional[int] = None) -> None:
        """Initialize the AlphaSignal client.

        Args:
            timeout: Request timeout in seconds. If None, uses config default.
        """
        self.config = get_config()
        self.timeout = timeout or self.config.api_timeout

    def get_last_campaign(self) -> Dict[str, Any]:
        """Fetch the latest campaign from AlphaSignal API.

        Returns:
            Dictionary containing campaign data with keys:
                - _id: Campaign ID
                - html: Campaign HTML content
                - subject: Campaign subject line
                - timestamp: Campaign timestamp

        Raises:
            ApiClientError: If the API request fails
        """
        url = f"{self.BASE_URL}/last-campaign"
        logger.info(f"Fetching campaign from AlphaSignal: {url}")

        try:
            request = Request(url)

            # Add all browser headers to mimic real requests
            for header, value in self.DEFAULT_HEADERS.items():
                request.add_header(header, value)

            with urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ApiClientError(
                        f"API returned non-200 status: {response.status}",
                        status_code=response.status,
                    )

                data = json.loads(response.read().decode("utf-8"))
                logger.info(
                    f"Successfully fetched campaign: {data.get('_id', 'unknown')}"
                )
                return data

        except HTTPError as e:
            logger.error(f"HTTP error fetching campaign: {e.code} - {e.reason}")
            raise ApiClientError(
                f"HTTP error: {e.code} - {e.reason}", status_code=e.code
            ) from e

        except URLError as e:
            logger.error(f"URL error fetching campaign: {e.reason}")
            raise ApiClientError(f"URL error: {e.reason}") from e

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ApiClientError(f"Invalid JSON response: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error fetching campaign: {e}")
            raise ApiClientError(f"Unexpected error: {e}") from e
