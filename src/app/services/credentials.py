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
    mlflow_tracking_uri: Optional[str] = None
    mlflow_experiment: Optional[str] = None
    mlflow_api_token: Optional[str] = None
    cyberarc_safe: Optional[str] = None
    cyberarc_app_id: Optional[str] = None
    certificate_bundle_path: Optional[str] = None
    credential_store_path: Optional[str] = None
    fastapi_base_url: Optional[str] = None
    model_registry_path: Optional[str] = None
    environment: str = "local"
    app_version: str = "dev"
    extra: Dict[str, str] = field(default_factory=dict)

    def public_config(self) -> Dict[str, str]:
        """Expose safe values to the client application."""

        public_values = {
            "s3_bucket": self.s3_bucket or "",
            "dataset_key": self.dataset_key or "",
            "environment": self.environment,
            "app_version": self.app_version,
            "mlflow_tracking_uri": self.mlflow_tracking_uri or "",
            "mlflow_experiment": self.mlflow_experiment or "",
            "cyberarc_safe": self.cyberarc_safe or "",
            "cyberarc_app_id": self.cyberarc_app_id or "",
            "certificate_bundle_path": self.certificate_bundle_path or "",
            "credential_store_path": self.credential_store_path or "",
            "fastapi_base_url": self.fastapi_base_url or "",
            "model_registry_path": self.model_registry_path or "",
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
        mlflow_tracking_uri=env.get(f"{prefix}MLFLOW_TRACKING_URI"),
        mlflow_experiment=env.get(f"{prefix}MLFLOW_EXPERIMENT"),
        mlflow_api_token=env.get(f"{prefix}MLFLOW_API_TOKEN"),
        cyberarc_safe=env.get(f"{prefix}CYBERARC_SAFE"),
        cyberarc_app_id=env.get(f"{prefix}CYBERARC_APP_ID"),
        certificate_bundle_path=env.get(f"{prefix}CERTIFICATE_BUNDLE_PATH"),
        credential_store_path=env.get(f"{prefix}CREDENTIAL_STORE_PATH"),
        fastapi_base_url=env.get(f"{prefix}FASTAPI_BASE_URL"),
        model_registry_path=env.get(f"{prefix}MODEL_REGISTRY_PATH"),
        environment=env.get(f"{prefix}ENVIRONMENT", "local"),
        app_version=env.get(f"{prefix}APP_VERSION", "dev"),
    )
    return creds
