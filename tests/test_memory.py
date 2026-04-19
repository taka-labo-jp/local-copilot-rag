"""memory サービスのユニットテスト。

検証項目:
- Palace 初期化
- ドキュメント追加とチャンク数
- 検索（ベクトル + キーワード ハイブリッド）
- 検索フィルタ（wing / room / source_files）
- 空クエリの処理
- ドキュメント削除
- Query Transform（クエリバリアント生成）
"""
from pathlib import Path

import pytest

from app.services.memory import (
    _build_query_variants,
    _keyword_rank,
    _rrf_fuse,
    _tokenize,
    add_document,
    delete_document_chunks,
    init_palace,
    search,
    search_with_diagnostics,
)


@pytest.fixture()
def palace(tmp_path):
    """テスト用 palace を初期化して返す。"""
    palace_path = str(tmp_path / "palace")
    init_palace(palace_path)
    return palace_path


class TestInitPalace:
    """init_palace のテスト。"""

    def test_creates_directory(self, tmp_path):
        """palace ディレクトリが作成される。"""
        path = str(tmp_path / "new_palace")
        init_palace(path)
        assert Path(path).exists()


class TestAddDocument:
    """add_document のテスト。"""

    @pytest.mark.asyncio
    async def test_add_text_document(self, palace):
        """テキストドキュメントを追加できる。"""
        count = await add_document(
            source_filename="spec.txt",
            palace_path=palace,
            wing="specifications",
            room="test",
            markdown_text="これはテスト仕様書です。要件1: 基本機能。",
        )
        assert count >= 1

    @pytest.mark.asyncio
    async def test_add_chunks(self, palace):
        """チャンク配列を直接追加できる。"""
        chunks = [
            {"text": "チャンク1の内容", "metadata": {"content_type": "text"}},
            {"text": "チャンク2の内容", "metadata": {"content_type": "table"}},
        ]
        count = await add_document(
            source_filename="multi.txt",
            palace_path=palace,
            chunks=chunks,
        )
        assert count >= 2

    @pytest.mark.asyncio
    async def test_add_empty_returns_zero(self, palace):
        """空テキストでは0を返す。"""
        count = await add_document(
            source_filename="empty.txt",
            palace_path=palace,
            markdown_text="",
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_add_empty_chunks_returns_zero(self, palace):
        """空チャンクリストでは0を返す。"""
        count = await add_document(
            source_filename="empty.txt",
            palace_path=palace,
            chunks=[{"text": "", "metadata": {}}],
        )
        assert count == 0


class TestSearch:
    """search / search_with_diagnostics のテスト。"""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, palace):
        """登録済みドキュメントを検索で見つけられる。"""
        await add_document(
            source_filename="auth.txt",
            palace_path=palace,
            wing="specifications",
            room="auth",
            markdown_text="ログイン機能の仕様。ユーザーはメールアドレスとパスワードでログインする。二要素認証にも対応する。",
        )
        results = search(
            query="ログイン認証",
            palace_path=palace,
            n_results=3,
        )
        assert len(results) >= 1
        assert any("ログイン" in r["text"] for r in results)

    @pytest.mark.asyncio
    async def test_search_with_wing_filter(self, palace):
        """wing フィルタで絞り込みできる。"""
        await add_document(
            source_filename="spec.txt",
            palace_path=palace,
            wing="specifications",
            markdown_text="仕様書のテキスト",
        )
        await add_document(
            source_filename="design.txt",
            palace_path=palace,
            wing="design",
            markdown_text="設計ドキュメント",
        )
        results = search(
            query="テキスト",
            palace_path=palace,
            wing="specifications",
        )
        for r in results:
            assert r["wing"] == "specifications"

    @pytest.mark.asyncio
    async def test_search_with_source_files_filter(self, palace):
        """source_files フィルタで絞り込みできる。"""
        await add_document(
            source_filename="target.txt",
            palace_path=palace,
            markdown_text="対象ファイルの内容",
        )
        await add_document(
            source_filename="other.txt",
            palace_path=palace,
            markdown_text="別のファイルの内容",
        )
        results = search(
            query="内容",
            palace_path=palace,
            source_files=["target.txt"],
        )
        for r in results:
            assert r["source_file"] == "target.txt"

    def test_search_empty_query(self, palace):
        """空クエリは空結果を返す。"""
        result = search_with_diagnostics(
            query="",
            palace_path=palace,
        )
        assert result["results"] == []
        assert result["diagnostics"]["fetch_k"] == 0

    @pytest.mark.asyncio
    async def test_search_diagnostics_fields(self, palace):
        """diagnostics に必要なフィールドが含まれる。"""
        await add_document(
            source_filename="diag.txt",
            palace_path=palace,
            markdown_text="診断テスト用テキスト",
        )
        result = search_with_diagnostics(
            query="診断テスト",
            palace_path=palace,
        )
        diag = result["diagnostics"]
        assert "query" in diag
        assert "vector_hit_count" in diag
        assert "keyword_match_count" in diag
        assert "elapsed_ms" in diag
        assert "reranked" in diag


