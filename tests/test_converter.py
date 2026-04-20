"""converter サービスのユニットテスト。

検証項目:
- テキスト/Markdown ファイルの変換
- convert_to_chunks の出力形式
- XLSX テーブルチャンク化
- 空ファイル・不正バイナリの挙動
- 抽出画像ディレクトリの削除
"""
import io
from pathlib import Path

import pytest

from app.services.converter import (
    convert_to_chunks,
    convert_to_markdown,
    delete_extracted_images,
)


class TestConvertToMarkdown:
    """convert_to_markdown のテスト。"""

    def test_txt_conversion(self):
        """テキストファイルをそのまま返す。"""
        content = "テスト内容です"
        result = convert_to_markdown(content.encode("utf-8"), "test.txt")
        assert "テスト内容" in result

    def test_md_conversion(self):
        """Markdownファイルをそのまま返す。"""
        content = "# 見出し\n\n本文です"
        result = convert_to_markdown(content.encode("utf-8"), "doc.md")
        assert "見出し" in result

    def test_html_conversion(self):
        """HTMLファイルからテキストを抽出する。"""
        html = "<html><body><h1>Title</h1><p>Body text</p></body></html>"
        result = convert_to_markdown(html.encode("utf-8"), "page.html")
        assert "Title" in result
        assert "Body" in result

    def test_csv_conversion(self):
        """CSVファイルを変換する。"""
        csv = "name,age\nAlice,30\nBob,25"
        result = convert_to_markdown(csv.encode("utf-8"), "data.csv")
        assert "Alice" in result


class TestConvertToChunks:
    """convert_to_chunks のテスト。"""

    def test_txt_chunks_structure(self, tmp_path):
        """テキストファイルのチャンクが正しい構造を持つ。"""
        content = "仕様書の本文です。要件1: テスト機能。要件2: バリデーション。"
        chunks = convert_to_chunks(
            file_bytes=content.encode("utf-8"),
            filename="spec.txt",
            image_root_dir=str(tmp_path),
            enable_visual_page_ocr=False,
        )
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "text" in chunk
            assert "metadata" in chunk
            assert isinstance(chunk["metadata"], dict)

    def test_txt_chunks_content_type(self, tmp_path):
        """テキストチャンクの content_type が 'text' である。"""
        chunks = convert_to_chunks(
            file_bytes=b"hello world",
            filename="test.txt",
            image_root_dir=str(tmp_path),
            enable_visual_page_ocr=False,
        )
        text_chunks = [c for c in chunks if c["metadata"].get("content_type") == "text"]
        assert len(text_chunks) >= 1

    def test_md_chunks(self, tmp_path):
        """Markdownチャンクが生成される。"""
        md = "# Header\n\nParagraph content."
        chunks = convert_to_chunks(
            file_bytes=md.encode("utf-8"),
            filename="readme.md",
            image_root_dir=str(tmp_path),
            enable_visual_page_ocr=False,
        )
        assert len(chunks) >= 1

    def test_html_chunks(self, tmp_path):
        """HTMLファイルからチャンクが生成される。"""
        html = "<html><body><p>Test paragraph</p></body></html>"
        chunks = convert_to_chunks(
            file_bytes=html.encode("utf-8"),
            filename="page.html",
            image_root_dir=str(tmp_path),
            enable_visual_page_ocr=False,
        )
        assert len(chunks) >= 1

    def test_json_chunks(self, tmp_path):
        """JSONファイルからチャンクが生成される。"""
        import json
        data = {"key": "value", "items": [1, 2, 3]}
        chunks = convert_to_chunks(
            file_bytes=json.dumps(data).encode("utf-8"),
            filename="data.json",
            image_root_dir=str(tmp_path),
            enable_visual_page_ocr=False,
        )
        assert len(chunks) >= 1


class TestDeleteExtractedImages:
    """delete_extracted_images のテスト。"""

    def test_delete_existing_dir(self, tmp_path):
        """存在するディレクトリを削除できる。"""
        # ダミーの抽出画像ディレクトリを作成
        from app.services.converter import _source_root_dir
        target = _source_root_dir(str(tmp_path), "test.xlsx")
        target.mkdir(parents=True)
        (target / "image.png").write_bytes(b"PNG")
        assert target.exists()

        delete_extracted_images(str(tmp_path), "test.xlsx")
        assert not target.exists()

    def test_delete_nonexistent_dir(self, tmp_path):
        """存在しないディレクトリの削除はエラーにならない。"""
        delete_extracted_images(str(tmp_path), "nonexistent.xlsx")
        # 例外が発生しないことを確認


class TestXlsxConversion:
    """XLSX 変換のテスト。"""

    def test_xlsx_table_chunks(self, tmp_path):
        """XLSXファイルからテーブルチャンクが生成される。"""
        # openpyxl で最小限のXLSXを生成
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["名前", "年齢", "部署"])
        ws.append(["田中", "30", "開発"])
        ws.append(["佐藤", "25", "営業"])

        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()
        wb.close()

        chunks = convert_to_chunks(
            file_bytes=xlsx_bytes,
            filename="staff.xlsx",
            image_root_dir=str(tmp_path),
            excel_rows_per_chunk=5,
            enable_visual_page_ocr=False,
        )
        table_chunks = [c for c in chunks if c["metadata"].get("content_type") == "table"]
        assert len(table_chunks) >= 1
        # テーブルチャンクに列名が含まれる
        assert "名前" in table_chunks[0]["text"]

    def test_xlsx_rows_per_chunk(self, tmp_path):
        """excel_rows_per_chunk 設定でチャンクが分割される。"""
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["col1", "col2"])
        for i in range(20):
            ws.append([f"val{i}", f"data{i}"])

        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()
        wb.close()

        chunks = convert_to_chunks(
            file_bytes=xlsx_bytes,
            filename="big.xlsx",
            image_root_dir=str(tmp_path),
            excel_rows_per_chunk=5,
            enable_visual_page_ocr=False,
        )
        table_chunks = [c for c in chunks if c["metadata"].get("content_type") == "table"]
        # 20行 / 5行 = 4チャンク
        assert len(table_chunks) >= 4


