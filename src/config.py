"""
Configuration module for AI News Lambda function.

This module handles all configuration management through environment variables
and AWS Secrets Manager, following AWS Lambda best practices for secure
and flexible configuration.

Environment Variables Required (for Secrets Manager):
    - SECRETS_MANAGER_NAME: Name of secret in AWS Secrets Manager
    OR (for local development):
    - DEEPSEEK_API_KEY: API key for Volcengine LLM service
    - LLM_MODEL: Model identifier (e.g., volcengine/ep-xxx)
    - RESEND_API_KEY: API key for Resend email service
    - EMAIL_FROM: Sender email address (e.g., "AI News <newsletter@example.com>")
    - EMAIL_TO: Recipient email address(es), comma-separated

Environment Variables Optional:
    - LLM_TEMPERATURE: LLM sampling temperature (default: 0.7)
    - LLM_MAX_TOKENS: Max tokens for LLM response (default: 2000)
    - API_REQUEST_TIMEOUT: Timeout for external API requests in seconds (default: 30)
    - IS_LOCAL: Set to "true" for local development (skip Secrets Manager)
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class Config:
    """Configuration class that loads settings from environment variables or Secrets Manager."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables or Secrets Manager."""
        # Check if running locally (for development)
        self._is_local = os.environ.get("IS_LOCAL", "false").lower() == "true"

        if self._is_local:
            # Local development: read directly from environment variables
            logger.info("Running in local mode, reading from environment variables")
            self._load_from_env()
        else:
            # Production: read from Secrets Manager
            logger.info("Running in production mode, reading from Secrets Manager")
            self._load_from_secrets_manager()

    def _load_from_env(self) -> None:
        """Load configuration from environment variables (local development)."""
        # LLM Configuration (Volcengine)
        self.llm_api_key: str = self._get_required("DEEPSEEK_API_KEY")
        self.llm_model: str = self._get_required("LLM_MODEL")
        self.llm_temperature: float = self._get_float("LLM_TEMPERATURE", default=1.3)
        self.llm_max_tokens: int = self._get_int("LLM_MAX_TOKENS", default=8192)

        # Resend Email Configuration
        self.resend_api_key: str = self._get_required("RESEND_API_KEY")
        self.email_from: str = self._get_required("EMAIL_FROM")
        self.email_to: List[str] = self._get_list("EMAIL_TO")

        # API Configuration
        self.api_timeout: int = self._get_int("API_REQUEST_TIMEOUT", default=30)

    def _load_from_secrets_manager(self) -> None:
        """Load configuration from AWS Secrets Manager (production)."""
        import boto3
        from botocore.exceptions import ClientError

        secret_name = os.environ.get("SECRETS_MANAGER_NAME", "ai-news")

        logger.info(f"Loading secrets from: {secret_name}")

        try:
            # Create Secrets Manager client
            client = boto3.client("secretsmanager")

            response = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(response["SecretString"])

            # LLM Configuration (Volcengine)
            self.llm_api_key = secret.get("DEEPSEEK_API_KEY", "")
            if not self.llm_api_key:
                raise ValueError("DEEPSEEK_API_KEY not found in secrets")

            self.llm_model = secret.get("LLM_MODEL", "")
            if not self.llm_model:
                raise ValueError("LLM_MODEL not found in secrets")

            self.llm_temperature = float(secret.get("LLM_TEMPERATURE", 0.7))
            self.llm_max_tokens = int(secret.get("LLM_MAX_TOKENS", 2000))

            # Resend Email Configuration
            self.resend_api_key = secret.get("RESEND_API_KEY", "")
            if not self.resend_api_key:
                raise ValueError("RESEND_API_KEY not found in secrets")

            self.email_from = secret.get("EMAIL_FROM", "")
            if not self.email_from:
                raise ValueError("EMAIL_FROM not found in secrets")

            email_to = secret.get("EMAIL_TO", "")
            if not email_to:
                raise ValueError("EMAIL_TO not found in secrets")
            self.email_to = [
                item.strip() for item in email_to.split(",") if item.strip()
            ]

            # API Configuration
            self.api_timeout = int(secret.get("API_REQUEST_TIMEOUT", 30))

            logger.info("Successfully loaded secrets from Secrets Manager")

        except ClientError as e:
            logger.error(f"Failed to load secrets from Secrets Manager: {e}")
            raise ValueError(f"Failed to load secrets: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secrets JSON: {e}")
            raise ValueError(f"Invalid secrets JSON format: {e}") from e

    @staticmethod
    def _get_required(key: str) -> str:
        """Get a required environment variable.

        Args:
            key: Environment variable name

        Returns:
            The value of the environment variable

        Raises:
            ValueError: If the environment variable is not set
        """
        value = os.environ.get(key)
        if not value:
            raise ValueError(f"Required environment variable '{key}' is not set")
        return value

    @staticmethod
    def _get_optional(key: str, default: str = "") -> str:
        """Get an optional environment variable with a default value.

        Args:
            key: Environment variable name
            default: Default value if not set

        Returns:
            The value of the environment variable or the default
        """
        return os.environ.get(key, default)

    @staticmethod
    def _get_int(key: str, default: int) -> int:
        """Get an environment variable as an integer.

        Args:
            key: Environment variable name
            default: Default value if not set or invalid

        Returns:
            The integer value of the environment variable
        """
        value = os.environ.get(key)
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    @staticmethod
    def _get_float(key: str, default: float) -> float:
        """Get an environment variable as a float.

        Args:
            key: Environment variable name
            default: Default value if not set or invalid

        Returns:
            The float value of the environment variable
        """
        value = os.environ.get(key)
        if not value:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    @staticmethod
    def _get_list(key: str) -> List[str]:
        """Get an environment variable as a list of strings.

        The value should be comma-separated.

        Args:
            key: Environment variable name

        Returns:
            List of strings

        Raises:
            ValueError: If the environment variable is not set
        """
        value = os.environ.get(key)
        if not value:
            raise ValueError(f"Required environment variable '{key}' is not set")
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def is_local(self) -> bool:
        """Check if running in local development mode."""
        return self._is_local

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary (excluding sensitive values).

        Returns:
            Dictionary representation of non-sensitive configuration
        """
        return {
            "is_local": self._is_local,
            "llm_model": self.llm_model,
            "llm_temperature": self.llm_temperature,
            "llm_max_tokens": self.llm_max_tokens,
            "email_from": self.email_from,
            "email_to": self.email_to,
            "api_timeout": self.api_timeout,
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance (singleton pattern).

    This function implements a simple singleton pattern to avoid
    repeatedly reading environment variables.

    Returns:
        The global Config instance
    """
    global _config
    if _config is None:
        _config = Config()
    return _config
