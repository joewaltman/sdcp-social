"""Base Meta Graph API client."""

import logging
from typing import Any, Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


class MetaAPIError(Exception):
    """Exception for Meta API errors."""

    def __init__(self, message: str, code: Optional[int] = None, subcode: Optional[int] = None):
        self.message = message
        self.code = code
        self.subcode = subcode
        super().__init__(message)


class MetaClient:
    """Base client for Meta Graph API."""

    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self):
        settings = get_settings()
        self.access_token = settings.meta_access_token
        self.page_id = settings.facebook_page_id
        self.instagram_account_id = settings.instagram_business_account_id
        self._client = httpx.Client(timeout=60.0)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Make a request to the Meta Graph API."""
        url = f"{self.BASE_URL}/{endpoint}"

        # Add access token to params
        if params is None:
            params = {}
        params["access_token"] = self.access_token

        try:
            if method.upper() == "GET":
                response = self._client.get(url, params=params)
            elif method.upper() == "POST":
                response = self._client.post(url, params=params, data=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            result = response.json()

            # Check for API errors in response
            if "error" in result:
                error = result["error"]
                raise MetaAPIError(
                    message=error.get("message", "Unknown error"),
                    code=error.get("code"),
                    subcode=error.get("error_subcode"),
                )

            return result

        except httpx.HTTPStatusError as e:
            # Try to parse error from response
            try:
                error_data = e.response.json().get("error", {})
                raise MetaAPIError(
                    message=error_data.get("message", str(e)),
                    code=error_data.get("code"),
                    subcode=error_data.get("error_subcode"),
                ) from e
            except Exception:
                raise MetaAPIError(message=str(e)) from e

    def get(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Make a GET request."""
        return self._make_request("GET", endpoint, params=params)

    def post(
        self, endpoint: str, params: Optional[dict] = None, data: Optional[dict] = None
    ) -> dict[str, Any]:
        """Make a POST request."""
        return self._make_request("POST", endpoint, params=params, data=data)

    def verify_credentials(self) -> dict[str, Any]:
        """Verify the access token and get account info."""
        try:
            # Get page info
            page_info = self.get(self.page_id, params={"fields": "name,id"})
            logger.info(f"Connected to Facebook Page: {page_info.get('name')}")

            # Get Instagram account info
            ig_info = self.get(
                self.instagram_account_id,
                params={"fields": "username,id"},
            )
            logger.info(f"Connected to Instagram: @{ig_info.get('username')}")

            return {
                "facebook": page_info,
                "instagram": ig_info,
            }

        except MetaAPIError as e:
            logger.error(f"Failed to verify credentials: {e.message}")
            raise

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
