"""Credential loading utilities for the primary credit app."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RuntimeCredentials:
    """Represents secrets fetched from the environment at runtime."""

    s3_bucket: Optional[str] = None
    dataset_key: Optional[str] = None
    llm_api_key: Optional[str] = None
    celery_broker_url: Optional[str] = None
    celery_backend_url: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)

    def public_config(self) -> Dict[str, str]:
        """Expose safe values to the client application."""

        public_values = {
            "s3_bucket": self.s3_bucket or "",
            "dataset_key": self.dataset_key or "",
        }
        public_values.update(self.extra)
        return public_values


def load_runtime_credentials(prefix: str = "PRIMARY_CREDIT_") -> RuntimeCredentials:
    """Load credentials from environment variables using the provided prefix."""

    env = os.environ
    creds = RuntimeCredentials(
        s3_bucket=env.get(f"{prefix}S3_BUCKET"),
        dataset_key=env.get(f"{prefix}DATASET_KEY"),
        llm_api_key=env.get(f"{prefix}LLM_API_KEY"),
        celery_broker_url=env.get(f"{prefix}CELERY_BROKER_URL"),
        celery_backend_url=env.get(f"{prefix}CELERY_BACKEND_URL"),
        extra={
            "environment": env.get(f"{prefix}ENVIRONMENT", "local"),
            "app_version": env.get(f"{prefix}APP_VERSION", "dev"),
        },
    )
    return creds
