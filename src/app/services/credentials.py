"""Credential bootstrapping and configuration helpers."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping

try:  # pragma: no cover - Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for older interpreters
    import tomli as tomllib  # type: ignore[import]


BOOTSTRAP_ENV_VAR = "PRIMARY_CREDIT_BOOTSTRAP_SESSION"
SPHERE_RC_ENV_VAR = "PRIMARY_CREDIT_SPHERERC_PATH"
DEFAULT_APP_NAME = "primary-credit"
DEFAULT_ENVIRONMENT_KEY = "local"
DEFAULT_REGION = "us-east-1"


def _normalise_key(value: str) -> str:
    return value.strip().upper()


def _flatten_environment_key(value: str) -> str:
    return _normalise_key(value).replace("-", "_").replace("/", "_")


def _json_or_raw(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


class QRExecConfig:
    """In-memory representation of bootstrap secrets.

    The class reads configuration from the `.sphererc` file and lazily resolves
    CyberArk references that are exposed through environment variables. The
    decoded instance can be serialized to JSON so that it can be stored in an
    environment variable for subsequent processes.
    """

    def __init__(
        self,
        *,
        app_name: str,
        environment_key: str,
        region: str,
        execution_root: Path | str,
    ) -> None:
        self.app_name = app_name or DEFAULT_APP_NAME
        self.environment_key = environment_key or DEFAULT_ENVIRONMENT_KEY
        self.region = region or DEFAULT_REGION
        self.execution_root = Path(execution_root)
        self._local_store: dict[str, Any] = {}
        self._cyberark_cache: dict[str, Any] = {}
        self._logger = logging.getLogger("primary-credit.config")

    # ------------------------------------------------------------------ setup
    def setup_environment(self) -> None:
        self._local_store = self._load_sphererc()

    # ------------------------------------------------------------------ loading helpers
    def _load_sphererc(self) -> dict[str, Any]:
        path = self._resolve_sphererc_path()
        if not path or not path.exists():
            self._logger.debug("sphererc.missing", extra={"path": str(path) if path else None})
            return {}

        raw_text = path.read_text(encoding="utf-8")
        data: dict[str, Any] = {}
        if not raw_text.strip():
            return data

        parsers = (
            self._parse_toml,
            self._parse_json,
            self._parse_simple_kv,
        )
        for parser in parsers:
            try:
                parsed = parser(raw_text)
            except ValueError:
                continue
            else:
                data = parsed
                break
        normalised = {_normalise_key(k): v for k, v in data.items()}
        return normalised

    def _resolve_sphererc_path(self) -> Path | None:
        env_path = os.getenv(SPHERE_RC_ENV_VAR)
        if env_path:
            return Path(env_path).expanduser()
        default_path = self.execution_root / ".sphererc"
        if default_path.exists():
            return default_path
        # support repo-local configs like config/sphererc.toml
        fallback = self.execution_root / "config" / "sphererc.toml"
        if fallback.exists():
            return fallback
        return default_path

    @staticmethod
    def _parse_toml(raw: str) -> dict[str, Any]:
        try:
            return tomllib.loads(raw)
        except Exception as error:  # noqa: BLE001 - normalization layer
            raise ValueError("Invalid TOML payload") from error

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError("Invalid JSON payload") from error

    @staticmethod
    def _parse_simple_kv(raw: str) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError("Invalid key/value configuration")
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip().strip('"')
        return data

    # ------------------------------------------------------------------ serialization helpers
    def to_serialized(self) -> str:
        payload = {
            "app_name": self.app_name,
            "environment_key": self.environment_key,
            "region": self.region,
            "execution_root": str(self.execution_root),
            "local_store": self._local_store,
        }
        return json.dumps(payload)

    @classmethod
    def from_serialized(cls, payload: str) -> "QRExecConfig":
        data = _json_or_raw(payload)
        if not isinstance(data, Mapping):
            raise TypeError("Invalid bootstrap payload")
        execution_root_value = data.get("execution_root")
        execution_root = Path(execution_root_value) if execution_root_value else Path.cwd()
        instance = cls(
            app_name=str(data.get("app_name", DEFAULT_APP_NAME)),
            environment_key=str(data.get("environment_key", DEFAULT_ENVIRONMENT_KEY)),
            region=str(data.get("region", DEFAULT_REGION)),
            execution_root=execution_root,
        )
        local_store = data.get("local_store", {})
        if isinstance(local_store, Mapping):
            instance._local_store = {_normalise_key(str(k)): v for k, v in local_store.items()}
        return instance

    # ------------------------------------------------------------------ resolution
    def get(self, key: str, default: Any = None) -> Any:
        lookup_key = _normalise_key(key)
        if lookup_key in self._local_store:
            value = self._local_store[lookup_key]
            resolved = self._resolve_value(lookup_key, value)
            if resolved is not None:
                return resolved
        env_key = f"PRIMARY_CREDIT_{lookup_key}"
        if env_key in os.environ:
            return _json_or_raw(os.environ[env_key])
        return default

    def get_dict(self, key: str) -> dict[str, Any]:
        value = self.get(key, default={})
        if isinstance(value, str):
            parsed = _json_or_raw(value)
            if isinstance(parsed, dict):
                return parsed
            return {}
        if isinstance(value, Mapping):
            return dict(value)
        return {}

    def _resolve_value(self, key: str, value: Any) -> Any:
        if isinstance(value, str) and value.lower().startswith("cyberark://"):
            reference = value.split("://", 1)[1]
            return self._resolve_cyberark(reference)
        if isinstance(value, str) and (key.endswith("_FILE") or key.endswith("_PATH")):
            path = Path(value)
            if not path.is_absolute():
                path = (self.execution_root / path).resolve()
            return str(path)
        return value

    def _resolve_cyberark(self, reference: str) -> Any:
        cache_key = _flatten_environment_key(reference)
        if cache_key in self._cyberark_cache:
            return self._cyberark_cache[cache_key]
        env_key = f"PRIMARY_CREDIT_SECRET_{cache_key}"
        raw_value = os.getenv(env_key)
        if raw_value is None:
            self._logger.debug("cyberark.miss", extra={"reference": reference})
            return None
        resolved = _json_or_raw(raw_value)
        self._cyberark_cache[cache_key] = resolved
        return resolved


def bootstrap_environment(
    *,
    app_name: str | None = None,
    environment_key: str | None = None,
    region: str | None = None,
    execution_root: Path | str | None = None,
) -> QRExecConfig:
    """Initialise the configuration session and persist it to the environment."""

    root_path = Path(execution_root or Path.cwd())
    config = QRExecConfig(
        app_name=app_name or os.getenv("PRIMARY_CREDIT_APP_NAME", DEFAULT_APP_NAME),
        environment_key=environment_key
        or os.getenv("PRIMARY_CREDIT_ENVIRONMENT_KEY", DEFAULT_ENVIRONMENT_KEY),
        region=region or os.getenv("PRIMARY_CREDIT_REGION", DEFAULT_REGION),
        execution_root=root_path,
    )
    config.setup_environment()
    os.environ[BOOTSTRAP_ENV_VAR] = config.to_serialized()
    return config


def load_bootstrap_session(serialized: str | None = None) -> QRExecConfig | None:
    payload = serialized or os.getenv(BOOTSTRAP_ENV_VAR)
    if not payload:
        return None
    return QRExecConfig.from_serialized(payload)


@dataclass(slots=True)
class RuntimeCredentials:
    """Non-sensitive configuration hydrated during bootstrap."""

    app_display_name: str
    app_name: str
    app_version: str
    environment_key: str
    region: str
    uid: str | None = None
    dataset_key: str | None = None
    mlflow_enabled: bool = False
    embeddings_model: str | None = None
    llm_model: str | None = None
    llm_use_case: str | None = None
    llm_embeddings_api: str | None = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def public_config(self) -> Dict[str, Any]:
        payload = {
            "app_display_name": self.app_display_name,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "environment": self.environment_key,
            "region": self.region,
            "dataset_key": self.dataset_key or "",
            "mlflow_enabled": self.mlflow_enabled,
            "embeddings_model": self.embeddings_model or "",
            "llm_model": self.llm_model or "",
            "llm_use_case": self.llm_use_case or "",
        }
        payload.update(self.extra)
        return payload


@dataclass(slots=True)
class StorageCredentials:
    bucket: str
    dataset_key: str | None
    prefix: str = "artifacts/"
    scheme: str = "s3"
    anonymous: bool = False
    key: str | None = None
    secret: str | None = None
    client_kwargs: Dict[str, Any] = field(default_factory=dict)
    s3_additional_kwargs: Dict[str, Any] = field(default_factory=dict)
    use_listings_cache: bool = True
    ca_bundle_path: str | None = None


@dataclass(slots=True)
class LLMParameters:
    model: str
    use_case: str | None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EmbeddingParameters:
    model: str
    parameters: Dict[str, Any] = field(default_factory=dict)


def load_runtime_credentials(
    config: QRExecConfig,
    *,
    env: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
) -> RuntimeCredentials:
    """Hydrate the runtime credential payload from config and request context."""

    environment = env or os.environ
    header_map = {k.lower(): v for k, v in (headers or {}).items()}

    app_display_name = config.get("APP_DISPLAY_NAME") or environment.get(
        "PRIMARY_CREDIT_APP_DISPLAY_NAME",
        "Primary Credit Issuance Workspace",
    )
    app_name = config.get("APP_NAME") or environment.get("PRIMARY_CREDIT_APP_NAME", config.app_name)
    app_version = config.get("APP_VERSION") or environment.get("PRIMARY_CREDIT_APP_VERSION", "dev")
    environment_key = config.get("ENVIRONMENT_KEY") or config.environment_key
    region = config.get("REGION") or config.region
    dataset_key = config.get("S3_DATASET_KEY") or config.get("S3_DATA_SET_KEY")
    embeddings_model = config.get("EMBEDDINGS_MODEL")
    llm_model = config.get("LLM_MODEL")
    llm_use_case = config.get("LLM_USE_CASE")
    llm_embeddings_api = config.get("LLM_EMBEDDINGS_API")
    mlflow_enabled = bool(config.get("MLFLOW_ENABLED", False))

    uid = environment.get("PRIMARY_CREDIT_UID")
    if not uid:
        for candidate in ("x-solara-uid", "x-user-uid", "x-authenticated-user"):
            if candidate in header_map:
                uid = header_map[candidate]
                break

    extra = {
        "llm_embeddings_api": llm_embeddings_api or "",
    }

    return RuntimeCredentials(
        app_display_name=app_display_name,
        app_name=app_name,
        app_version=app_version,
        environment_key=environment_key,
        region=region,
        uid=uid,
        dataset_key=dataset_key,
        mlflow_enabled=mlflow_enabled,
        embeddings_model=embeddings_model,
        llm_model=llm_model,
        llm_use_case=llm_use_case,
        llm_embeddings_api=llm_embeddings_api,
        extra=extra,
    )


def load_storage_credentials(config: QRExecConfig) -> StorageCredentials | None:
    secret_payload = config.get("S3_KEY")
    payload: MutableMapping[str, Any]
    if isinstance(secret_payload, str):
        parsed = _json_or_raw(secret_payload)
        if isinstance(parsed, Mapping):
            payload = dict(parsed)
        else:
            payload = {}
    elif isinstance(secret_payload, Mapping):
        payload = dict(secret_payload)
    else:
        payload = {}

    bucket = payload.get("bucket") or config.get("S3_BUCKET")
    dataset_key = config.get("S3_DATASET_KEY") or config.get("S3_DATA_SET_KEY")
    if not bucket:
        return None

    prefix = payload.get("prefix", "artifacts/")
    if prefix and not str(prefix).endswith("/"):
        prefix = f"{prefix}/"
    scheme = payload.get("scheme", "s3")
    anonymous = bool(payload.get("anonymous", False))
    key = payload.get("key")
    secret = payload.get("secret")
    client_kwargs = dict(payload.get("client_kwargs", {}))
    s3_additional_kwargs = dict(payload.get("s3_additional_kwargs", {}))
    use_listings_cache = payload.get("use_listings_cache")
    if use_listings_cache is None:
        use_listings_cache = True
    ca_bundle_path = config.get("S3EMEA_CERTIFICATE_FILE")
    if ca_bundle_path and client_kwargs.get("verify") is None:
        client_kwargs["verify"] = ca_bundle_path
    endpoint_url = config.get("S3_ENDPOINT_URL")
    if endpoint_url and "endpoint_url" not in client_kwargs:
        client_kwargs["endpoint_url"] = endpoint_url
    default_acl = config.get("S3_DEFAULT_ACL")
    if default_acl and "ACL" not in s3_additional_kwargs:
        s3_additional_kwargs["ACL"] = default_acl

    return StorageCredentials(
        bucket=bucket,
        dataset_key=dataset_key,
        prefix=prefix,
        scheme=scheme,
        anonymous=anonymous,
        key=key,
        secret=secret,
        client_kwargs=client_kwargs,
        s3_additional_kwargs=s3_additional_kwargs,
        use_listings_cache=bool(use_listings_cache),
        ca_bundle_path=ca_bundle_path,
    )


def load_llm_credentials(config: QRExecConfig) -> LLMParameters | None:
    model = config.get("LLM_MODEL")
    if not model:
        return None
    use_case = config.get("LLM_USE_CASE")
    secret_payload = config.get("LLM_KEY")
    parameters: Dict[str, Any] = {}
    if isinstance(secret_payload, Mapping):
        parameters.update(secret_payload)
    elif isinstance(secret_payload, str):
        parsed = _json_or_raw(secret_payload)
        if isinstance(parsed, Mapping):
            parameters.update(parsed)

    api_base = config.get("LLM_API") or config.get("LLM_API_BASE")
    if api_base:
        parameters.setdefault("api_base", api_base)

    api_key = config.get("LLM_API_KEY")
    if api_key:
        parameters.setdefault("api_key", api_key)

    return LLMParameters(model=model, use_case=use_case, parameters=parameters)


def load_embedding_credentials(config: QRExecConfig) -> EmbeddingParameters | None:
    model = config.get("EMBEDDINGS_MODEL")
    if not model:
        return None
    secret_payload = config.get("EMBEDDINGS_KEY")
    parameters: Dict[str, Any] = {}
    if isinstance(secret_payload, Mapping):
        parameters.update(secret_payload)
    elif isinstance(secret_payload, str):
        parsed = _json_or_raw(secret_payload)
        if isinstance(parsed, Mapping):
            parameters.update(parsed)

    api_base = config.get("LLM_EMBEDDINGS_API") or config.get("EMBEDDINGS_API")
    if api_base:
        parameters.setdefault("api_base", api_base)

    api_key = config.get("EMBEDDINGS_API_KEY")
    if api_key:
        parameters.setdefault("api_key", api_key)

    return EmbeddingParameters(model=model, parameters=parameters)

