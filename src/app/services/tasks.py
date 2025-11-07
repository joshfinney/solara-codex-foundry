"""Async tasks responsible for bootstrapping and data preparation."""

from __future__ import annotations

import asyncio
import datetime as _dt
import os
import random
from pathlib import Path
from typing import Any, Iterable

from app.core.pandas_compat import pd
from app.models import dataset as dataset_models

from . import credentials, telemetry
from .logging import StructuredLogger
from .storage import ArtifactMetadata, StorageClient


class SessionTasks:
    """Bundle of asynchronous tasks used by the app controller."""

    def __init__(
        self,
        logger: StructuredLogger,
        storage_client: StorageClient,
        *,
        execution_root: Path | None = None,
    ) -> None:
        self._logger = logger
        self._storage = storage_client
        self._execution_root = execution_root or Path(
            os.getenv("PRIMARY_CREDIT_EXECUTION_ROOT", Path(__file__).resolve().parents[3])
        )

    # ------------------------------------------------------------------ bootstrap
    async def bootstrap(self) -> dataset_models.BootstrapResult:
        with telemetry.telemetry_span(self._logger, "bootstrap"):
            config_session = credentials.load_bootstrap_session()
            if config_session is None:
                config_session = credentials.bootstrap_environment(execution_root=self._execution_root)

            runtime = credentials.load_runtime_credentials(config_session)
            self._logger.configure_context(
                project_name=runtime.app_name,
                environment=runtime.environment_key,
                region=runtime.region,
                user_id=runtime.uid,
            )
            if runtime.logstash_endpoints:
                self._logger.configure_logstash_endpoints(runtime.logstash_endpoints)
            storage_creds = credentials.load_storage_credentials(config_session)
            llm_creds = credentials.load_llm_credentials(config_session)
            embedding_creds = credentials.load_embedding_credentials(config_session)

            if storage_creds:
                self._storage.configure(storage_creds)

            self._logger.info(
                "bootstrap.complete",
                bucket=getattr(storage_creds, "bucket", None),
                dataset_key=runtime.dataset_key,
                environment=runtime.environment_key,
            )
            return dataset_models.BootstrapResult(
                config=config_session,
                credentials=runtime,
                storage=storage_creds,
                llm=llm_creds,
                embeddings=embedding_creds,
            )

    # ------------------------------------------------------------------ dataset loading
    async def load_dataset(self, creds: credentials.RuntimeCredentials) -> dataset_models.DatasetResult:
        with telemetry.telemetry_span(self._logger, "dataset.load"):
            if creds.dataset_key:
                dataset = await self._load_remote_dataset(creds)
                if dataset:
                    return dataset
            self._logger.warning("dataset.synthetic", reason="using synthetic fallback")
            return self._generate_synthetic_dataset()

    async def _load_remote_dataset(
        self, creds: credentials.RuntimeCredentials
    ) -> dataset_models.DatasetResult | None:
        dataset_key = creds.dataset_key
        if not dataset_key:
            return None
        try:
            frame, format_name = await asyncio.to_thread(self._storage.read_table, dataset_key)
        except FileNotFoundError:
            self._logger.error("dataset.read_missing", key=dataset_key)
            return None
        if frame is None:
            return None
        format_label = f"s3:{format_name}"
        with telemetry.telemetry_span(self._logger, "dataset.read", source=format_label):
            self._logger.info(
                "dataset.read.complete",
                key=dataset_key,
                rows=len(frame),
                columns=list(frame.columns),
                format=format_name,
            )
        if format_name == "csv" and "issue_date" in frame.columns:
            frame["issue_date"] = pd.to_datetime(frame["issue_date"])
        rows = frame.to_dict("records")
        earliest = frame["issue_date"].min().date()
        latest = frame["issue_date"].max().date()
        return dataset_models.DatasetResult(
            rows=rows,
            frame=frame,
            source=format_label,
            loaded_at=_dt.datetime.now(_dt.timezone.utc),
            earliest_issue_date=earliest,
            latest_issue_date=latest,
        )

    def _generate_synthetic_dataset(self, count: int = 60) -> dataset_models.DatasetResult:
        today = _dt.date.today()
        records = []
        for idx in range(count):
            issue_date = today - _dt.timedelta(days=count - idx - 1)
            records.append(
                {
                    "issue_date": issue_date,
                    "cusip": f"0000{idx:05d}",
                    "issuer": random.choice(["Alpha Bank", "Bravo Credit", "Cascade Holdings", "Delta Capital"]),
                    "tenor": random.choice(["3Y", "5Y", "7Y", "10Y"]),
                    "size_mm": random.choice([250, 500, 750, 1000]),
                    "currency": random.choice(["USD", "EUR"]),
                    "bookrunner": random.choice(["Solara Markets", "Northwind Securities", "Plaza Brokerage"]),
                }
            )
        frame = pd.DataFrame(records)
        frame["issue_date"] = pd.to_datetime(frame["issue_date"])
        earliest = records[0]["issue_date"]
        latest = records[-1]["issue_date"]
        return dataset_models.DatasetResult(
            rows=records,
            frame=frame,
            source="synthetic",
            loaded_at=_dt.datetime.now(_dt.timezone.utc),
            earliest_issue_date=earliest,
            latest_issue_date=latest,
        )

    # ------------------------------------------------------------------ filtering
    async def filter_dataset(
        self, dataset: dataset_models.DatasetResult, window_days: int
    ) -> dataset_models.FilterResult:
        with telemetry.telemetry_span(self._logger, "dataset.filter", window_days=window_days):
            start = _dt.datetime.now(_dt.timezone.utc)
            rows = self._filter_rows(dataset.rows, dataset.latest_issue_date, window_days)
            duration_ms = int((_dt.datetime.now(_dt.timezone.utc) - start).total_seconds() * 1000)
            frame = None
            if dataset.frame is not None:
                cutoff = dataset.latest_issue_date - _dt.timedelta(days=window_days - 1)
                mask = dataset.frame["issue_date"] >= _dt.datetime.combine(cutoff, _dt.time.min)
                frame = dataset.frame.loc[mask]
            return dataset_models.FilterResult(
                window_days=window_days,
                rows=rows,
                frame=frame,
                row_count=len(rows),
                duration_ms=duration_ms,
            )

    def _filter_rows(self, rows: Iterable[dict[str, Any]], latest: _dt.date, window_days: int) -> list[dict[str, Any]]:
        cutoff = latest - _dt.timedelta(days=window_days - 1)
        filtered: list[dict[str, Any]] = []
        for row in rows:
            issue_date = row.get("issue_date")
            if isinstance(issue_date, _dt.datetime):
                issue_date = issue_date.date()
            if issue_date and issue_date >= cutoff:
                filtered.append(row)
        return filtered

    # ------------------------------------------------------------------ feedback
    async def submit_inline_feedback(self, payload: dataset_models.InlineFeedback) -> None:
        with telemetry.telemetry_span(self._logger, "feedback.inline"):
            self._logger.info(
                "feedback.inline.submitted",
                conversation_id=payload.conversation_id,
                comments=payload.comments,
                submitted_at=payload.submitted_at.isoformat(),
            )

    async def upload_artifact(self, name: str, content_type: str, data: bytes) -> ArtifactMetadata:
        return self._storage.upload_artifact(name=name, content_type=content_type, data=data)
