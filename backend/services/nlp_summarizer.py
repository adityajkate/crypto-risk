"""
Core NLP stack:
- spaCy: sentence segmentation, NER, noun chunks, token filtering
- Sentence-Transformers: semantic embeddings, semantic deduplication, title relevance
- scikit-learn: TF-IDF n-grams, cosine similarity, optional clustering
- NetworkX: TextRank/PageRank over a semantic sentence graph
- MMR: diverse sentence selection so the summary does not repeat the same story

Expected article shape:
{
    "title": str,
    "full_content" | "summary" | "text": str,
    "url": str optional,
    "source": str optional,
    "published_at" | "timestamp" | "date": str/int optional,
    "engagement_count": int optional,
    "sentiment": {"label": "Bullish|Bearish|Neutral", "confidence": 0.0-1.0 or 0-100} optional
}
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import numpy as np

logger = logging.getLogger(__name__)

try:
    import spacy
except ImportError as exc:
    raise ImportError(
        "spaCy is required. Install with: pip install spacy && "
        "python -m spacy download en_core_web_sm"
    ) from exc

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError as exc:
    raise ImportError(
        "scikit-learn is required. Install with: pip install scikit-learn"
    ) from exc

try:
    from sentence_transformers import SentenceTransformer
except ImportError as exc:
    raise ImportError(
        "sentence-transformers is required. Install with: pip install sentence-transformers"
    ) from exc

try:
    import networkx as nx
except ImportError as exc:
    raise ImportError(
        "networkx is required. Install with: pip install networkx"
    ) from exc


@dataclass(slots=True)
class ArticleDoc:
    index: int
    title: str
    body: str
    text: str
    source: str = "unknown"
    url: str = ""
    published_at: Optional[datetime] = None
    engagement: float = 0.0
    sentiment_label: str = "Neutral"
    sentiment_confidence: float = 0.55
    quality: float = 0.5


@dataclass(slots=True)
class SentenceCandidate:
    text: str
    article_index: int
    sentence_index: int
    sentence_count: int
    source: str
    title: str
    published_at: Optional[datetime]
    engagement: float
    article_quality: float
    score: float = 0.0
    score_parts: Dict[str, float] = field(default_factory=dict)


class ProductionNLPSummarizer:
    """
    Higher-quality NLP summarizer designed for FastAPI responses with the original response shape.

    Improvements over the earlier version:
    - fixes quote normalization and text cleaning
    - deduplicates articles before scoring
    - uses all scoring functions in the summary path
    - uses MMR to reduce repetition
    - considers more than only the first two sentences
    - adds source/recency/engagement weighting
    - makes risk, sentiment, and price impact more explainable
    """

    def __init__(
        self,
        spacy_model: str = "en_core_web_sm",
        sentence_model: str = "all-MiniLM-L6-v2",
        max_articles: int = 80,
        max_sentences_per_article: int = 8,
    ) -> None:
        logger.info("Initializing Production NLP Summarizer...")

        try:
            # Parser + NER are useful; keep the full model enabled.
            self.nlp = spacy.load(spacy_model)
        except OSError as exc:
            raise RuntimeError(
                f"spaCy model '{spacy_model}' not found. Run: python -m spacy download {spacy_model}"
            ) from exc

        try:
            self.sentence_model = SentenceTransformer(sentence_model)
        except Exception as exc:
            raise RuntimeError(
                f"Could not load SentenceTransformer model '{sentence_model}': {exc}"
            ) from exc

        self.max_articles = max_articles
        self.max_sentences_per_article = max_sentences_per_article

        self.crypto_terms = {
            "bitcoin",
            "btc",
            "ethereum",
            "eth",
            "crypto",
            "cryptocurrency",
            "blockchain",
            "defi",
            "nft",
            "token",
            "coin",
            "exchange",
            "wallet",
            "mining",
            "staking",
            "protocol",
            "smart contract",
            "dapp",
            "web3",
            "layer",
            "validator",
            "node",
            "hash",
            "block",
            "chain",
            "liquidity",
            "yield",
            "apy",
            "tvl",
            "market cap",
            "stablecoin",
            "etf",
            "dao",
            "dex",
            "cex",
            "airdrop",
            "halving",
            "mainnet",
            "testnet",
        }

        self.boilerplate_patterns = [
            r"strict editorial policy",
            r"focuses on accuracy",
            r"subscribe to (?:our|the) newsletter",
            r"follow us on",
            r"click here to",
            r"terms and conditions",
            r"privacy policy",
            r"not financial advice",
            r"sponsored content",
            r"affiliate disclosure",
            r"all rights reserved",
            r"read more",
            r"share this article",
            r"advertisement",
        ]

        self.risk_patterns: Dict[str, Dict[str, Any]] = {
            "critical": {
                "weight": 1.0,
                "keywords": [
                    "hack",
                    "hacked",
                    "exploit",
                    "vulnerability",
                    "breach",
                    "scam",
                    "fraud",
                    "rug pull",
                    "rugpull",
                    "stolen",
                    "compromised",
                    "attack",
                    "malware",
                    "phishing",
                    "insolvent",
                    "bankrupt",
                    "collapse",
                ],
                "context": [
                    "wallet",
                    "fund",
                    "exchange",
                    "protocol",
                    "bridge",
                    "security",
                    "user",
                ],
            },
            "high": {
                "weight": 0.78,
                "keywords": [
                    "lawsuit",
                    "regulation",
                    "ban",
                    "investigation",
                    "sec",
                    "cftc",
                    "doj",
                    "enforcement",
                    "fine",
                    "penalty",
                    "sanction",
                    "delisting",
                    "suspension",
                    "trading halt",
                    "probe",
                    "settlement",
                ],
                "context": [
                    "regulatory",
                    "legal",
                    "government",
                    "court",
                    "compliance",
                    "authority",
                ],
            },
            "medium": {
                "weight": 0.52,
                "keywords": [
                    "volatility",
                    "uncertain",
                    "warning",
                    "risk",
                    "delay",
                    "issue",
                    "controversy",
                    "dispute",
                    "outflow",
                    "sell-off",
                    "liquidation",
                    "resistance",
                    "support",
                    "correction",
                    "slump",
                ],
                "context": [
                    "market",
                    "price",
                    "trading",
                    "volume",
                    "investor",
                    "token",
                ],
            },
        }

        self.positive_events = {
            "partnership",
            "acquisition",
            "merger",
            "listing",
            "mainnet",
            "upgrade",
            "integration",
            "adoption",
            "institutional",
            "approval",
            "record",
            "milestone",
            "launch",
            "breakthrough",
            "rally",
            "surge",
            "inflow",
            "funding",
        }
        self.negative_events = {
            "hack",
            "exploit",
            "lawsuit",
            "ban",
            "delisting",
            "outflow",
            "sell-off",
            "liquidation",
            "bankruptcy",
            "insolvent",
            "probe",
            "fine",
            "penalty",
            "halt",
            "vulnerability",
            "breach",
        }
        self.bullish_lexicon = {
            "surge",
            "rally",
            "gain",
            "gains",
            "bullish",
            "breakout",
            "approval",
            "adoption",
            "growth",
            "record",
            "inflow",
            "accumulate",
            "accumulation",
            "partnership",
            "launch",
            "upgrade",
            "positive",
            "buy",
            "rebound",
            "recover",
        }
        self.bearish_lexicon = {
            "drop",
            "fall",
            "falls",
            "plunge",
            "slump",
            "bearish",
            "sell-off",
            "outflow",
            "liquidation",
            "hack",
            "lawsuit",
            "ban",
            "fine",
            "penalty",
            "negative",
            "risk",
            "warning",
            "delay",
            "exploit",
            "breach",
            "crash",
        }

        logger.info("Production NLP Summarizer initialized")

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def summarize_articles(
        self,
        articles: List[Dict[str, Any]],
        coin: str,
        max_summary_sentences: int = 4,
        max_summary_chars: int = 650,
    ) -> Dict[str, Any]:
        """Generate frontend-ready JSON from a list of article dictionaries."""
        if not articles:
            raise ValueError(f"No articles provided for {coin}")

        article_docs = self._prepare_articles(articles, coin=coin)
        if not article_docs:
            raise ValueError(f"No usable article text found for {coin}")

        candidates = self._collect_candidates(article_docs, coin=coin)
        if not candidates:
            raise ValueError(f"No usable summary sentences found for {coin}")

        scored_candidates, embeddings, clusters = self._score_candidates(
            candidates, coin=coin
        )
        selected = self._select_summary_sentences(
            scored_candidates,
            embeddings,
            max_sentences=max_summary_sentences,
        )
        summary = self._render_summary(selected, max_chars=max_summary_chars)

        combined_text = " ".join(
            doc.text for doc in article_docs[: min(50, len(article_docs))]
        )
        sentiment = self._aggregate_sentiment(article_docs)
        key_insights = self._extract_key_phrases(
            combined_text, coin=coin, max_phrases=8
        )
        risk_factors, risk_details = self._detect_risks(combined_text, article_docs)
        price_impact, impact_score = self._assess_price_impact(
            combined_text, sentiment, article_docs, risk_details
        )
        reasoning = self._build_reasoning(
            sentiment=sentiment,
            price_impact=price_impact,
            impact_score=impact_score,
            article_count=len(article_docs),
            candidates=len(candidates),
            selected=selected,
        )

        # Keep the original frontend/API contract only. No extra response fields.
        return {
            "summary": summary,
            "sentiment": sentiment["label"],
            "confidence": sentiment["confidence"],
            "key_insights": key_insights,
            "price_impact": price_impact,
            "reasoning": reasoning[:240],
            "risk_factors": risk_factors,
            "used_fallback": False,
            "summary_source": "nlp_production",
            "model_used": "spacy_sbert_tfidf_textrank_mmr_ner",
            "llm_error": None,
        }

    async def summarize_articles_async(
        self,
        articles: List[Dict[str, Any]],
        coin: str,
        max_summary_sentences: int = 4,
        max_summary_chars: int = 650,
    ) -> Dict[str, Any]:
        """Async wrapper for FastAPI endpoints."""
        return await asyncio.to_thread(
            self.summarize_articles,
            articles,
            coin,
            max_summary_sentences,
            max_summary_chars,
        )

    # ---------------------------------------------------------------------
    # Article preparation
    # ---------------------------------------------------------------------

    def _prepare_articles(
        self, articles: List[Dict[str, Any]], coin: str
    ) -> List[ArticleDoc]:
        prepared: List[ArticleDoc] = []

        for idx, article in enumerate(articles[: self.max_articles * 2]):
            title = self._clean_text(str(article.get("title") or ""))
            body = self._article_body(article)
            body = self._clean_text(body)
            if len(body) < 80 and len(title) < 20:
                continue

            source = (
                str(
                    article.get("source") or article.get("publisher") or "unknown"
                ).strip()
                or "unknown"
            )
            url = str(article.get("url") or article.get("link") or "").strip()
            published_at = self._parse_datetime(
                article.get("published_at")
                or article.get("timestamp")
                or article.get("date")
            )
            engagement = self._safe_float(
                article.get("engagement_count") or article.get("engagement") or 0.0
            )
            sent_label, sent_conf = self._article_sentiment(article, f"{title} {body}")

            text = f"{title}. {body}" if title and title not in body[:150] else body
            quality = self._article_quality(
                title=title,
                body=body,
                source=source,
                published_at=published_at,
                engagement=engagement,
            )

            prepared.append(
                ArticleDoc(
                    index=idx,
                    title=title,
                    body=body,
                    text=text,
                    source=source,
                    url=url,
                    published_at=published_at,
                    engagement=engagement,
                    sentiment_label=sent_label,
                    sentiment_confidence=sent_conf,
                    quality=quality,
                )
            )

        deduped = self._deduplicate_articles(prepared)
        deduped.sort(key=self._article_sort_key, reverse=True)
        return deduped[: self.max_articles]

    @staticmethod
    def _article_body(article: Dict[str, Any]) -> str:
        for key in (
            "full_content",
            "content",
            "body",
            "summary",
            "description",
            "text",
        ):
            value = article.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ""

    def _deduplicate_articles(self, docs: List[ArticleDoc]) -> List[ArticleDoc]:
        seen_keys: set[str] = set()
        seen_title_tokens: List[set[str]] = []
        result: List[ArticleDoc] = []

        for doc in docs:
            url_key = self._canonical_url_key(doc.url)
            title_key = (
                self._stable_hash(self._normalize_for_key(doc.title))
                if doc.title
                else ""
            )
            content_key = self._stable_hash(self._normalize_for_key(doc.text[:500]))
            exact_key = url_key or title_key or content_key

            if exact_key and exact_key in seen_keys:
                continue

            title_tokens = self._token_set(doc.title)
            near_duplicate = False
            if title_tokens:
                for old_tokens in seen_title_tokens[-200:]:
                    if self._jaccard(title_tokens, old_tokens) >= 0.88:
                        near_duplicate = True
                        break
            if near_duplicate:
                continue

            if exact_key:
                seen_keys.add(exact_key)
            if title_tokens:
                seen_title_tokens.append(title_tokens)
            result.append(doc)

        return result

    @staticmethod
    def _article_sort_key(doc: ArticleDoc) -> Tuple[float, float, float]:
        timestamp = doc.published_at.timestamp() if doc.published_at else 0.0
        return (doc.quality, timestamp, doc.engagement)

    @staticmethod
    def _canonical_url_key(url: str) -> str:
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower().replace("www.", "")
            path = re.sub(r"/$", "", parsed.path.lower())
            return f"{host}{path}"
        except Exception:
            return ""

    # ---------------------------------------------------------------------
    # Candidate collection and filtering
    # ---------------------------------------------------------------------

    def _collect_candidates(
        self, docs: List[ArticleDoc], coin: str
    ) -> List[SentenceCandidate]:
        candidates: List[SentenceCandidate] = []

        for doc in docs:
            sentences = self._extract_sentences(doc.body or doc.text)
            if not sentences:
                continue

            kept_for_article = 0
            for sent_idx, sentence in enumerate(sentences):
                if kept_for_article >= self.max_sentences_per_article:
                    break
                cleaned = self._clean_sentence(sentence)
                if self._is_bad_sentence(cleaned, coin=coin):
                    continue
                candidates.append(
                    SentenceCandidate(
                        text=cleaned,
                        article_index=doc.index,
                        sentence_index=sent_idx,
                        sentence_count=len(sentences),
                        source=doc.source,
                        title=doc.title,
                        published_at=doc.published_at,
                        engagement=doc.engagement,
                        article_quality=doc.quality,
                    )
                )
                kept_for_article += 1

        # Remove duplicate or near-exact duplicate sentences before expensive scoring.
        unique: List[SentenceCandidate] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = self._stable_hash(self._normalize_for_key(candidate.text))
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    def _extract_sentences(self, text: str) -> List[str]:
        if not text:
            return []
        doc = self.nlp(text[:120_000])
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    def _is_bad_sentence(self, sentence: str, coin: str = "") -> bool:
        if not sentence:
            return True

        lower = sentence.lower()
        words = re.findall(r"[a-zA-Z0-9$%]+", sentence)

        if len(sentence) < 45 or len(sentence) > 420:
            return True
        if len(words) < 7:
            return True
        if lower.endswith("?"):
            return True
        if re.search(
            r"(?:lorem ipsum|consectetur adipiscing|morbi pretium|aliquam mollis)",
            lower,
        ):
            return True
        if any(re.search(pattern, lower) for pattern in self.boilerplate_patterns):
            return True
        if lower.count("|") >= 2 or lower.count("/") >= 6:
            return True
        if self._uppercase_ratio(sentence) > 0.45:
            return True
        if len(set(words)) / max(len(words), 1) < 0.42:
            return True

        # Keep finance/crypto/asset sentences, but don't be too strict.
        coin_lower = coin.lower().strip()
        coin_terms = (
            {coin_lower, coin_lower.replace(" ", ""), coin_lower.upper()}
            if coin_lower
            else set()
        )
        finance_signals = {
            "price",
            "market",
            "trading",
            "investor",
            "fund",
            "shares",
            "stock",
            "exchange",
            "volume",
            "rally",
            "drop",
            "gain",
            "loss",
            "token",
            "coin",
            "blockchain",
            "crypto",
            "etf",
            "rate",
            "yield",
            "liquidity",
            "wallet",
            "protocol",
        }
        if not any(
            term in lower
            for term in self.crypto_terms
            | finance_signals
            | {t for t in coin_terms if t}
        ):
            # This is a soft content quality gate. It removes generic site text.
            return True

        return False

    # ---------------------------------------------------------------------
    # Scoring
    # ---------------------------------------------------------------------

    def _score_candidates(
        self,
        candidates: List[SentenceCandidate],
        coin: str,
    ) -> Tuple[List[SentenceCandidate], np.ndarray, Dict[int, int]]:
        texts = [candidate.text for candidate in candidates]
        embeddings = self._encode(texts)

        textrank_scores = self._textrank_scores(embeddings)
        tfidf_scores = self._tfidf_scores(texts)
        title_scores = self._title_similarity_scores(candidates, embeddings)
        relevance_scores = self._coin_relevance_scores(texts, coin)
        entity_scores = self._entity_number_scores(texts)
        position_scores = self._position_scores(candidates)
        article_scores = self._article_weight_scores(candidates)
        novelty_scores = self._novelty_scores(embeddings)

        for i, candidate in enumerate(candidates):
            parts = {
                "textrank": textrank_scores[i],
                "tfidf": tfidf_scores[i],
                "title_similarity": title_scores[i],
                "coin_relevance": relevance_scores[i],
                "entity_number": entity_scores[i],
                "position": position_scores[i],
                "article_quality": article_scores[i],
                "novelty": novelty_scores[i],
            }
            candidate.score_parts = parts
            candidate.score = float(
                0.27 * parts["textrank"]
                + 0.20 * parts["tfidf"]
                + 0.13 * parts["title_similarity"]
                + 0.12 * parts["position"]
                + 0.10 * parts["entity_number"]
                + 0.08 * parts["coin_relevance"]
                + 0.07 * parts["article_quality"]
                + 0.03 * parts["novelty"]
            )

        clusters = self._cluster_candidates(embeddings, max_clusters=6)
        scored_candidates = list(candidates)
        scored_candidates.sort(key=lambda c: c.score, reverse=True)
        return scored_candidates, embeddings, clusters

    def _encode(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        try:
            embeddings = self.sentence_model.encode(
                list(texts),
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except TypeError:
            embeddings = self.sentence_model.encode(
                list(texts), show_progress_bar=False, convert_to_numpy=True
            )
            embeddings = self._l2_normalize(np.asarray(embeddings))
        return np.asarray(embeddings, dtype=np.float32)

    @staticmethod
    def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(matrix, axis=1, keepdims=True)
        norm[norm == 0] = 1.0
        return matrix / norm

    def _textrank_scores(self, embeddings: np.ndarray) -> List[float]:
        n = len(embeddings)
        if n == 0:
            return []
        if n == 1:
            return [1.0]

        sim = cosine_similarity(embeddings)
        sim = np.maximum(sim, 0.0)
        np.fill_diagonal(sim, 0.0)
        sim[sim < 0.18] = 0.0

        if float(sim.sum()) == 0.0:
            return [1.0] * n

        graph = nx.from_numpy_array(sim)
        try:
            ranks = nx.pagerank(
                graph, alpha=0.85, max_iter=200, tol=1e-7, weight="weight"
            )
            scores = np.array([ranks.get(i, 0.0) for i in range(n)], dtype=np.float32)
        except nx.PowerIterationFailedConvergence:
            scores = sim.mean(axis=1)

        return self._normalize(scores).tolist()

    def _tfidf_scores(self, texts: Sequence[str]) -> List[float]:
        if not texts:
            return []
        if len(texts) == 1:
            return [1.0]

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 3),
            max_features=1_200,
            min_df=1,
            max_df=0.88,
            sublinear_tf=True,
        )
        try:
            matrix = vectorizer.fit_transform(texts)
            # Sum captures informative terms; mean avoids favoring long sentences too much.
            summed = np.asarray(matrix.sum(axis=1)).ravel()
            density = np.asarray((matrix > 0).sum(axis=1)).ravel()
            scores = summed / np.maximum(np.sqrt(density), 1.0)
        except ValueError:
            scores = np.ones(len(texts), dtype=np.float32)
        return self._normalize(scores).tolist()

    def _title_similarity_scores(
        self, candidates: List[SentenceCandidate], embeddings: np.ndarray
    ) -> List[float]:
        titles = [candidate.title or candidate.text for candidate in candidates]
        title_embeddings = self._encode(titles)
        scores = np.sum(embeddings * title_embeddings, axis=1)
        scores = np.clip(scores, 0.0, 1.0)
        return self._normalize(scores).tolist()

    def _coin_relevance_scores(self, texts: Sequence[str], coin: str) -> List[float]:
        coin_lower = coin.lower().strip()
        coin_variants = (
            {coin_lower, coin_lower.replace(" ", ""), coin.upper()}
            if coin_lower
            else set()
        )
        scores = []
        for text in texts:
            lower = text.lower()
            coin_hits = sum(
                1 for term in coin_variants if term and term.lower() in lower
            )
            crypto_hits = sum(1 for term in self.crypto_terms if term in lower)
            market_hits = len(
                re.findall(
                    r"\b(?:price|market|volume|trading|investor|exchange|token|fund|etf)\b",
                    lower,
                )
            )
            score = min(1.0, 0.55 * coin_hits + 0.10 * crypto_hits + 0.07 * market_hits)
            scores.append(score)
        return self._normalize(np.array(scores, dtype=np.float32)).tolist()

    def _entity_number_scores(self, texts: Sequence[str]) -> List[float]:
        scores: List[float] = []
        for doc in self.nlp.pipe(texts, batch_size=32):
            entities = sum(
                1
                for ent in doc.ents
                if ent.label_
                in {
                    "ORG",
                    "PERSON",
                    "GPE",
                    "PRODUCT",
                    "EVENT",
                    "MONEY",
                    "PERCENT",
                    "DATE",
                    "CARDINAL",
                }
            )
            numbers = len(
                re.findall(
                    r"(?:\$\s*)?\d+(?:[,.]\d+)*(?:\.\d+)?\s*(?:%|billion|million|bn|m|k)?",
                    doc.text,
                    flags=re.I,
                )
            )
            quote_or_claim = (
                1
                if re.search(
                    r"\b(?:said|reported|announced|according|filed|approved|launched)\b",
                    doc.text,
                    flags=re.I,
                )
                else 0
            )
            score = min(1.0, 0.15 * entities + 0.18 * numbers + 0.18 * quote_or_claim)
            scores.append(score)
        return self._normalize(np.array(scores, dtype=np.float32)).tolist()

    @staticmethod
    def _position_scores(candidates: List[SentenceCandidate]) -> List[float]:
        scores = []
        for candidate in candidates:
            denominator = max(candidate.sentence_count - 1, 1)
            relative_pos = candidate.sentence_index / denominator
            # News articles usually put the most important info early, but we still keep later details.
            scores.append(float(math.exp(-2.2 * relative_pos)))
        return scores

    def _article_weight_scores(
        self, candidates: List[SentenceCandidate]
    ) -> List[float]:
        engagements = np.array(
            [max(c.engagement, 0.0) for c in candidates], dtype=np.float32
        )
        if engagements.max() > 0:
            engagement_scores = np.log1p(engagements) / np.log1p(
                float(engagements.max())
            )
        else:
            engagement_scores = np.zeros(len(candidates), dtype=np.float32)

        recency_scores = []
        now = datetime.now(timezone.utc)
        for c in candidates:
            if c.published_at:
                age_hours = max((now - c.published_at).total_seconds() / 3600.0, 0.0)
                recency = math.exp(-age_hours / 168.0)  # one-week half-ish decay
            else:
                recency = 0.45
            recency_scores.append(recency)

        quality = np.array([c.article_quality for c in candidates], dtype=np.float32)
        combined = (
            0.45 * quality
            + 0.35 * np.array(recency_scores, dtype=np.float32)
            + 0.20 * engagement_scores
        )
        return self._normalize(combined).tolist()

    def _novelty_scores(self, embeddings: np.ndarray) -> List[float]:
        if len(embeddings) <= 1:
            return [1.0] * len(embeddings)
        sim = cosine_similarity(embeddings)
        np.fill_diagonal(sim, 0.0)
        redundancy = sim.max(axis=1)
        novelty = 1.0 - np.clip(redundancy, 0.0, 1.0)
        return self._normalize(novelty).tolist()

    def _cluster_candidates(
        self, embeddings: np.ndarray, max_clusters: int = 6
    ) -> Dict[int, int]:
        n = len(embeddings)
        if n == 0:
            return {}
        if n == 1:
            return {0: 0}

        cluster_count = min(max(2, int(math.sqrt(n))), max_clusters, n)
        try:
            from sklearn.cluster import AgglomerativeClustering

            try:
                model = AgglomerativeClustering(
                    n_clusters=cluster_count, metric="cosine", linkage="average"
                )
            except TypeError:
                model = AgglomerativeClustering(
                    n_clusters=cluster_count, affinity="cosine", linkage="average"
                )
            labels = model.fit_predict(embeddings)
            return {i: int(label) for i, label in enumerate(labels)}
        except Exception:
            return {i: 0 for i in range(n)}

    # ---------------------------------------------------------------------
    # Summary selection and rendering
    # ---------------------------------------------------------------------

    def _select_summary_sentences(
        self,
        sorted_candidates: List[SentenceCandidate],
        embeddings_in_original_order: np.ndarray,
        max_sentences: int = 4,
    ) -> List[SentenceCandidate]:
        if not sorted_candidates:
            return []

        # Rebuild embeddings for the sorted order because candidates were sorted after scoring.
        sorted_texts = [candidate.text for candidate in sorted_candidates]
        sorted_embeddings = self._encode(sorted_texts)

        selected: List[int] = []
        source_counts: Dict[str, int] = defaultdict(int)
        article_counts: Dict[int, int] = defaultdict(int)
        lambda_relevance = 0.72

        # Always seed with the strongest sentence.
        selected.append(0)
        source_counts[sorted_candidates[0].source] += 1
        article_counts[sorted_candidates[0].article_index] += 1

        while len(selected) < min(max_sentences, len(sorted_candidates)):
            best_idx = None
            best_mmr = -1e9

            for idx, candidate in enumerate(sorted_candidates):
                if idx in selected:
                    continue
                if source_counts[candidate.source] >= 2:
                    continue
                if (
                    article_counts[candidate.article_index] >= 1
                    and len(sorted_candidates) > max_sentences
                ):
                    continue

                similarity_to_selected = max(
                    float(np.dot(sorted_embeddings[idx], sorted_embeddings[sel_idx]))
                    for sel_idx in selected
                )
                if similarity_to_selected > 0.84:
                    continue

                mmr_score = (
                    lambda_relevance * candidate.score
                    - (1.0 - lambda_relevance) * similarity_to_selected
                )
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = idx

            if best_idx is None:
                # Relax constraints if too few sentences were selected.
                remaining = [
                    i for i in range(len(sorted_candidates)) if i not in selected
                ]
                if not remaining:
                    break
                best_idx = max(remaining, key=lambda i: sorted_candidates[i].score)

            selected.append(best_idx)
            source_counts[sorted_candidates[best_idx].source] += 1
            article_counts[sorted_candidates[best_idx].article_index] += 1

        selected_candidates = [sorted_candidates[i] for i in selected]
        # Put the strongest sentence first, then maintain rough news-flow by article and position.
        lead = selected_candidates[0]
        rest = sorted(
            selected_candidates[1:], key=lambda c: (c.article_index, c.sentence_index)
        )
        return [lead] + rest

    def _render_summary(
        self, selected: List[SentenceCandidate], max_chars: int = 650
    ) -> str:
        """
        Render a coherent frontend-ready paragraph.

        The previous version simply joined selected sentences. That can create output like:
        "Sentence A. However, sentence B. Meanwhile, sentence C."
        when the selected sentences came from different articles. This renderer fixes that by:
        - removing dangling transition words
        - deduplicating overlapping selected facts
        - ordering sentences by a stable news flow
        - trimming without cutting mid-word
        """
        parts = []
        for candidate in selected:
            sentence = self._clean_sentence(candidate.text)
            sentence = self._remove_dangling_connector(sentence)
            if sentence:
                parts.append(sentence)

        parts = self._deduplicate_summary_parts(parts)
        parts = sorted(parts, key=self._summary_theme_order)

        summary = " ".join(parts)
        summary = re.sub(r"\s+", " ", summary).strip()

        if len(summary) <= max_chars:
            return summary

        # Prefer dropping the least central trailing sentence before truncating text.
        while len(summary) > max_chars and len(parts) > 1:
            parts.pop()
            summary = " ".join(parts).strip()

        if len(summary) > max_chars:
            summary = summary[: max_chars - 3].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."
        return summary

    def _remove_dangling_connector(self, sentence: str) -> str:
        """Remove connectors that only make sense inside the original article context."""
        if not sentence:
            return ""

        sentence = re.sub(
            r"^(?:however|but|yet|still|meanwhile|additionally|furthermore|moreover|also|instead|nevertheless|therefore|as a result|on the other hand)\s*,?\s+",
            "",
            sentence.strip(),
            flags=re.I,
        )
        sentence = re.sub(r"^and\s+", "", sentence, flags=re.I).strip()

        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
            if sentence[-1] not in ".!?":
                sentence += "."
        return sentence

    def _deduplicate_summary_parts(self, parts: List[str]) -> List[str]:
        """Remove near-duplicate summary sentences after MMR selection."""
        if len(parts) <= 1:
            return parts

        embeddings = self._encode(parts)
        kept: List[int] = []
        for idx, part in enumerate(parts):
            if not kept:
                kept.append(idx)
                continue
            max_sim = max(float(np.dot(embeddings[idx], embeddings[j])) for j in kept)
            # High threshold because different finance sentences often share terms.
            if max_sim < 0.82:
                kept.append(idx)
        return [parts[i] for i in kept]

    def _summary_theme_order(self, sentence: str) -> Tuple[int, int]:
        """
        Stable summary order for market news:
        1. current price / macro setup
        2. on-chain / investor behavior
        3. regulatory / risk items
        4. analyst forecasts / long-term projections
        5. everything else
        """
        lower = sentence.lower()

        current_market = {
            "held near",
            "traded",
            "trading",
            "price",
            "rebound",
            "support",
            "resistance",
            "oil",
            "conflict",
            "macro",
            "inflation",
            "rates",
            "dollar",
            "stocks",
            "market",
            "volume",
        }
        onchain = {
            "shark",
            "whale",
            "wallet",
            "wallets",
            "supply",
            "absorbed",
            "accumulated",
            "acquired",
            "on-chain",
            "holder",
            "holders",
            "miner",
            "exchange reserve",
            "inflow",
            "outflow",
        }
        risk = {
            "hack",
            "exploit",
            "lawsuit",
            "sec",
            "cftc",
            "ban",
            "regulation",
            "investigation",
            "liquidation",
            "sell-off",
            "risk",
            "warning",
        }
        forecast = {
            "trader",
            "analyst",
            "forecast",
            "target",
            "peak",
            "path",
            "projection",
            "predict",
            "prediction",
            "peter brandt",
            "late 2029",
            "2029",
            "2030",
        }

        if any(term in lower for term in current_market):
            return (0, 0)
        if any(term in lower for term in onchain):
            return (1, 0)
        if any(term in lower for term in risk):
            return (2, 0)
        if any(term in lower for term in forecast):
            return (3, 0)
        return (4, 0)

    # ---------------------------------------------------------------------
    # Insights, topics, sentiment, risk, price impact
    # ---------------------------------------------------------------------

    def _extract_key_phrases(
        self, text: str, coin: str, max_phrases: int = 8
    ) -> List[str]:
        if not text:
            return []

        doc = self.nlp(text[:80_000])
        scores: Counter[str] = Counter()

        for ent in doc.ents:
            if ent.label_ in {
                "ORG",
                "PERSON",
                "GPE",
                "PRODUCT",
                "EVENT",
                "MONEY",
                "PERCENT",
                "DATE",
            }:
                phrase = self._normalize_phrase(ent.text)
                if self._valid_phrase(phrase):
                    scores[phrase] += 3

        for chunk in doc.noun_chunks:
            phrase = self._normalize_phrase(chunk.text)
            if self._valid_phrase(phrase):
                scores[phrase] += 1

        for match in re.findall(
            r"\b(?:bitcoin|ethereum|crypto|blockchain|defi|nft|dao|dex|etf|stablecoin)\s+[a-z0-9-]+\b|"
            r"\b[a-z0-9-]+\s+(?:protocol|network|token|coin|exchange|wallet|etf|fund|upgrade|launch|listing|approval)\b",
            text.lower(),
        ):
            phrase = self._normalize_phrase(match)
            if self._valid_phrase(phrase):
                scores[phrase] += 2

        # TF-IDF phrase boost.
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(2, 3),
                max_features=80,
                min_df=1,
                sublinear_tf=True,
            )
            matrix = vectorizer.fit_transform([text])
            feature_scores = np.asarray(matrix.sum(axis=0)).ravel()
            features = vectorizer.get_feature_names_out()
            for feature, score in zip(features, feature_scores):
                phrase = self._normalize_phrase(feature)
                if self._valid_phrase(phrase):
                    scores[phrase] += float(score) * 2
        except ValueError:
            pass

        coin_lower = coin.lower().strip()
        if coin_lower:
            for phrase in list(scores.keys()):
                if coin_lower in phrase.lower():
                    scores[phrase] += 2

        ranked = [phrase for phrase, _ in scores.most_common(30)]
        deduped = self._semantic_dedup_phrases(ranked, max_phrases=max_phrases)
        return [self._display_phrase(phrase) for phrase in deduped]

    def _build_topics(
        self,
        candidates: List[SentenceCandidate],
        clusters: Dict[int, int],
        scored_candidates: List[SentenceCandidate],
        max_topics: int = 5,
    ) -> List[Dict[str, Any]]:
        # Map text to score because scored_candidates is sorted.
        score_by_text = {c.text: c.score for c in scored_candidates}
        grouped: Dict[int, List[SentenceCandidate]] = defaultdict(list)
        for original_idx, cluster_id in clusters.items():
            if 0 <= original_idx < len(candidates):
                grouped[cluster_id].append(candidates[original_idx])

        topics = []
        for cluster_id, group in grouped.items():
            group_sorted = sorted(
                group, key=lambda c: score_by_text.get(c.text, 0), reverse=True
            )
            combined = " ".join(c.text for c in group_sorted[:5])
            phrases = self._extract_key_phrases(combined, coin="", max_phrases=2)
            label = phrases[0] if phrases else self._shorten(group_sorted[0].text, 56)
            topics.append(
                {
                    "topic": label,
                    "sentence_count": len(group),
                    "top_sentence": group_sorted[0].text,
                    "sources": sorted({c.source for c in group_sorted[:5] if c.source}),
                }
            )

        topics.sort(key=lambda t: t["sentence_count"], reverse=True)
        return topics[:max_topics]

    def _aggregate_sentiment(self, docs: List[ArticleDoc]) -> Dict[str, Any]:
        totals = {"Bullish": 0.0, "Bearish": 0.0, "Neutral": 0.0}
        weight_total = 0.0

        for rank, doc in enumerate(docs):
            recency_weight = math.exp(-rank / max(len(docs) * 0.45, 1.0))
            confidence = max(min(doc.sentiment_confidence, 1.0), 0.05)
            weight = confidence * recency_weight * (0.65 + 0.35 * doc.quality)
            label = doc.sentiment_label if doc.sentiment_label in totals else "Neutral"
            totals[label] += weight
            weight_total += weight

        if weight_total <= 0:
            bullish = bearish = neutral = 33.3
        else:
            bullish = 100.0 * totals["Bullish"] / weight_total
            bearish = 100.0 * totals["Bearish"] / weight_total
            neutral = 100.0 * totals["Neutral"] / weight_total

        label = "Neutral"
        confidence = max(bullish, bearish, neutral)
        if bullish >= bearish + 18 and bullish >= neutral - 8:
            label = "Bullish" if bullish >= 58 else "Mixed-Bullish"
            confidence = bullish
        elif bearish >= bullish + 18 and bearish >= neutral - 8:
            label = "Bearish" if bearish >= 58 else "Mixed-Bearish"
            confidence = bearish
        elif max(bullish, bearish) >= neutral + 8:
            label = "Mixed-Bullish" if bullish > bearish else "Mixed-Bearish"
            confidence = max(bullish, bearish)
        else:
            label = "Neutral"
            confidence = neutral

        return {
            "label": label,
            "confidence": int(round(min(max(confidence, 0.0), 100.0))),
            "bullish_pct": round(bullish, 1),
            "bearish_pct": round(bearish, 1),
            "neutral_pct": round(neutral, 1),
        }

    def _detect_risks(
        self, text: str, docs: List[ArticleDoc]
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        lower = text.lower()
        details: Dict[str, Dict[str, Any]] = {}

        for level, config in self.risk_patterns.items():
            for keyword in config["keywords"]:
                pattern = self._keyword_pattern(keyword)
                matches = list(re.finditer(pattern, lower))
                if not matches:
                    continue

                context_hits = 0
                examples: List[str] = []
                for match in matches[:5]:
                    start = max(match.start() - 120, 0)
                    end = min(match.end() + 120, len(lower))
                    window = lower[start:end]
                    if any(ctx in window for ctx in config.get("context", [])):
                        context_hits += 1
                    if len(examples) < 2:
                        examples.append(self._shorten(text[start:end].strip(), 180))

                severity = (
                    len(matches)
                    * float(config["weight"])
                    * (1.35 if context_hits else 1.0)
                )
                name = self._risk_label(level, keyword)
                details[name] = {
                    "risk": name,
                    "level": level,
                    "keyword": keyword,
                    "score": round(severity, 2),
                    "mentions": len(matches),
                    "context_mentions": context_hits,
                    "examples": examples,
                }

        # Sentiment-distribution risk.
        bearish_count = sum(1 for doc in docs if doc.sentiment_label == "Bearish")
        bearish_ratio = bearish_count / max(len(docs), 1)
        if bearish_ratio >= 0.55:
            details["Sentiment: bearish coverage concentration"] = {
                "risk": "Sentiment: bearish coverage concentration",
                "level": "medium" if bearish_ratio < 0.7 else "high",
                "keyword": "bearish sentiment",
                "score": round(bearish_ratio * 4, 2),
                "mentions": bearish_count,
                "context_mentions": bearish_count,
                "examples": [],
            }

        ranked = sorted(details.values(), key=lambda d: d["score"], reverse=True)
        if not ranked:
            return ["No major NLP-detected risks in the current article set"], []

        factors = []
        for item in ranked[:5]:
            if item["level"] == "critical":
                factors.append(
                    f"Critical: {item['keyword'].title()} risk mentioned across coverage"
                )
            elif item["level"] == "high":
                factors.append(
                    f"High: {item['keyword'].title()} / regulatory risk detected"
                )
            else:
                factors.append(
                    f"Medium: {item['keyword'].title()} market risk detected"
                )
        return factors, ranked[:5]

    def _assess_price_impact(
        self,
        text: str,
        sentiment: Dict[str, Any],
        docs: List[ArticleDoc],
        risk_details: List[Dict[str, Any]],
    ) -> Tuple[str, float]:
        lower = text.lower()
        score = 0.0

        # Event-driven impact.
        for event in self.positive_events:
            score += min(lower.count(event), 5) * 0.55
        for event in self.negative_events:
            score += min(lower.count(event), 5) * 0.70

        # Price/volume/numeric context.
        market_numbers = re.findall(
            r"\b(?:price|volume|market cap|open interest|liquidation|inflow|outflow|trading)\b.{0,80}?(?:\$\s*)?\d+(?:[,.]\d+)*(?:\.\d+)?\s*(?:%|billion|million|bn|m|k)?",
            lower,
        )
        score += min(len(market_numbers), 8) * 0.45

        # Sentiment conviction.
        directional = max(
            sentiment.get("bullish_pct", 0), sentiment.get("bearish_pct", 0)
        )
        if directional >= 70:
            score += 2.0
        elif directional >= 58:
            score += 1.1

        # Risk severity.
        score += (
            min(sum(float(item.get("score", 0.0)) for item in risk_details), 8.0) * 0.35
        )

        # Coverage volume and source diversity.
        sources = {doc.source for doc in docs if doc.source}
        if len(docs) >= 40:
            score += 1.3
        elif len(docs) >= 18:
            score += 0.75
        if len(sources) >= 8:
            score += 0.6

        if score >= 8.0:
            return "High", score
        if score >= 4.2:
            return "Medium", score
        if score >= 1.7:
            return "Low", score
        return "None", score

    def _build_reasoning(
        self,
        sentiment: Dict[str, Any],
        price_impact: str,
        impact_score: float,
        article_count: int,
        candidates: int,
        selected: List[SentenceCandidate],
    ) -> str:
        lead_sources = sorted({s.source for s in selected if s.source})[:3]
        sentiment_text = (
            f"Sentiment is {sentiment['label']} with "
            f"{sentiment['bullish_pct']:.0f}% bullish, "
            f"{sentiment['bearish_pct']:.0f}% bearish, "
            f"{sentiment['neutral_pct']:.0f}% neutral weighted coverage"
        )
        impact_text = f"Price impact is {price_impact} from an NLP event score of {impact_score:.1f}"
        coverage_text = f"Analyzed {article_count} deduplicated articles and {candidates} candidate sentences"
        source_text = (
            f"Top summary evidence came from {', '.join(lead_sources)}"
            if lead_sources
            else "Top summary evidence came from the highest-ranked article sentences"
        )
        return f"{sentiment_text}. {impact_text}. {coverage_text}. {source_text}."

    # ---------------------------------------------------------------------
    # Text utilities
    # ---------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = html.unescape(str(text))
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(
            r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", text, flags=re.I
        )
        text = re.sub(
            r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.I
        )
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"https?://(?:www\.)?([^\s/]+)[^\s]*", r"\1", text)
        text = re.sub(r"\S+@\S+", " ", text)
        text = text.translate(
            str.maketrans(
                {
                    "“": '"',
                    "”": '"',
                    "„": '"',
                    "‟": '"',
                    "’": "'",
                    "‘": "'",
                    "‚": "'",
                    "‛": "'",
                    "—": "-",
                    "–": "-",
                    "…": "...",
                }
            )
        )
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"([!?.,;:])\1{2,}", r"\1", text)
        return text.strip()

    def _clean_sentence(self, sentence: str) -> str:
        sentence = self._clean_text(sentence)
        sentence = re.sub(
            r"\s+(?:Investing\.com|Benzinga|Bloomberg|Reuters|CoinDesk|Cointelegraph|Yahoo Finance|Barron's|Fortune|CNBC|MarketWatch|The Block|Decrypt|Bitcoin Magazine|CryptoSlate|NewsBTC|U\.Today|Stocktwits|Coinpedia|CoinGape|BeInCrypto|Cryptonews|FXStreet|AMBCrypto)\s*$",
            "",
            sentence,
            flags=re.I,
        )
        sentence = re.sub(r"\s+-\s+(?:[A-Z][\w.&-]+\s*){1,4}$", "", sentence)
        sentence = sentence.strip(" -|•\t\n")
        if sentence and sentence[-1] not in ".!?":
            sentence += "."
        return sentence

    def _article_quality(
        self,
        title: str,
        body: str,
        source: str,
        published_at: Optional[datetime],
        engagement: float,
    ) -> float:
        length_score = min(len(body) / 2_500.0, 1.0)
        title_score = 1.0 if 20 <= len(title) <= 180 else 0.45
        source_score = 0.65 if source and source != "unknown" else 0.35
        engagement_score = min(math.log1p(max(engagement, 0.0)) / 8.0, 1.0)
        if published_at:
            age_days = max(
                (datetime.now(timezone.utc) - published_at).total_seconds() / 86_400.0,
                0.0,
            )
            recency_score = math.exp(-age_days / 14.0)
        else:
            recency_score = 0.45
        return float(
            0.25 * length_score
            + 0.20 * title_score
            + 0.20 * source_score
            + 0.20 * recency_score
            + 0.15 * engagement_score
        )

    def _article_sentiment(
        self, article: Dict[str, Any], text: str
    ) -> Tuple[str, float]:
        sentiment = article.get("sentiment") or {}
        if isinstance(sentiment, dict) and sentiment.get("label"):
            label = self._normalize_sentiment_label(str(sentiment.get("label")))
            confidence = self._normalize_confidence(sentiment.get("confidence", 0.65))
            return label, confidence

        # Lexical NLP backup when upstream sentiment is missing.
        lower = text.lower()
        bullish_hits = sum(
            1
            for word in self.bullish_lexicon
            if re.search(self._keyword_pattern(word), lower)
        )
        bearish_hits = sum(
            1
            for word in self.bearish_lexicon
            if re.search(self._keyword_pattern(word), lower)
        )
        if bullish_hits > bearish_hits + 1:
            confidence = min(0.55 + 0.06 * (bullish_hits - bearish_hits), 0.86)
            return "Bullish", confidence
        if bearish_hits > bullish_hits + 1:
            confidence = min(0.55 + 0.06 * (bearish_hits - bullish_hits), 0.86)
            return "Bearish", confidence
        return "Neutral", 0.55

    @staticmethod
    def _normalize_sentiment_label(label: str) -> str:
        value = label.strip().lower()
        if value in {
            "bullish",
            "positive",
            "pos",
            "up",
            "mixed-bullish",
            "mixed bullish",
        }:
            return (
                "Bullish"
                if value != "mixed-bullish" and value != "mixed bullish"
                else "Bullish"
            )
        if value in {
            "bearish",
            "negative",
            "neg",
            "down",
            "mixed-bearish",
            "mixed bearish",
        }:
            return (
                "Bearish"
                if value != "mixed-bearish" and value != "mixed bearish"
                else "Bearish"
            )
        return "Neutral"

    @staticmethod
    def _normalize_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.55
        if confidence > 1.0:
            confidence /= 100.0
        return float(min(max(confidence, 0.05), 1.0))

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            # Support seconds or milliseconds.
            timestamp = (
                float(value) / 1000.0 if float(value) > 10_000_000_000 else float(value)
            )
            try:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (OSError, ValueError):
                return None
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            text = text.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(text)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                # Common simple format fallback.
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %b %Y", "%b %d, %Y"):
                    try:
                        return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue
        return None

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _normalize(values: np.ndarray) -> np.ndarray:
        values = np.asarray(values, dtype=np.float32)
        if len(values) == 0:
            return values
        min_value = float(values.min())
        max_value = float(values.max())
        if math.isclose(max_value, min_value):
            return np.ones_like(values, dtype=np.float32)
        return (values - min_value) / (max_value - min_value)

    @staticmethod
    def _uppercase_ratio(text: str) -> float:
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return 0.0
        return sum(1 for c in letters if c.isupper()) / len(letters)

    @staticmethod
    def _normalize_for_key(text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "").lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _stable_hash(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

    @staticmethod
    def _token_set(text: str) -> set[str]:
        stop = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "to",
            "of",
            "in",
            "on",
            "for",
            "with",
            "by",
            "from",
            "as",
            "is",
            "are",
        }
        return {
            tok
            for tok in re.findall(r"[a-z0-9]+", text.lower())
            if tok not in stop and len(tok) > 2
        }

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    @staticmethod
    def _keyword_pattern(keyword: str) -> str:
        escaped = re.escape(keyword.lower())
        escaped = escaped.replace(r"\ ", r"\s+")
        return rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"

    @staticmethod
    def _risk_label(level: str, keyword: str) -> str:
        if level == "critical":
            return f"Critical: {keyword.title()} threat"
        if level == "high" and keyword.lower() in {
            "sec",
            "cftc",
            "doj",
            "regulation",
            "ban",
            "lawsuit",
        }:
            return f"Regulatory: {keyword.upper()} action"
        if level == "high":
            return f"High: {keyword.title()} risk"
        return f"Medium: {keyword.title()} risk"

    @staticmethod
    def _normalize_phrase(phrase: str) -> str:
        phrase = re.sub(r"[^a-zA-Z0-9$%\s.-]", " ", phrase or "")
        phrase = re.sub(r"\s+", " ", phrase).strip().lower()
        phrase = re.sub(r"^(?:the|a|an|this|that|these|those)\s+", "", phrase)
        return phrase

    @staticmethod
    def _valid_phrase(phrase: str) -> bool:
        if not phrase:
            return False
        words = phrase.split()
        if not (1 <= len(words) <= 5):
            return False
        if len(phrase) < 3 or len(phrase) > 64:
            return False
        bad = {
            "market",
            "price",
            "crypto",
            "bitcoin",
            "ethereum",
            "article",
            "week",
            "today",
            "yesterday",
            "right now",
            "read more",
            "source",
        }
        return phrase not in bad

    def _semantic_dedup_phrases(
        self, phrases: List[str], max_phrases: int
    ) -> List[str]:
        if not phrases:
            return []
        phrases = list(dict.fromkeys(phrases))
        if len(phrases) == 1:
            return phrases
        embeddings = self._encode(phrases)
        selected: List[int] = []
        for idx, _phrase in enumerate(phrases):
            if len(selected) >= max_phrases:
                break
            if not selected:
                selected.append(idx)
                continue
            sim = max(float(np.dot(embeddings[idx], embeddings[j])) for j in selected)
            if sim < 0.83:
                selected.append(idx)
        return [phrases[i] for i in selected[:max_phrases]]

    @staticmethod
    def _display_phrase(phrase: str) -> str:
        lowercase = {
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        out = []
        for idx, word in enumerate(phrase.split()):
            if idx > 0 and word in lowercase:
                out.append(word)
            elif word.upper() in {
                "BTC",
                "ETH",
                "ETF",
                "SEC",
                "CFTC",
                "NFT",
                "DAO",
                "DEX",
            }:
                out.append(word.upper())
            else:
                out.append(word[:1].upper() + word[1:])
        return " ".join(out)

    @staticmethod
    def _shorten(text: str, length: int) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        if len(text) <= length:
            return text
        return text[: max(0, length - 3)].rsplit(" ", 1)[0] + "..."


_summarizer_instance: Optional[ProductionNLPSummarizer] = None


def get_summarizer() -> ProductionNLPSummarizer:
    """FastAPI-friendly singleton. Load heavy NLP models only once per worker process."""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = ProductionNLPSummarizer()
    return _summarizer_instance
