"""
RAG retriever — semantic search over indexed ICD-10, CPT, HCPCS code databases.
Returns ranked candidates for a given clinical query.
All ChromaDB and SentenceTransformer calls are wrapped in run_sync() to avoid
blocking the asyncio event loop under concurrent load.
"""
import logging
from functools import partial
from typing import Dict, List, Optional

from app.config import get_settings
from app.models.schemas import CodeType, MedicalCode
from app.rag.indexer import get_chroma_client, get_embedding_model
from app.utils.async_utils import run_sync

logger = logging.getLogger(__name__)
settings = get_settings()


def _embed_texts_sync(texts: List[str]) -> List[List[float]]:
    """Synchronous embedding — called via run_sync from async context."""
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False).tolist()


def _chroma_query_sync(collection, query_embedding, n_results, where_filter):
    """Synchronous ChromaDB query — called via run_sync from async context."""
    kwargs = dict(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    if where_filter:
        kwargs["where"] = where_filter
    return collection.query(**kwargs)


def _chroma_get_sync(collection, where_filter):
    """Synchronous ChromaDB get — called via run_sync from async context."""
    return collection.get(
        where=where_filter,
        include=["metadatas", "documents"],
    )


class CodeRetriever:
    """Semantic code retrieval from the vector knowledge base."""

    async def search_icd10(
        self,
        query: str,
        top_k: int = None,
        category_filter: Optional[str] = None,
    ) -> List[Dict]:
        return await self._search(
            collection_name=settings.chroma_collection_icd10,
            query=query,
            top_k=top_k or settings.rag_top_k,
            code_type="ICD-10-CM",
            category_filter=category_filter,
        )

    async def search_cpt(
        self,
        query: str,
        top_k: int = None,
    ) -> List[Dict]:
        return await self._search(
            collection_name=settings.chroma_collection_cpt,
            query=query,
            top_k=top_k or settings.rag_top_k,
            code_type="CPT",
        )

    async def search_hcpcs(
        self,
        query: str,
        top_k: int = None,
    ) -> List[Dict]:
        return await self._search(
            collection_name=settings.chroma_collection_hcpcs,
            query=query,
            top_k=top_k or settings.rag_top_k,
            code_type="HCPCS",
        )

    async def search_all(
        self,
        query: str,
        include_icd10: bool = True,
        include_cpt: bool = True,
        include_hcpcs: bool = False,
        top_k: int = None,
    ) -> Dict[str, List[Dict]]:
        results = {}
        k = top_k or settings.rag_top_k
        if include_icd10:
            results["icd10"] = await self.search_icd10(query, k)
        if include_cpt:
            results["cpt"] = await self.search_cpt(query, k)
        if include_hcpcs:
            results["hcpcs"] = await self.search_hcpcs(query, k)
        return results

    async def lookup_code(self, code: str, code_type: str) -> Optional[Dict]:
        """Look up a specific code by its code string."""
        collection_map = {
            "ICD-10-CM": settings.chroma_collection_icd10,
            "ICD-10-PCS": settings.chroma_collection_icd10,
            "CPT": settings.chroma_collection_cpt,
            "HCPCS": settings.chroma_collection_hcpcs,
        }
        collection_name = collection_map.get(code_type)
        if not collection_name:
            return None

        # Build list of formats to try: standard (I21.9) and CMS no-period (I219)
        candidates_to_try = [code]
        if "." in code:
            candidates_to_try.append(code.replace(".", ""))
        elif len(code) > 3 and code[0].isalpha() and code[1].isdigit():
            candidates_to_try.append(code[:3] + "." + code[3:])

        client = get_chroma_client()
        for lookup_code in candidates_to_try:
            try:
                collection = client.get_collection(collection_name)
                results = await run_sync(
                    _chroma_get_sync,
                    collection,
                    {"code": lookup_code},
                )
                if results["metadatas"]:
                    return results["metadatas"][0]
            except Exception as e:
                logger.debug(f"Code lookup failed for {lookup_code}: {e}")
        return None

    async def _search(
        self,
        collection_name: str,
        query: str,
        top_k: int,
        code_type: str,
        category_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Core vector search method — async-safe."""
        client = get_chroma_client()
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
            if count == 0:
                logger.debug(f"Collection {collection_name} is empty")
                return []
        except Exception:
            logger.debug(f"Collection {collection_name} not found")
            return []

        # Embed query in thread pool
        embeddings = await run_sync(_embed_texts_sync, [query])
        query_embedding = embeddings[0]

        where_filter = None
        if category_filter:
            where_filter = {"category": category_filter}

        results = await run_sync(
            _chroma_query_sync,
            collection,
            query_embedding,
            min(top_k, count),
            where_filter,
        )

        candidates = []
        if not results["metadatas"] or not results["metadatas"][0]:
            return candidates

        for meta, doc, dist in zip(
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
        ):
            # Convert cosine distance to similarity score (0-1)
            similarity = max(0.0, 1.0 - dist)
            if similarity < settings.rag_similarity_threshold:
                continue
            candidates.append({
                "code": meta.get("code", ""),
                "code_type": meta.get("code_type", code_type),
                "description": meta.get("description", ""),
                "long_description": meta.get("long_description", meta.get("description", "")),
                "category": meta.get("category", ""),
                "chapter": meta.get("chapter", ""),
                "similarity": round(similarity, 4),
                "document": doc,
            })

        return sorted(candidates, key=lambda x: x["similarity"], reverse=True)


# Module-level singleton
_retriever: Optional[CodeRetriever] = None


def get_retriever() -> CodeRetriever:
    global _retriever
    if _retriever is None:
        _retriever = CodeRetriever()
    return _retriever
