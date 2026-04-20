"""LLMヘルパーのユニットテスト。"""

import pytest

from app.services.llm import _parse_todo_preview_payload


class TestTodoPreviewPayload:
    """TODO草案JSONの正規化を確認する。"""

    def test_parse_object_payload(self):
        payload = '{"title":"設計確認","description":"回答を整理する","acceptance_criteria":"完了条件を確認する"}'

        result = _parse_todo_preview_payload(payload)

        assert result["title"] == "設計確認"
        assert result["description"] == "回答を整理する"
        assert result["acceptance_criteria"] == "完了条件を確認する"

    def test_parse_list_payload(self):
        payload = '[{"title":"設計確認","description":"回答を整理する","acceptance_criteria":["完了条件を確認する","レビュー完了"]}]'

        result = _parse_todo_preview_payload(payload)

        assert result["title"] == "設計確認"
        assert result["description"] == "回答を整理する"
        assert result["acceptance_criteria"] == "完了条件を確認する\nレビュー完了"

    def test_parse_fenced_payload_with_alias_keys(self):
        payload = '```json\n{"name":"設計確認","summary":"回答を整理する","doneDefinition":["レビュー完了"]}\n```'

        result = _parse_todo_preview_payload(payload)

        assert result["title"] == "設計確認"
        assert result["description"] == "回答を整理する"
        assert result["acceptance_criteria"] == "レビュー完了"

    def test_parse_invalid_payload_raises(self):
        with pytest.raises(RuntimeError):
            _parse_todo_preview_payload('["invalid"]')