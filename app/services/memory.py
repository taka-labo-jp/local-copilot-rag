"""LangChain + ChromaDB ラッパーサービス。

- 仕様書を決定論的にチャンク分割して埋め込み保存
- 検索はベクトル検索 + キーワード検索のハイブリッド
- 2種類の順位を Reciprocal Rank Fusion (RRF) で統合
"""
import logging
import os
import re
import uuid
from datetime import datetime
from time import perf_counter
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)


def _patch_chromadb_collection_model_fields() -> None:
    """chromadbのPydantic 2.11+非推奨アクセスを回避する。

    chromadb 0.6.x の Collection.get_model_fields() は instance.model_fields を参照し、
    Pydantic 2.11+ で大量の deprecation warning を発生させる。
    ここで class.model_fields を優先参照する実装に差し替える。
    """
    try:
        from chromadb.types import Collection

        def _get_model_fields(self):
            cls = type(self)
            fields = getattr(cls, "model_fields", None)
            if fields is not None:
                return fields
            return getattr(self, "__fields__", {})

        Collection.get_model_fields = _get_model_fields
    except Exception:
        logger.debug("chromadb Collection patch skipped", exc_info=True)


_patch_chromadb_collection_model_fields()

_COLLECTION_NAME = "spec_chunks"
_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
_EMBEDDING_LOCAL_FILES_ONLY = os.getenv("EMBEDDING_LOCAL_FILES_ONLY", "true").lower() in {"1", "true", "yes", "on"}
_DEFAULT_CHUNK_SIZE = 800
_DEFAULT_CHUNK_OVERLAP = 120
_DEFAULT_RRF_K = 60

_embeddings: HuggingFaceEmbeddings | None = None
_vector_stores: dict[str, Chroma] = {}


def _get_embeddings() -> HuggingFaceEmbeddings:
    """ローカル埋め込みモデルを遅延初期化して返す。"""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=_EMBEDDING_MODEL,
            model_kwargs={"local_files_only": _EMBEDDING_LOCAL_FILES_ONLY},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def _get_vector_store(palace_path: str) -> Chroma:
    """指定ディレクトリの永続Chromaコレクションを返す。"""
    root = Path(palace_path)
    root.mkdir(parents=True, exist_ok=True)
    key = str(root.resolve())

    if key not in _vector_stores:
        _vector_stores[key] = Chroma(
            collection_name=_COLLECTION_NAME,
            embedding_function=_get_embeddings(),
            persist_directory=key,
            client_settings=ChromaSettings(
                anonymized_telemetry=False,
                chroma_product_telemetry_impl="app.services.chroma_telemetry.NoOpProductTelemetry",
            ),
        )
    return _vector_stores[key]


def init_palace(palace_path: str) -> None:
    """永続ストアを初期化する。"""
    _get_vector_store(palace_path)
    logger.info("Chroma initialized at %s", palace_path)


def _build_splitter() -> RecursiveCharacterTextSplitter:
    """取り込み時に使う決定論的チャンク分割器を返す。"""
    return RecursiveCharacterTextSplitter(
        chunk_size=_DEFAULT_CHUNK_SIZE,
        chunk_overlap=_DEFAULT_CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "、", " ", ""],
    )


async def add_document(
    source_filename: str,
    palace_path: str,
    wing: str = "specifications",
    room: str | None = None,
    markdown_text: str | None = None,
    chunks: list[dict[str, Any]] | None = None,
) -> int:
    """ドキュメントをチャンク化して Chroma に登録し、登録チャンク数を返す。"""
    room_name = room or Path(source_filename).stem
    splitter = _build_splitter()

    normalized_inputs: list[dict[str, Any]] = []
    if chunks:
        for item in chunks:
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            normalized_inputs.append({"text": text, "metadata": metadata})
    elif markdown_text:
        text = markdown_text.strip()
        if text:
            normalized_inputs.append(
                {
                    "text": text,
                    "metadata": {
                        "content_type": "text",
                        "extractor": "markitdown",
                    },
                }
            )

    if not normalized_inputs:
        return 0

    now = datetime.now().isoformat()
    doc_type = Path(source_filename).suffix.lower().lstrip(".") or "md"
    documents: list[Document] = []
    ids: list[str] = []

    chunk_index = 0
    for src_index, item in enumerate(normalized_inputs):
        sub_chunks = [c.strip() for c in splitter.split_text(item["text"]) if c.strip()]
        base_meta = item["metadata"]

        for sub_index, chunk_text in enumerate(sub_chunks):
            chunk_id = f"{wing}:{room_name}:{uuid.uuid4().hex}:{chunk_index}"
            metadata = {
                "source_file": source_filename,
                "wing": wing,
                "room": room_name,
                "doc_type": doc_type,
                "page": "",
                "section": "",
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "source_chunk_index": src_index,
                "source_chunk_part": sub_index,
                "created_at": now,
            }
            metadata.update(base_meta)

            documents.append(
                Document(
                    page_content=chunk_text,
                    metadata=metadata,
                )
            )
            ids.append(chunk_id)
            chunk_index += 1

    vector_store = _get_vector_store(palace_path)
    vector_store.add_documents(documents=documents, ids=ids)
    logger.info("Added %d chunks for %s", len(ids), source_filename)
    return len(ids)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-z_\-]+|[一-龥ぁ-んァ-ヶー]+", text.lower())


