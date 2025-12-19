"""Authentication handler for various service authentication types."""

import base64
from typing import Any, Dict, Optional

import httpx
from pydantic import HttpUrl

from src.models import AuthConfig, AuthType


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class AuthHandler:
    """Handles authentication for different service types."""

    @staticmethod
    async def authenticate(
        endpoint: HttpUrl, auth_config: AuthConfig, additional_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Generate authentication headers for a service request.

        Args:
            endpoint: Service endpoint URL
            auth_config: Authentication configuration
            additional_headers: Additional headers to merge

        Returns:
            Dictionary of headers to use for authentication

        Raises:
            AuthenticationError: If authentication fails
        """
        headers = additional_headers.copy() if additional_headers else {}

        try:
            if auth_config.auth_type == AuthType.API_KEY:
                headers.update(await AuthHandler._handle_api_key(auth_config))
            elif auth_config.auth_type == AuthType.BEARER_TOKEN:
                headers.update(await AuthHandler._handle_bearer_token(auth_config))
            elif auth_config.auth_type == AuthType.BASIC_AUTH:
                headers.update(await AuthHandler._handle_basic_auth(auth_config))
            elif auth_config.auth_type == AuthType.OAUTH2:
                headers.update(await AuthHandler._handle_oauth2(endpoint, auth_config))
            elif auth_config.auth_type == AuthType.SERVICE_PRINCIPAL:
                headers.update(await AuthHandler._handle_service_principal(auth_config))
            elif auth_config.auth_type == AuthType.CUSTOM:
                headers.update(await AuthHandler._handle_custom(auth_config))

            # Merge any additional headers from config
            if auth_config.headers:
                headers.update(auth_config.headers)

            return headers

        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}") from e

    @staticmethod
    async def _handle_api_key(auth_config: AuthConfig) -> Dict[str, str]:
        """Handle API key authentication."""
        api_key = auth_config.credentials.get("api_key")
        if not api_key:
            raise AuthenticationError("API key not provided in credentials")

        # Check for custom header name
        header_name = auth_config.credentials.get("header_name", "X-API-Key")
        return {header_name: api_key}

    @staticmethod
    async def _handle_bearer_token(auth_config: AuthConfig) -> Dict[str, str]:
        """Handle bearer token authentication."""
        token = auth_config.credentials.get("token")
        if not token:
            raise AuthenticationError("Bearer token not provided in credentials")

        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    async def _handle_basic_auth(auth_config: AuthConfig) -> Dict[str, str]:
        """Handle basic authentication."""
        username = auth_config.credentials.get("username")
        password = auth_config.credentials.get("password")

        if not username or not password:
            raise AuthenticationError("Username and password required for basic auth")

        # Encode credentials
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()

        return {"Authorization": f"Basic {encoded}"}

    @staticmethod
    async def _handle_oauth2(endpoint: HttpUrl, auth_config: AuthConfig) -> Dict[str, str]:
        """Handle OAuth2 authentication."""
        client_id = auth_config.credentials.get("client_id")
        client_secret = auth_config.credentials.get("client_secret")
        token_endpoint = auth_config.token_endpoint

        if not all([client_id, client_secret, token_endpoint]):
            raise AuthenticationError("OAuth2 requires client_id, client_secret, and token_endpoint")

        # Check for existing access token
        access_token = auth_config.credentials.get("access_token")
        if access_token:
            return {"Authorization": f"Bearer {access_token}"}

        # Request new access token
        grant_type = auth_config.credentials.get("grant_type", "client_credentials")
        scope = auth_config.credentials.get("scope", "")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                str(token_endpoint),
                data={
                    "grant_type": grant_type,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": scope,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise AuthenticationError(f"OAuth2 token request failed: {response.text}")

            token_data = response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise AuthenticationError("No access token in OAuth2 response")

            return {"Authorization": f"Bearer {access_token}"}

    @staticmethod
    async def _handle_service_principal(auth_config: AuthConfig) -> Dict[str, str]:
        """Handle Azure Service Principal authentication."""
        try:
            from azure.identity.aio import ClientSecretCredential
        except ImportError:
            raise AuthenticationError("azure-identity package required for service principal auth")

        tenant_id = auth_config.credentials.get("tenant_id")
        client_id = auth_config.credentials.get("client_id")
        client_secret = auth_config.credentials.get("client_secret")
        scope = auth_config.credentials.get("scope", "https://management.azure.com/.default")

        if not all([tenant_id, client_id, client_secret]):
            raise AuthenticationError("Service Principal requires tenant_id, client_id, and client_secret")

        # Get access token using Azure Identity
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

        token = await credential.get_token(scope)
        await credential.close()

        return {"Authorization": f"Bearer {token.token}"}

    @staticmethod
    async def _handle_custom(auth_config: AuthConfig) -> Dict[str, str]:
        """Handle custom authentication logic."""
        # For custom auth, expect headers to be provided directly in config
        if auth_config.headers:
            return auth_config.headers

        # Or build from credentials
        return {key: str(value) for key, value in auth_config.credentials.items()}


class ServiceAuthenticator:
    """High-level service authentication manager."""

    def __init__(self):
        self._token_cache: Dict[str, Dict[str, Any]] = {}

    async def get_authenticated_headers(
        self, service_id: str, endpoint: HttpUrl, auth_config: AuthConfig
    ) -> Dict[str, str]:
        """
        Get authenticated headers for a service, using cache when appropriate.

        Args:
            service_id: Unique service identifier
            endpoint: Service endpoint
            auth_config: Authentication configuration

        Returns:
            Dictionary of authenticated headers
        """
        # For now, we'll authenticate on every request
        # In production, you'd want to cache tokens and refresh them
        return await AuthHandler.authenticate(endpoint, auth_config)

    async def verify_authentication(self, endpoint: HttpUrl, headers: Dict[str, str]) -> bool:
        """
        Verify that authentication is working by making a test request.

        Args:
            endpoint: Service endpoint to test
            headers: Headers with authentication

        Returns:
            True if authentication is successful
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(str(endpoint), headers=headers)
                # Consider 2xx and 3xx as successful (service might redirect)
                return response.status_code < 400
        except Exception:
            return False
