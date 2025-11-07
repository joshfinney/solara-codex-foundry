import logging

from app.services.logging import StructuredLogger


def test_human_readable_console(caplog, monkeypatch):
    monkeypatch.setenv("PRIMARY_CREDIT_LOG_FORMAT", "human")
    caplog.set_level(logging.INFO)

    logger = StructuredLogger("test-logger")
    logger.info("test.event", user="alice", attempt=1)

    records = [record for record in caplog.records if record.name == "test-logger"]
    assert records
    message = records[-1].message
    assert "test.event" in message
    assert "user=alice" in message
    assert "attempt=1" in message