def _keyword_rank(
    query: str,
    ids: list[str],
    docs: list[str],
) -> dict[str, float]:
    """単純なキーワード一致スコアを算出して返す。"""
    terms = [t for t in _tokenize(query) if len(t) >= 2]
    if not terms:
        return {}

    scores: dict[str, float] = {}
    uniq_terms = list(dict.fromkeys(terms))

    for doc_id, text in zip(ids, docs):
        low = text.lower()
        # 複雑化を避けるため、出現回数ベースの軽量スコアを採用する。
        hit = sum(low.count(term) for term in uniq_terms)
        if hit > 0:
            scores[doc_id] = hit / max(1, len(uniq_terms))

    return scores


def _rrf_fuse(
    vector_order: list[str],
    keyword_order: list[str],
    rrf_k: int = _DEFAULT_RRF_K,
) -> dict[str, float]:
    """2系統の順位をRRFで統合する。"""
    fused: dict[str, float] = {}

    for rank, doc_id in enumerate(vector_order, start=1):
        fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)

    for rank, doc_id in enumerate(keyword_order, start=1):
        fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)

    return fused


def _build_query_variants(query: str) -> list[str]:
    """問い合わせを軽量に展開し、複数検索用のバリアントを返す。"""
    base = query.strip()
    if not base:
        return []

    variants = [base]
    normalized = re.sub(r"\s+", " ", base)
    if normalized != base:
        variants.append(normalized)

    # 日本語の読点・スラッシュ・箇条書き区切りをサブクエリとして追加
    split_tokens = re.split(r"[、,／/・]|\s{2,}", normalized)
    split_tokens = [s.strip() for s in split_tokens if len(s.strip()) >= 2]
    for token in split_tokens[:3]:
        if token not in variants:
            variants.append(token)

    # 先頭バリアントを優先しつつ重複排除
    return list(dict.fromkeys(variants))


def _rerank_candidates(
    query: str,
    ranked_ids: list[str],
    by_id: dict[str, dict],
    fused_scores: dict[str, float],
) -> list[str]:
    """軽量な語彙一致ボーナスを使って候補を再ランキングする。"""
    terms = [t for t in _tokenize(query) if len(t) >= 2]
    uniq_terms = list(dict.fromkeys(terms))

    rescored: list[tuple[str, float]] = []
    for doc_id in ranked_ids:
        item = by_id.get(doc_id)
        if not item:
            continue

        text = str(item.get("text", "")).lower()
        if not uniq_terms:
            lexical = 0.0
        else:
            hit = sum(1 for term in uniq_terms if term in text)
            lexical = hit / len(uniq_terms)

        score = fused_scores.get(doc_id, 0.0) + (0.15 * lexical)
        rescored.append((doc_id, score))

    return [doc_id for doc_id, _ in sorted(rescored, key=lambda x: x[1], reverse=True)]


def _to_result_item(item: dict, keyword_scores: dict[str, float], fused_scores: dict[str, float], doc_id: str) -> dict:
    """内部データをAPI返却用フォーマットへ整形する。"""
    meta = item["meta"]
    distance = item["distance"]
    keyword_score = keyword_scores.get(doc_id, 0.0)

    if distance is None:
        similarity = keyword_score
    else:
        similarity = 1.0 / (1.0 + max(0.0, distance))

    return {
        "text": item["text"],
        "wing": meta.get("wing", ""),
        "room": meta.get("room", ""),
        "source_file": meta.get("source_file", "?"),
        "content_type": meta.get("content_type", "text"),
        "similarity": similarity,
        "chunk_id": doc_id,
        "hybrid_score": fused_scores.get(doc_id, 0.0),
    }


