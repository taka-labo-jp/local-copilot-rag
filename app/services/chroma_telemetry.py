"""Chroma telemetry bridge.

ローカル用途で不要な product telemetry を無効化するための no-op 実装。
"""

from chromadb.config import System
from chromadb.telemetry.product import ProductTelemetryClient, ProductTelemetryEvent
from overrides import override


class NoOpProductTelemetry(ProductTelemetryClient):
    """Chroma product telemetry を送信しない実装。"""

    def __init__(self, system: System):
        super().__init__(system)

    @override
    def capture(self, event: ProductTelemetryEvent) -> None:
        return None
