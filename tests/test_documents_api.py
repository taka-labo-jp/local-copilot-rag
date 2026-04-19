"""ドキュメントAPI のユニットテスト。

検証項目:
- ファイルアップロード（正常系・未対応形式・空ファイル）
- ドキュメント一覧取得
- ドキュメント削除（正常系・存在しないID）
- 拡張子ホワイトリスト検証
- プロジェクト CRUD
- プロジェクト間移動
- 一括アップロード
"""
import io
from pathlib import Path

import pytest


class TestUploadDocument:
    """POST /api/documents のテスト。"""

    def test_upload_txt_file(self, app_client):
        """テキストファイルの正常アップロード。"""
        content = "これはテスト仕様書です。\n要件1: テスト対象の機能。"
        resp = app_client.post(
            "/api/documents",
            files={"file": ("spec.txt", io.BytesIO(content.encode("utf-8")), "text/plain")},
            data={"wing": "specifications", "room": "test-room", "project": ""},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == "spec.txt"
        assert body["drawer_count"] >= 1
        assert body["wing"] == "specifications"

    def test_upload_md_file(self, app_client):
        """Markdownファイルの正常アップロード。"""
        content = "# 仕様書\n\n## 概要\nテスト用の仕様書です。"
        resp = app_client.post(
            "/api/documents",
            files={"file": ("readme.md", io.BytesIO(content.encode("utf-8")), "text/markdown")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == "readme.md"
        assert body["text_chunk_count"] >= 1

    def test_upload_unsupported_extension(self, app_client):
        """未対応の拡張子は415エラーを返す。"""
        resp = app_client.post(
            "/api/documents",
            files={"file": ("malware.exe", io.BytesIO(b"MZ..."), "application/octet-stream")},
        )
        assert resp.status_code == 415
        assert "未対応の形式" in resp.json()["detail"]

    def test_upload_empty_file(self, app_client):
        """空ファイルは400エラーを返す。"""
        resp = app_client.post(
            "/api/documents",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert resp.status_code == 400
        assert "空のファイル" in resp.json()["detail"]

    @pytest.mark.parametrize("ext", [".py", ".exe", ".sh", ".bat", ".dll", ".so", ".bin"])
    def test_blocked_extensions(self, app_client, ext):
        """実行可能ファイル等の危険な拡張子はすべてブロックされる。"""
        resp = app_client.post(
            "/api/documents",
            files={"file": (f"test{ext}", io.BytesIO(b"data"), "application/octet-stream")},
        )
        assert resp.status_code == 415

    def test_upload_overwrite_existing(self, app_client):
        """同一ファイル名の再アップロードで上書きされる。"""
        content_v1 = "バージョン1の内容"
        content_v2 = "バージョン2の内容（更新済み）"
        # 1回目
        resp1 = app_client.post(
            "/api/documents",
            files={"file": ("spec.txt", io.BytesIO(content_v1.encode()), "text/plain")},
        )
        assert resp1.status_code == 200
        assert resp1.json()["overwritten_count"] == 0

        # 2回目（上書き）
        resp2 = app_client.post(
            "/api/documents",
            files={"file": ("spec.txt", io.BytesIO(content_v2.encode()), "text/plain")},
        )
        assert resp2.status_code == 200
        assert resp2.json()["overwritten_count"] == 1

    def test_upload_with_project(self, app_client):
        """プロジェクト指定付きでアップロードできる。"""
        content = "プロジェクトAの仕様"
        resp = app_client.post(
            "/api/documents",
            files={"file": ("proj_a.txt", io.BytesIO(content.encode()), "text/plain")},
            data={"project": "ProjectA"},
        )
        assert resp.status_code == 200
        assert resp.json()["project"] == "ProjectA"


class TestListDocuments:
    """GET /api/documents のテスト。"""

    def test_list_empty(self, app_client):
        """初期状態では空リストを返す。"""
        resp = app_client.get("/api/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_upload(self, app_client):
        """アップロード後に一覧へ反映される。"""
        app_client.post(
            "/api/documents",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        resp = app_client.get("/api/documents")
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) == 1
        assert docs[0]["filename"] == "test.txt"


class TestDeleteDocument:
    """DELETE /api/documents/{doc_id} のテスト。"""

    def test_delete_existing(self, app_client):
        """登録済みドキュメントを正常に削除できる。"""
        app_client.post(
            "/api/documents",
            files={"file": ("del.txt", io.BytesIO(b"to be deleted"), "text/plain")},
        )
        docs = app_client.get("/api/documents").json()
        doc_id = docs[0]["id"]

        resp = app_client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 200
        assert "削除しました" in resp.json()["message"]

        # 削除後は一覧から消える
        assert len(app_client.get("/api/documents").json()) == 0

    def test_delete_nonexistent(self, app_client):
        """存在しないIDの削除は404を返す。"""
        resp = app_client.delete("/api/documents/99999")
        assert resp.status_code == 404


class TestProjects:
    """プロジェクト CRUD のテスト。"""

    def test_create_project(self, app_client):
        """新規プロジェクトを作成できる。"""
        resp = app_client.post("/api/documents/projects", json={"name": "TestProject"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "TestProject"
        assert "id" in body

    def test_create_duplicate_project(self, app_client):
        """同名プロジェクトの作成は409エラーを返す。"""
        app_client.post("/api/documents/projects", json={"name": "Dup"})
        resp = app_client.post("/api/documents/projects", json={"name": "Dup"})
        assert resp.status_code == 409

    def test_create_empty_name(self, app_client):
        """空名のプロジェクト作成は400エラーを返す。"""
        resp = app_client.post("/api/documents/projects", json={"name": ""})
        assert resp.status_code == 400

    def test_list_projects(self, app_client):
        """プロジェクト一覧を取得できる。"""
        app_client.post("/api/documents/projects", json={"name": "P1"})
        app_client.post("/api/documents/projects", json={"name": "P2"})
        resp = app_client.get("/api/documents/projects")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "P1" in names
        assert "P2" in names

    def test_delete_project(self, app_client):
        """プロジェクトを削除できる。"""
        create_resp = app_client.post("/api/documents/projects", json={"name": "Del"})
        pid = create_resp.json()["id"]
        resp = app_client.delete(f"/api/documents/projects/{pid}")
        assert resp.status_code == 200
        assert "削除しました" in resp.json()["message"]

    def test_delete_nonexistent_project(self, app_client):
        """存在しないプロジェクトの削除は404を返す。"""
        resp = app_client.delete("/api/documents/projects/99999")
        assert resp.status_code == 404


class TestMoveDocument:
    """PATCH /api/documents/{doc_id}/project のテスト。"""

    def test_move_to_project(self, app_client):
        """ドキュメントをプロジェクトに移動できる。"""
        app_client.post("/api/documents/projects", json={"name": "Target"})
        app_client.post(
            "/api/documents",
            files={"file": ("move.txt", io.BytesIO(b"move test"), "text/plain")},
        )
        doc_id = app_client.get("/api/documents").json()[0]["id"]
        resp = app_client.patch(f"/api/documents/{doc_id}/project", json={"project": "Target"})
        assert resp.status_code == 200
        assert resp.json()["project"] == "Target"

    def test_move_to_nonexistent_project(self, app_client):
        """存在しないプロジェクトへの移動は404を返す。"""
        app_client.post(
            "/api/documents",
            files={"file": ("move2.txt", io.BytesIO(b"data"), "text/plain")},
        )
        doc_id = app_client.get("/api/documents").json()[0]["id"]
        resp = app_client.patch(f"/api/documents/{doc_id}/project", json={"project": "Ghost"})
        assert resp.status_code == 404

    def test_move_nonexistent_doc(self, app_client):
        """存在しないドキュメントの移動は404を返す。"""
        resp = app_client.patch("/api/documents/99999/project", json={"project": ""})
        assert resp.status_code == 404


class TestBulkUpload:
    """POST /api/documents/bulk-upload のテスト。"""

    def test_bulk_upload_empty_folder(self, app_client):
        """空フォルダの一括取込は0件を返す。"""
        resp = app_client.post("/api/documents/bulk-upload")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["uploaded"] == 0

    def test_bulk_upload_with_files(self, app_client, mock_settings):
        """フォルダ内ファイルが正常に一括取込される。"""
        bulk_dir = Path(mock_settings.bulk_upload_dir)
        (bulk_dir / "spec1.txt").write_text("仕様1", encoding="utf-8")
        (bulk_dir / "spec2.md").write_text("# 仕様2", encoding="utf-8")

        resp = app_client.post("/api/documents/bulk-upload")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["uploaded"] == 2
        assert body["failed"] == 0

    def test_bulk_upload_with_unsupported(self, app_client, mock_settings):
        """未対応ファイルはスキップされ failed カウントが増える。"""
        bulk_dir = Path(mock_settings.bulk_upload_dir)
        (bulk_dir / "ok.txt").write_text("ok", encoding="utf-8")
        (bulk_dir / "bad.exe").write_bytes(b"MZ")

        resp = app_client.post("/api/documents/bulk-upload")
        body = resp.json()
        assert body["uploaded"] == 1
        assert body["failed"] == 1

    def test_bulk_upload_project_from_subfolder(self, app_client, mock_settings):
        """サブフォルダ名がプロジェクト名として使われる。"""
        bulk_dir = Path(mock_settings.bulk_upload_dir)
        proj_dir = bulk_dir / "MyProject"
        proj_dir.mkdir()
        (proj_dir / "doc.txt").write_text("project doc", encoding="utf-8")

        resp = app_client.post("/api/documents/bulk-upload")
        body = resp.json()
        assert body["uploaded"] == 1
        result = body["results"][0]
        assert result["project"] == "MyProject"


class TestAllowedExtensions:
    """許可拡張子のホワイトリスト検証。"""

    EXPECTED = {
        ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt",
        ".pdf", ".html", ".htm", ".md", ".txt", ".csv",
        ".json", ".xml", ".epub", ".zip",
    }

    def test_allowed_extensions_match(self):
        """ALLOWED_EXTENSIONS が期待されるセットと一致する。"""
        from app.api.documents import ALLOWED_EXTENSIONS
        assert ALLOWED_EXTENSIONS == self.EXPECTED

    def test_no_executable_extensions(self):
        """実行可能拡張子が含まれていないことを確認する。"""
        from app.api.documents import ALLOWED_EXTENSIONS
        dangerous = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".py", ".rb", ".js", ".php", ".dll", ".so"}
        assert ALLOWED_EXTENSIONS.isdisjoint(dangerous)
