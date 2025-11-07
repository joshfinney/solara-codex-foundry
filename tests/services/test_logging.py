import logging
import json

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


def test_logstash_payload_format(caplog, monkeypatch):
    monkeypatch.setenv("PRIMARY_CREDIT_LOG_FORMAT", "human")
    caplog.set_level(logging.DEBUG, logger="test-logstash")

    logger = StructuredLogger("test-logstash")
    logger.configure_context(
        project_name="primary-credit",
        environment="DEV",
        region="eu-west-2",
        user_id="user-123",
        page_type="new_issue",
    )
    logger.configure_logstash_endpoints(["https://logs.dev"])

    logger.info(
        "pandas_ai.chat.audit",
        conversation_id="conv-1",
        event_type="ai_response",
        event_data={"response": [], "last_code_executed": None, "elapsed_time_ms": 10, "logs": "out"},
    )

    records = [
        record for record in caplog.records if record.name == "test-logstash" and record.message.startswith("[Logstash:")
    ]
    assert records
    prefix, payload = records[-1].message.split(" ", 1)
    assert prefix == "[Logstash:https://logs.dev]"
    body = json.loads(payload)
    assert body["project_name"] == "primary-credit"
    assert body["environment"] == "dev"
    assert body["region"] == "EU-WEST-2"
    assert body["user_id"] == "user-123"
    assert body["conversation_id"] == "conv-1"
    assert body["event_type"] == "ai_response"
    assert body["page_type"] == "new_issue"
    assert body["event_data"]["elapsed_time_ms"] == 10
