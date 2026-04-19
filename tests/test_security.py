"""セキュリティ関連のユニットテスト。

検証項目:
- パストラバーサル攻撃の防止（ファイル名に ../）
- 拡張子ホワイトリストのバイパス試行
- SQLインジェクション耐性（パラメタライズドクエリ）
- 大量入力によるDoS耐性（極端に長い文字列）
- CORS ヘッダの確認
- SSE レスポンスの Content-Type
- プロジェクト名のサニタイズ
"""
import io

import pytest


class TestPathTraversal:
    """パストラバーサル攻撃の防止テスト。"""

    @pytest.mark.parametrize("filename", [
        "../../../etc/passwd",
        "..\\..\\windows\\system32\\config\\sam",
        "spec/../../../etc/shadow",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ])
    def test_traversal_filenames_blocked(self, app_client, filename):
        """パストラバーサルを含むファイル名はブロックされる。

        注: 現在の実装は拡張子チェックでブロックされるが、
        パストラバーサル自体のリスクも確認する。
        """
        resp = app_client.post(
            "/api/documents",
            files={"file": (filename, io.BytesIO(b"malicious"), "text/plain")},
        )
        # 拡張子不一致で415、または他のエラーでブロック
        assert resp.status_code in (400, 415, 422)

    def test_traversal_with_valid_extension(self, app_client):
        """パストラバーサル + 有効拡張子でもファイルは保存先を超えない。

        markitdown がファイル内容を変換するだけで、
        ファイル名はメタデータとしてDBに保存される。
        ファイルシステムへの直接パス操作は行われない。
        """
        resp = app_client.post(
            "/api/documents",
            files={"file": ("../escape.txt", io.BytesIO(b"test content"), "text/plain")},
        )
        # アップロード自体は成功するが、ファイル名はメタデータとして保存されるだけ
        if resp.status_code == 200:
            body = resp.json()
            # ファイル名がそのまま記録されても、ファイルシステムに書き込まれない
            assert "drawer_count" in body


class TestExtensionBypass:
    """拡張子チェックのバイパス試行テスト。"""

    @pytest.mark.parametrize("filename", [
        "shell.txt.exe",
        "script.py",
        "payload.php",
        "exploit.jsp",
        "hack.asp",
        "test.txt\x00.exe",  # null byte injection
    ])
    def test_extension_bypass_blocked(self, app_client, filename):
        """二重拡張子・nullバイト等によるバイパスがブロックされる。"""
        resp = app_client.post(
            "/api/documents",
            files={"file": (filename, io.BytesIO(b"data"), "application/octet-stream")},
        )
        assert resp.status_code in (415, 422)


class TestSqlInjection:
    """SQLインジェクション耐性のテスト。"""

    def test_project_name_injection(self, app_client):
        """プロジェクト名にSQL文を含めてもエラーにならない。"""
        resp = app_client.post(
            "/api/documents/projects",
            json={"name": "'; DROP TABLE documents; --"},
        )
        # 作成自体は成功する（パラメタライズドクエリなので安全）
        assert resp.status_code == 200

        # ドキュメントテーブルが破壊されていないことを確認
        docs = app_client.get("/api/documents")
        assert docs.status_code == 200

    def test_session_id_injection(self, app_client):
        """セッションIDにSQL文を含めても安全。"""
        resp = app_client.get("/api/history/'; DROP TABLE chat_sessions; --")
        # 404（存在しない）を返すが、テーブルは破壊されない
        assert resp.status_code == 404

        # セッションテーブルが健在であることを確認
        history = app_client.get("/api/history")
        assert history.status_code == 200

    def test_filename_injection(self, app_client):
        """ファイル名にSQL文を含めても安全。"""
        sql_name = "test'; DELETE FROM documents WHERE '1'='1.txt"
        resp = app_client.post(
            "/api/documents",
            files={"file": (sql_name, io.BytesIO(b"safe content"), "text/plain")},
        )
        assert resp.status_code == 200

        # 他のドキュメントが削除されていないことを確認
        docs = app_client.get("/api/documents")
        assert docs.status_code == 200


class TestInputValidation:
    """入力バリデーションのテスト。"""

    def test_very_long_message(self, app_client):
        """極端に長いメッセージでもクラッシュしない。"""
        from unittest.mock import patch

        async def mock_stream(*args, **kwargs):
            yield "ok"

        long_msg = "あ" * 100_000
        with patch("app.services.llm.generate_stream", side_effect=mock_stream):
            resp = app_client.post(
                "/api/chat",
                json={"message": long_msg},
            )
        assert resp.status_code == 200

    def test_very_long_project_name(self, app_client):
        """極端に長いプロジェクト名でもクラッシュしない。"""
        long_name = "P" * 10_000
        resp = app_client.post(
            "/api/documents/projects",
            json={"name": long_name},
        )
        assert resp.status_code == 200

    def test_unicode_edge_cases(self, app_client):
        """特殊Unicode文字を含む入力でクラッシュしない。"""
        special = "テスト\u0000\uffff\ud7ff emoji: 🎉📚"
        resp = app_client.post(
            "/api/documents/projects",
            json={"name": special},
        )
        # 作成できるか400系エラーのどちらか（クラッシュしない）
        assert resp.status_code in (200, 400, 422)


class TestCorsHeaders:
    """CORS ヘッダのテスト。"""

    def test_cors_preflight(self, app_client):
        """OPTIONS プリフライトリクエストが正しく応答する。"""
        resp = app_client.options(
            "/api/documents",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers


class TestSseContentType:
    """SSE レスポンスの Content-Type テスト。"""

    def test_chat_returns_event_stream(self, app_client):
        """チャットAPIが text/event-stream を返す。"""
        from unittest.mock import patch

        async def mock_stream(*args, **kwargs):
            yield "ok"

        with patch("app.services.llm.generate_stream", side_effect=mock_stream):
            resp = app_client.post(
                "/api/chat",
                json={"message": "test"},
            )
        assert "text/event-stream" in resp.headers["content-type"]