def search_with_diagnostics(
    query: str,
    palace_path: str,
    wing: str | None = None,
    room: str | None = None,
    content_type: str | None = None,
    source_files: list[str] | None = None,
    n_results: int = 5,
) -> dict[str, Any]:
    """ハイブリッド検索の結果と診断情報を返す。"""
    start = perf_counter()

    if not query.strip():
        return {
            "results": [],
            "diagnostics": {
                "query": query,
                "fetch_k": 0,
                "vector_hit_count": 0,
                "corpus_doc_count": 0,
                "keyword_match_count": 0,
                "fused_candidate_count": 0,
                "elapsed_ms": 0,
            },
        }

    vector_store = _get_vector_store(palace_path)
    clauses: list[dict[str, Any]] = []
    if wing:
        clauses.append({"wing": wing})
    if room:
        clauses.append({"room": room})
    if content_type:
        clauses.append({"content_type": content_type})
    if source_files:
        normalized_files = [f.strip() for f in source_files if str(f).strip()]
        if len(normalized_files) == 1:
            clauses.append({"source_file": normalized_files[0]})
        elif normalized_files:
            clauses.append({"source_file": {"$in": normalized_files}})

    filter_obj: dict | None
    if not clauses:
        filter_obj = None
    elif len(clauses) == 1:
        filter_obj = clauses[0]
    else:
        filter_obj = {"$and": clauses}

    where = filter_obj if filter_obj else None
    raw = vector_store.get(where=where, include=["documents", "metadatas"])
    all_ids = raw.get("ids", [])
    all_docs = raw.get("documents", [])
    all_metas = raw.get("metadatas", [])

    query_variants = _build_query_variants(query)
    requested_k = max(12, n_results * 4)
    corpus_count = len(all_ids)
    if corpus_count == 0:
        elapsed_ms = int((perf_counter() - start) * 1000)
        diagnostics = {
            "query": query,
            "query_variants": query_variants,
            "source_files": source_files or [],
            "fetch_k": 0,
            "requested_fetch_k": requested_k,
            "vector_hit_count": 0,
            "corpus_doc_count": 0,
            "keyword_match_count": 0,
            "fused_candidate_count": 0,
            "reranked": True,
            "elapsed_ms": elapsed_ms,
        }
        return {"results": [], "diagnostics": diagnostics}

    fetch_k = min(requested_k, corpus_count)

    vector_hits: list[tuple[Document, float]] = []
    for qv in query_variants:
        variant_hits = vector_store.similarity_search_with_score(
            query=qv,
            k=fetch_k,
            filter=filter_obj,
        )
        vector_hits.extend(variant_hits)

    keyword_scores: dict[str, float] = {}
    for qv in query_variants:
        partial = _keyword_rank(query=qv, ids=all_ids, docs=all_docs)
        for k, v in partial.items():
            keyword_scores[k] = max(keyword_scores.get(k, 0.0), v)
    keyword_order = [k for k, _ in sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)]

    vector_order: list[str] = []
    by_id: dict[str, dict] = {}

    for rank, (doc, distance) in enumerate(vector_hits, start=1):
        meta = doc.metadata or {}
        doc_id = str(meta.get("chunk_id") or f"vec:{rank}:{hash(doc.page_content)}")
        vector_order.append(doc_id)
        by_id[doc_id] = {
            "text": doc.page_content,
            "meta": meta,
            "distance": float(distance),
        }

    for doc_id, text, meta in zip(all_ids, all_docs, all_metas):
        if doc_id not in by_id:
            by_id[doc_id] = {
                "text": text,
                "meta": meta or {},
                "distance": None,
            }

    fused_scores = _rrf_fuse(vector_order=vector_order, keyword_order=keyword_order)
    ranked_ids = [k for k, _ in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)]
    reranked_ids = _rerank_candidates(
        query=query,
        ranked_ids=ranked_ids,
        by_id=by_id,
        fused_scores=fused_scores,
    )

    results: list[dict] = []
    for doc_id in reranked_ids[:n_results]:
        item = by_id.get(doc_id)
        if not item:
            continue
        results.append(_to_result_item(item=item, keyword_scores=keyword_scores, fused_scores=fused_scores, doc_id=doc_id))

    elapsed_ms = int((perf_counter() - start) * 1000)
    diagnostics = {
        "query": query,
        "query_variants": query_variants,
        "source_files": source_files or [],
        "fetch_k": fetch_k,
        "requested_fetch_k": requested_k,
        "vector_hit_count": len(vector_hits),
        "corpus_doc_count": len(all_ids),
        "keyword_match_count": len(keyword_scores),
        "fused_candidate_count": len(ranked_ids),
        "reranked": True,
        "elapsed_ms": elapsed_ms,
    }
    return {"results": results, "diagnostics": diagnostics}


def search(
    query: str,
    palace_path: str,
    wing: str | None = None,
    room: str | None = None,
    content_type: str | None = None,
    source_files: list[str] | None = None,
    n_results: int = 5,
) -> list[dict]:
    """ハイブリッド検索結果を返す。"""
    return search_with_diagnostics(
        query=query,
        palace_path=palace_path,
        wing=wing,
        room=room,
        content_type=content_type,
        source_files=source_files,
        n_results=n_results,
    )["results"]


def delete_document_chunks(
    palace_path: str,
    source_filename: str,
    wing: str | None = None,
    room: str | None = None,
) -> int:
    """ファイルに対応するチャンクをChromaから削除する。"""
    vector_store = _get_vector_store(palace_path)
    clauses: list[dict[str, str]] = [{"source_file": source_filename}]
    if wing:
        clauses.append({"wing": wing})
    if room:
        clauses.append({"room": room})

    where: dict
    if len(clauses) == 1:
        where = clauses[0]
    else:
        where = {"$and": clauses}

    current = vector_store.get(where=where, include=[])
    ids = current.get("ids", [])
    if ids:
        vector_store.delete(ids=ids)

    return len(ids)
