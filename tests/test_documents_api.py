"""ドキュメントAPI のユニットテスト。

検証項目:
- ファイルアップロード（正常系・未対応形式・空ファイル）
- ドキュメント一覧取得
- ドキュメント削除（正常系・存在しないID）
- 拡張子ホワイトリスト検証
- プロジェクト CRUD
- プロジェクト間移動
- 一括アップロード
- 画像ファイル（AI vision 解析）
- drawio ファイル（XML チャンク）
"""
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
    """POST /api/documents/bulk-upload のテスト（SSE ストリーミング）。"""

    @staticmethod
    def _parse_sse(content: bytes) -> list[dict]:
        """SSE レスポンスを JSON イベントのリストにパースする。"""
        import json
        events = []
        for line in content.decode("utf-8").splitlines():
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except Exception:
                    pass
        return events

    def test_bulk_upload_empty_folder(self, app_client):
        """空フォルダの一括取込は0件を返す。"""
        resp = app_client.post("/api/documents/bulk-upload")
        assert resp.status_code == 200
        events = self._parse_sse(resp.content)
        done = next(e for e in events if e.get("type") == "done")
        assert done["total"] == 0
        assert done["uploaded"] == 0

    def test_bulk_upload_with_files(self, app_client, mock_settings):
        """フォルダ内ファイルが正常に一括取込される。"""
        bulk_dir = Path(mock_settings.bulk_upload_dir)
        (bulk_dir / "spec1.txt").write_text("仕様1", encoding="utf-8")
        (bulk_dir / "spec2.md").write_text("# 仕様2", encoding="utf-8")

        resp = app_client.post("/api/documents/bulk-upload")
        assert resp.status_code == 200
        events = self._parse_sse(resp.content)
        done = next(e for e in events if e.get("type") == "done")
        assert done["total"] == 2
        assert done["uploaded"] == 2
        assert done["failed"] == 0

    def test_bulk_upload_with_unsupported(self, app_client, mock_settings):
        """未対応ファイルはスキップされ failed カウントが増える。"""
        bulk_dir = Path(mock_settings.bulk_upload_dir)
        (bulk_dir / "ok.txt").write_text("ok", encoding="utf-8")
        (bulk_dir / "bad.exe").write_bytes(b"MZ")

        resp = app_client.post("/api/documents/bulk-upload")
        events = self._parse_sse(resp.content)
        done = next(e for e in events if e.get("type") == "done")
        assert done["uploaded"] == 1
        assert done["failed"] == 1

    def test_bulk_upload_project_param(self, app_client, mock_settings):
        """project パラメータで指定したプロジェクトに登録される。"""
        bulk_dir = Path(mock_settings.bulk_upload_dir)
        (bulk_dir / "doc.txt").write_text("project doc", encoding="utf-8")

        resp = app_client.post("/api/documents/bulk-upload", data={"project": "MyProject"})
        events = self._parse_sse(resp.content)
        done = next(e for e in events if e.get("type") == "done")
        assert done["uploaded"] == 1


class TestAllowedExtensions:
    """許可拡張子のホワイトリスト検証。"""

    EXPECTED_BASE = {
        ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt",
        ".pdf", ".html", ".htm", ".md", ".txt", ".csv",
        ".json", ".xml", ".epub", ".zip",
    }
    EXPECTED_IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
    EXPECTED_DRAWIO = {".drawio", ".dio"}

    def test_allowed_extensions_contain_base(self):
        """ALLOWED_EXTENSIONS が基本形式を含む。"""
        from app.api.documents import ALLOWED_EXTENSIONS
        assert self.EXPECTED_BASE.issubset(ALLOWED_EXTENSIONS)

    def test_allowed_extensions_contain_images(self):
        """ALLOWED_EXTENSIONS が画像拡張子を含む。"""
        from app.api.documents import ALLOWED_EXTENSIONS
        assert self.EXPECTED_IMAGE.issubset(ALLOWED_EXTENSIONS)

    def test_allowed_extensions_contain_drawio(self):
        """ALLOWED_EXTENSIONS が drawio 拡張子を含む。"""
        from app.api.documents import ALLOWED_EXTENSIONS
        assert self.EXPECTED_DRAWIO.issubset(ALLOWED_EXTENSIONS)

    def test_no_executable_extensions(self):
        """実行可能拡張子が含まれていないことを確認する。"""
        from app.api.documents import ALLOWED_EXTENSIONS
        dangerous = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".py", ".rb", ".js", ".php", ".dll", ".so"}
        assert ALLOWED_EXTENSIONS.isdisjoint(dangerous)


