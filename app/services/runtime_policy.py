"""ランタイムの外部送信ポリシーを適用するユーティリティ。"""

import os


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def apply_runtime_network_policy() -> dict[str, str]:
    """不要なテレメトリ送信を抑止する環境変数を設定する。"""
    applied: dict[str, str] = {}

    if not _is_truthy(os.getenv("DISABLE_RUNTIME_TELEMETRY", "true")):
        return applied

    defaults = {
        "DO_NOT_TRACK": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "ANONYMIZED_TELEMETRY": "False",
        "OTEL_SDK_DISABLED": "true",
        "OTEL_TRACES_EXPORTER": "none",
        "OTEL_METRICS_EXPORTER": "none",
        "OTEL_LOGS_EXPORTER": "none",
    }

    if _is_truthy(os.getenv("EMBEDDING_LOCAL_FILES_ONLY", "true")):
        defaults["HF_HUB_OFFLINE"] = "1"
        defaults["TRANSFORMERS_OFFLINE"] = "1"

    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value
            applied[key] = value

    return applied