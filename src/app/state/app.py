"""Primary Credit application controller and helpers."""

from __future__ import annotations

import asyncio
import dataclasses
import uuid
from typing import Optional

import solara

from app.models import app as app_models
from app.models import dataset as dataset_models
from app.services.credentials import RuntimeCredentials
from app.services.logging import StructuredLogger
from app.services.storage import StorageClient
from app.services.tasks import SessionTasks
from app.state.chat import ChatController


class AppController:
    """High level orchestrator for the Primary Credit experience."""

    def __init__(
        self,
        *,
        chat_controller: ChatController,
        logger: StructuredLogger,
        storage_client: StorageClient,
    ) -> None:
        self.chat = chat_controller
        self.logger = logger
        self.tasks = SessionTasks(logger, storage_client)
        self.state: solara.Reactive[app_models.AppState] = solara.reactive(app_models.AppState())
        self._credentials: Optional[RuntimeCredentials] = None
        self._bootstrap_started = False
        self._bootstrap_inflight = False
        self._start_bootstrap()

    # ------------------------------------------------------------------ lifecycle helpers
    def _start_bootstrap(self) -> None:
        if self._bootstrap_started:
            return
        self._bootstrap_started = True
        self._spawn(self._bootstrap())

    def _spawn(self, coroutine):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(coroutine)
        else:
            loop.create_task(coroutine)

    # ------------------------------------------------------------------ authentication gates
    def authenticate(self, username: str) -> None:
        def updater(prev: app_models.AppState):
            gate = dataclasses.replace(prev.gate, is_authenticated=True, username=username)
            return {"gate": gate}

        self.state.update(updater)

    def accept_terms(self) -> None:
        def updater(prev: app_models.AppState):
            gate = dataclasses.replace(prev.gate, has_accepted_terms=True)
            return {"gate": gate}

        self.state.update(updater)
        self.chat.record_attestation(True)

    # ------------------------------------------------------------------ bootstrap + dataset loading
    async def _bootstrap(self) -> None:
        if self._bootstrap_inflight:
            return
        self._bootstrap_inflight = True
        self.state.update(lambda prev: {"session": dataclasses.replace(prev.session, bootstrapping=True)})
        try:
            bootstrap = await self.tasks.bootstrap()
        except Exception as error:  # noqa: BLE001
            self.logger.error("bootstrap.failed", error=str(error))
            self.state.update(
                lambda prev: {
                    "session": dataclasses.replace(
                        prev.session,
                        bootstrapping=False,
                        error=str(error),
                        ready=False,
                    )
                }
            )
            self._bootstrap_inflight = False
            return

        self._credentials = bootstrap.credentials
        self.state.update(
            lambda prev: {
                "session": dataclasses.replace(
                    prev.session,
                    bootstrapping=False,
                    celery_ready=bootstrap.celery_ready,
                    error=None,
                    public_config=bootstrap.public_config(),
                    ready=False,
                    loading_label="Loading issuance data…",
                )
            }
        )
        await self._load_dataset()
        self._bootstrap_inflight = False

    async def _load_dataset(self) -> None:
        creds = self._credentials
        if creds is None:
            return
        self.state.update(
            lambda prev: {
                "session": dataclasses.replace(prev.session, bootstrapping=True, loading_label="Loading issuance data…")
            }
        )
        try:
            dataset = await self.tasks.load_dataset(creds)
        except Exception as error:  # noqa: BLE001
            self.logger.error("dataset.load.failed", error=str(error))
            self.state.update(
                lambda prev: {
                    "session": dataclasses.replace(
                        prev.session,
                        bootstrapping=False,
                        error=str(error),
                        ready=False,
                    )
                }
            )
            return

        lookback = min(self.state.value.dataset.lookback_days, dataset.max_window_days)

        def updater(prev: app_models.AppState):
            dataset_state = dataclasses.replace(
                prev.dataset,
                raw=dataset,
                filtered=None,
                cache={},
                lookback_days=lookback,
                max_lookback_days=dataset.max_window_days,
                cache_hits=0,
                cache_misses=0,
                last_duration_ms=None,
                last_cache_hit=False,
            )
            session_state = dataclasses.replace(prev.session, bootstrapping=False, loading_label="Applying filters…")
            return {"dataset": dataset_state, "session": session_state}

        self.state.update(updater)
        await self._apply_filter(lookback)
        self.state.update(
            lambda prev: {
                "session": dataclasses.replace(prev.session, ready=True, loading_label="Workspace ready"),
            }
        )

    async def _apply_filter(self, window_days: int) -> None:
        dataset = self.state.value.dataset.raw
        if dataset is None:
            return

        cached = self.state.value.dataset.cache.get(window_days)
        if cached is not None:
            cached_hit = dataclasses.replace(cached, cache_hit=True)

            def cache_updater(prev: app_models.AppState):
                new_cache = dict(prev.dataset.cache)
                new_cache[window_days] = cached
                dataset_state = dataclasses.replace(
                    prev.dataset,
                    filtered=cached_hit,
                    cache=new_cache,
                    lookback_days=window_days,
                    cache_hits=prev.dataset.cache_hits + 1,
                    last_duration_ms=cached.duration_ms,
                    last_cache_hit=True,
                )
                return {"dataset": dataset_state}

            self.logger.info("dataset.filter.cache_hit", window_days=window_days, row_count=cached.row_count)
            self.state.update(cache_updater)
            return

        self.state.update(lambda prev: {"dataset": dataclasses.replace(prev.dataset, lookback_days=window_days)})
        try:
            result = await self.tasks.filter_dataset(dataset, window_days)
        except Exception as error:  # noqa: BLE001
            self.logger.error("dataset.filter.failed", window_days=window_days, error=str(error))
            return

        def assign(prev: app_models.AppState):
            cache = dict(prev.dataset.cache)
            cache[window_days] = result
            dataset_state = dataclasses.replace(
                prev.dataset,
                filtered=result,
                cache=cache,
                lookback_days=window_days,
                cache_misses=prev.dataset.cache_misses + 1,
                last_duration_ms=result.duration_ms,
                last_cache_hit=False,
            )
            return {"dataset": dataset_state}

        self.logger.info(
            "dataset.filter.success",
            window_days=window_days,
            row_count=result.row_count,
            duration_ms=result.duration_ms,
        )
        self.state.update(assign)

    # ------------------------------------------------------------------ UI interactions
    def set_active_tab(self, tab: str) -> None:
        self.state.update(lambda prev: {"ui": dataclasses.replace(prev.ui, active_tab=tab)})

    def toggle_sidebar(self) -> None:
        self.state.update(lambda prev: {"ui": dataclasses.replace(prev.ui, sidebar_open=not prev.ui.sidebar_open)})

    def set_sidebar(self, open_: bool) -> None:
        self.state.update(lambda prev: {"ui": dataclasses.replace(prev.ui, sidebar_open=open_)})

    def set_lookback_days(self, window_days: int) -> None:
        window_days = max(1, min(window_days, self.state.value.dataset.max_lookback_days))
        self.state.update(lambda prev: {"dataset": dataclasses.replace(prev.dataset, lookback_days=window_days)})
        self._spawn(self._apply_filter(window_days))

    def update_inline_feedback_text(self, text: str) -> None:
        self.state.update(lambda prev: {"ui": dataclasses.replace(prev.ui, inline_feedback_text=text)})

    def submit_inline_feedback(self) -> None:
        comments = self.state.value.ui.inline_feedback_text.strip()
        if not comments:
            return
        conversation_id = self.state.value.ui.conversation_id
        self.state.update(
            lambda prev: {
                "ui": dataclasses.replace(prev.ui, inline_feedback_status="submitting")
            }
        )
        payload = dataset_models.InlineFeedback(conversation_id=conversation_id, comments=comments)
        self._spawn(self._submit_inline_feedback(payload))

    async def _submit_inline_feedback(self, payload: dataset_models.InlineFeedback) -> None:
        try:
            await self.tasks.submit_inline_feedback(payload)
        finally:
            def complete(prev: app_models.AppState):
                return {
                    "ui": dataclasses.replace(
                        prev.ui,
                        inline_feedback_text="",
                        inline_feedback_status="submitted",
                        conversation_id=uuid.uuid4().hex[:8],
                    )
                }

            self.state.update(complete)
            await asyncio.sleep(1.5)
            self.state.update(
                lambda prev: {
                    "ui": dataclasses.replace(prev.ui, inline_feedback_status="idle")
                }
            )

    # ------------------------------------------------------------------ convenience accessors
    def get_filtered_rows(self) -> list[dict[str, object]]:
        filtered = self.state.value.dataset.filtered
        if filtered:
            return filtered.rows
        raw = self.state.value.dataset.raw
        return raw.rows if raw else []

    def get_filtered_frame(self):  # type: ignore[override]
        filtered = self.state.value.dataset.filtered
        if filtered and filtered.frame is not None:
            return filtered.frame
        raw = self.state.value.dataset.raw
        return raw.frame if raw else None


def use_app_controller(controller: AppController) -> app_models.AppState:
    """Convenience hook for reading the reactive app state."""

    return controller.state.use()
