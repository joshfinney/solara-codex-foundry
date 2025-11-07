import json
import os

from app.services import credentials


def test_bootstrap_and_secret_resolution(tmp_path, monkeypatch):
    sphere = tmp_path / ".sphererc"
    sphere.write_text(
        """
app_display_name = "Primary Credit Issuance Workspace"
app_name = "primary-credit"
app_version = "1.2.3"
environment_key = "uat"
region = "eu-west-1"
s3_dataset_key = "datasets/issuance.csv"
s3emea_certificate_file = "certs/aws.pem"
s3_key = "cyberark://s3_primary"
s3_endpoint_url = "https://example.local"
s3_default_acl = "bucket-owner-full-control"
llm_model = "gpt-test"
llm_use_case = "issuance"
llm_embeddings_api = "https://llm.local/embed"
llm_key = "cyberark://llm_primary"
embeddings_model = "text-embedding"
embeddings_key = "cyberark://embedding_primary"
mlflow_enabled = true
logstash_endpoints = ["https://logs.dev"]
"""
    )

    monkeypatch.setenv(
        "PRIMARY_CREDIT_SECRET_S3_PRIMARY",
        json.dumps(
            {
                "bucket": "primary-bucket",
                "prefix": "artifacts",
                "anonymous": False,
                "key": "access",
                "secret": "secret",
                "use_listings_cache": False,
                "client_kwargs": {"region_name": "eu-west-1"},
                "s3_additional_kwargs": {"ACL": "private"},
            }
        ),
    )
    monkeypatch.setenv(
        "PRIMARY_CREDIT_SECRET_LLM_PRIMARY",
        json.dumps({"api_key": "llm-secret", "timeout": 5}),
    )
    monkeypatch.setenv(
        "PRIMARY_CREDIT_SECRET_EMBEDDING_PRIMARY",
        json.dumps({"api_key": "embedding-secret"}),
    )

    config = credentials.bootstrap_environment(execution_root=tmp_path)
    assert os.getenv(credentials.BOOTSTRAP_ENV_VAR)

    runtime = credentials.load_runtime_credentials(config)
    assert runtime.app_version == "1.2.3"
    assert runtime.environment_key == "uat"
    assert runtime.dataset_key == "datasets/issuance.csv"
    assert runtime.public_config()["mlflow_enabled"] is True
    assert runtime.logstash_endpoints == ("https://logs.dev",)

    storage_creds = credentials.load_storage_credentials(config)
    assert storage_creds is not None
    assert storage_creds.bucket == "primary-bucket"
    assert storage_creds.prefix == "artifacts/"
    assert storage_creds.client_kwargs["endpoint_url"] == "https://example.local"
    assert storage_creds.client_kwargs["verify"].endswith("certs/aws.pem")
    assert storage_creds.s3_additional_kwargs["ACL"] == "private"

    llm_creds = credentials.load_llm_credentials(config)
    assert llm_creds is not None
    assert llm_creds.model == "gpt-test"
    assert llm_creds.parameters["api_key"] == "llm-secret"

    embedding_creds = credentials.load_embedding_credentials(config)
    assert embedding_creds is not None
    assert embedding_creds.parameters["api_key"] == "embedding-secret"

    serialized = config.to_serialized()
    restored = credentials.load_bootstrap_session(serialized)
    assert restored is not None
    assert restored.get("APP_NAME") == "primary-credit"
