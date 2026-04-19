"""ランタイム送信抑止ポリシーのテスト。"""

from app.services.runtime_policy import apply_runtime_network_policy


def test_runtime_policy_applies_defaults(monkeypatch):
    """既定設定でテレメトリ抑止用の環境変数が適用される。"""
    keys = [
        "DISABLE_RUNTIME_TELEMETRY",
        "DO_NOT_TRACK",
        "HF_HUB_DISABLE_TELEMETRY",
        "ANONYMIZED_TELEMETRY",
        "OTEL_SDK_DISABLED",
        "OTEL_TRACES_EXPORTER",
        "OTEL_METRICS_EXPORTER",
        "OTEL_LOGS_EXPORTER",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "EMBEDDING_LOCAL_FILES_ONLY",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)

    applied = apply_runtime_network_policy()

    assert applied["DO_NOT_TRACK"] == "1"
    assert applied["HF_HUB_DISABLE_TELEMETRY"] == "1"
    assert applied["ANONYMIZED_TELEMETRY"] == "False"
    assert applied["OTEL_SDK_DISABLED"] == "true"
    assert applied["OTEL_TRACES_EXPORTER"] == "none"
    assert applied["OTEL_METRICS_EXPORTER"] == "none"
    assert applied["OTEL_LOGS_EXPORTER"] == "none"
    assert applied["HF_HUB_OFFLINE"] == "1"
    assert applied["TRANSFORMERS_OFFLINE"] == "1"


def test_runtime_policy_can_be_disabled(monkeypatch):
    """明示的に無効化した場合は環境変数を変更しない。"""
    monkeypatch.setenv("DISABLE_RUNTIME_TELEMETRY", "false")
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)

    applied = apply_runtime_network_policy()

    assert applied == {}
    assert "DO_NOT_TRACK" not in applied


def test_runtime_policy_keeps_existing_values(monkeypatch):
    """既存の環境変数は上書きしない。"""
    monkeypatch.delenv("DISABLE_RUNTIME_TELEMETRY", raising=False)
    monkeypatch.setenv("DO_NOT_TRACK", "0")

    applied = apply_runtime_network_policy()

    assert "DO_NOT_TRACK" not in applied