class TestDrawioConversion:
    """drawio ファイル変換のテスト。"""

    def test_inline_xml_single_page(self):
        """インラインXMLの単一ページdrawioを変換できる。"""
        from app.services.converter import convert_drawio_to_chunks

        drawio_xml = """<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram name="インフラ構成" id="page1">
    <mxGraphModel>
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="2" value="Webサーバー" style="rounded=1;" vertex="1" parent="1">
          <mxGeometry x="100" y="100" width="120" height="60" as="geometry" />
        </mxCell>
        <mxCell id="3" value="DBサーバー" style="rounded=1;" vertex="1" parent="1">
          <mxGeometry x="300" y="100" width="120" height="60" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""
        chunks = convert_drawio_to_chunks(
            file_bytes=drawio_xml.encode("utf-8"),
            source_filename="infra.drawio",
        )
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk["metadata"]["content_type"] == "diagram"
        assert chunk["metadata"]["extractor"] == "drawio-xml"
        assert chunk["metadata"]["page_name"] == "インフラ構成"
        assert chunk["metadata"]["page_index"] == 1
        assert "File: infra.drawio" in chunk["text"]
        assert "Format: drawio/mxGraph XML" in chunk["text"]
        assert "mxGraphModel" in chunk["text"]

    def test_multi_page_drawio(self):
        """複数ページのdrawioが各ページ1チャンクに変換される。"""
        from app.services.converter import convert_drawio_to_chunks

        drawio_xml = """<mxfile>
  <diagram name="Page-1">
    <mxGraphModel><root><mxCell id="0"/><mxCell id="1" value="A" parent="0"/></root></mxGraphModel>
  </diagram>
  <diagram name="Page-2">
    <mxGraphModel><root><mxCell id="0"/><mxCell id="1" value="B" parent="0"/></root></mxGraphModel>
  </diagram>
  <diagram name="Page-3">
    <mxGraphModel><root><mxCell id="0"/><mxCell id="1" value="C" parent="0"/></root></mxGraphModel>
  </diagram>
</mxfile>"""
        chunks = convert_drawio_to_chunks(
            file_bytes=drawio_xml.encode("utf-8"),
            source_filename="multi.drawio",
        )
        assert len(chunks) == 3
        assert chunks[0]["metadata"]["page_name"] == "Page-1"
        assert chunks[1]["metadata"]["page_name"] == "Page-2"
        assert chunks[2]["metadata"]["page_name"] == "Page-3"
        assert chunks[0]["metadata"]["page_index"] == 1
        assert chunks[2]["metadata"]["page_index"] == 3

    def test_compressed_page_content(self):
        """base64+rawDEFLATE圧縮コンテンツのdrawioを変換できる。"""
        import base64
        import zlib
        from app.services.converter import convert_drawio_to_chunks

        inner_xml = "<mxGraphModel><root><mxCell id=\"0\"/><mxCell id=\"1\" value=\"圧縮テスト\" parent=\"0\"/></root></mxGraphModel>"

        # rawDeflate圧縮 (wbits=-15)
        compress_obj = zlib.compressobj(wbits=-15)
        raw_deflate = compress_obj.compress(inner_xml.encode("utf-8")) + compress_obj.flush()
        b64content = base64.b64encode(raw_deflate).decode("utf-8")

        drawio_xml = f"""<mxfile>
  <diagram name="CompressedPage">{b64content}</diagram>
</mxfile>"""
        chunks = convert_drawio_to_chunks(
            file_bytes=drawio_xml.encode("utf-8"),
            source_filename="compressed.drawio",
        )
        assert len(chunks) == 1
        assert "mxGraphModel" in chunks[0]["text"]
        assert chunks[0]["metadata"]["page_name"] == "CompressedPage"

    def test_invalid_xml_returns_empty(self):
        """不正なXMLは空リストを返す。"""
        from app.services.converter import convert_drawio_to_chunks

        chunks = convert_drawio_to_chunks(
            file_bytes=b"this is not xml <<<",
            source_filename="bad.drawio",
        )
        assert chunks == []

    def test_dio_extension(self):
        """.dio 拡張子も変換できる。"""
        from app.services.converter import convert_drawio_to_chunks, DRAWIO_EXTENSIONS

        assert ".dio" in DRAWIO_EXTENSIONS

        drawio_xml = """<mxfile>
  <diagram name="Test">
    <mxGraphModel><root><mxCell id="0"/></root></mxGraphModel>
  </diagram>
</mxfile>"""
        chunks = convert_drawio_to_chunks(
            file_bytes=drawio_xml.encode("utf-8"),
            source_filename="arch.dio",
        )
        assert len(chunks) == 1