class TestImageUpload:
    """画像ファイルのアップロードテスト（AI vision 解析をモック）。"""

    _AI_RESPONSE = "これはテスト用インフラ構成図です。Webサーバーとデータベースが描かれています。"

    def _make_minimal_png(self) -> bytes:
        """最小限の有効な PNG バイト列を生成する。"""
        import struct, zlib as _zlib
        def png_chunk(tag: bytes, data: bytes) -> bytes:
            c = struct.pack(">I", len(data)) + tag + data
            return c + struct.pack(">I", _zlib.crc32(tag + data) & 0xFFFFFFFF)

        header = b"\x89PNG\r\n\x1a\n"
        ihdr = png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        # 1x1 RGB white pixel
        raw = b"\x00\xff\xff\xff"
        idat = png_chunk(b"IDAT", _zlib.compress(raw))
        iend = png_chunk(b"IEND", b"")
        return header + ihdr + idat + iend

    @pytest.mark.parametrize("ext,mime", [
        (".png", "image/png"),
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
    ])
    def test_upload_image_calls_ai_and_registers(self, app_client, ext, mime):
        """画像ファイルをアップロードすると AI 解析が呼ばれてチャンクが登録される。"""
        png_bytes = self._make_minimal_png()
        with patch(
            "app.api.documents.llm.analyze_image_with_ai",
            new_callable=AsyncMock,
            return_value=self._AI_RESPONSE,
        ):
            resp = app_client.post(
                "/api/documents",
                files={"file": (f"diagram{ext}", io.BytesIO(png_bytes), mime)},
                data={"wing": "specifications", "room": "infra"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == f"diagram{ext}"
        assert body["image_chunk_count"] >= 1
        assert body["drawer_count"] >= 1

    def test_upload_image_ai_failure_returns_500(self, app_client):
        """AI 解析が失敗した場合は 500 エラーを返す。"""
        png_bytes = self._make_minimal_png()
        with patch(
            "app.api.documents.llm.analyze_image_with_ai",
            new_callable=AsyncMock,
            side_effect=RuntimeError("vision API error"),
        ):
            resp = app_client.post(
                "/api/documents",
                files={"file": ("test.png", io.BytesIO(png_bytes), "image/png")},
            )
        assert resp.status_code == 500

    def test_image_extensions_blocked_without_ai(self, app_client):
        """画像拡張子は受理されること（415 にならない）。"""
        with patch(
            "app.api.documents.llm.analyze_image_with_ai",
            new_callable=AsyncMock,
            return_value="test description",
        ):
            resp = app_client.post(
                "/api/documents",
                files={"file": ("photo.webp", io.BytesIO(b"RIFF....WEBP"), "image/webp")},
            )
        # 415 は返さない（形式は受け付ける）
        assert resp.status_code != 415


class TestDrawioUpload:
    """drawio ファイルのアップロードテスト。"""

    def _make_drawio(self, page_name: str = "Page-1", value: str = "テスト") -> bytes:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram name="{page_name}">
    <mxGraphModel>
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="2" value="{value}" vertex="1" parent="1">
          <mxGeometry x="100" y="100" width="120" height="60" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>""".encode("utf-8")

    def test_upload_drawio_registers_diagram_chunk(self, app_client):
        """drawio ファイルをアップロードすると diagram チャンクが登録される。"""
        resp = app_client.post(
            "/api/documents",
            files={"file": ("infra.drawio", io.BytesIO(self._make_drawio()), "application/xml")},
            data={"wing": "specifications", "room": "infra-diagram"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == "infra.drawio"
        assert body["diagram_chunk_count"] >= 1
        assert body["drawer_count"] >= 1

    def test_upload_dio_extension(self, app_client):
        """.dio 拡張子も受理して diagram チャンクを登録する。"""
        resp = app_client.post(
            "/api/documents",
            files={"file": ("arch.dio", io.BytesIO(self._make_drawio()), "application/xml")},
        )
        assert resp.status_code == 200
        assert resp.json()["diagram_chunk_count"] >= 1

    def test_upload_multipage_drawio(self, app_client):
        """複数ページの drawio は全ページ分チャンクが登録される。"""
        multipage = """<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram name="Page-1">
    <mxGraphModel><root><mxCell id="0"/><mxCell id="1" value="A" vertex="1" parent="0"><mxGeometry as="geometry"/></mxCell></root></mxGraphModel>
  </diagram>
  <diagram name="Page-2">
    <mxGraphModel><root><mxCell id="0"/><mxCell id="1" value="B" vertex="1" parent="0"><mxGeometry as="geometry"/></mxCell></root></mxGraphModel>
  </diagram>
</mxfile>""".encode("utf-8")
        resp = app_client.post(
            "/api/documents",
            files={"file": ("multipage.drawio", io.BytesIO(multipage), "application/xml")},
        )
        assert resp.status_code == 200
        assert resp.json()["diagram_chunk_count"] == 2