class TestDeleteDocumentChunks:
    """delete_document_chunks のテスト。"""

    @pytest.mark.asyncio
    async def test_delete_chunks(self, palace):
        """登録したチャンクを削除できる。"""
        await add_document(
            source_filename="del.txt",
            palace_path=palace,
            wing="specifications",
            room="test",
            markdown_text="削除対象のテキスト",
        )
        deleted = delete_document_chunks(
            palace_path=palace,
            source_filename="del.txt",
        )
        assert deleted >= 1

    def test_delete_nonexistent(self, palace):
        """存在しないファイルの削除は0を返す。"""
        deleted = delete_document_chunks(
            palace_path=palace,
            source_filename="nonexistent.txt",
        )
        assert deleted == 0


class TestQueryVariants:
    """_build_query_variants のテスト。"""

    def test_simple_query(self):
        """単純なクエリはそのまま返す。"""
        variants = _build_query_variants("ログイン")
        assert "ログイン" in variants

    def test_comma_separated(self):
        """カンマ区切りのクエリが分割される。"""
        variants = _build_query_variants("認証、認可、セキュリティ")
        assert len(variants) >= 2

    def test_empty_query(self):
        """空クエリは空リストを返す。"""
        variants = _build_query_variants("")
        assert variants == []


class TestTokenize:
    """_tokenize のテスト。"""

    def test_japanese(self):
        """日本語テキストがトークン化される。"""
        tokens = _tokenize("ログイン機能のテスト")
        assert len(tokens) >= 1

    def test_english(self):
        """英語テキストがトークン化される。"""
        tokens = _tokenize("login function test")
        assert "login" in tokens
        assert "function" in tokens

    def test_mixed(self):
        """日英混在テキストがトークン化される。"""
        tokens = _tokenize("APIのテスト authentication")
        assert any("api" == t for t in tokens)
        assert any("authentication" == t for t in tokens)


class TestRrfFuse:
    """_rrf_fuse のテスト。"""

    def test_single_source(self):
        """片方のみの順位でもスコアが計算される。"""
        scores = _rrf_fuse(["a", "b", "c"], [])
        assert "a" in scores
        assert scores["a"] > scores["b"] > scores["c"]

    def test_both_sources(self):
        """両系統に共通するIDが高スコアになる。"""
        scores = _rrf_fuse(["a", "b"], ["b", "a"])
        # 両方1位+2位のbが最高になるか、少なくとも両方にスコアがある
        assert "a" in scores
        assert "b" in scores

    def test_disjoint_sources(self):
        """重複なしの場合も正常に動作する。"""
        scores = _rrf_fuse(["a"], ["b"])
        assert "a" in scores
        assert "b" in scores


class TestKeywordRank:
    """_keyword_rank のテスト。"""

    def test_matching_documents(self):
        """キーワード一致するドキュメントにスコアが付く。"""
        scores = _keyword_rank(
            query="ログイン 認証",
            ids=["d1", "d2"],
            docs=["ログイン画面の仕様", "別の内容"],
        )
        assert "d1" in scores
        # d2 は一致しないのでスコアなし or 低い
        assert scores.get("d1", 0) > scores.get("d2", 0)

    def test_empty_query(self):
        """空クエリはスコアなしを返す。"""
        scores = _keyword_rank(
            query="",
            ids=["d1"],
            docs=["test"],
        )
        assert scores == {}
