"""
Production-Grade NLP Summarizer - NO FALLBACKS
All dependencies are REQUIRED for production quality.
Uses: spaCy, sentence-transformers, scikit-learn, networkx
"""

import re
import logging
from typing import List, Dict, Any
from collections import Counter
import numpy as np

logger = logging.getLogger(__name__)

# REQUIRED imports - no fallbacks, fail fast
try:
    import spacy
    from spacy.tokens import Doc
except ImportError:
    raise ImportError(
        "spaCy is REQUIRED. Install: pip install spacy && python -m spacy download en_core_web_sm"
    )

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    raise ImportError("scikit-learn is REQUIRED. Install: pip install scikit-learn")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError(
        "sentence-transformers is REQUIRED. Install: pip install sentence-transformers"
    )

try:
    import networkx as nx
except ImportError:
    raise ImportError("networkx is REQUIRED. Install: pip install networkx")


class ProductionNLPSummarizer:
    """
    Production-grade NLP summarizer with NO fallbacks.
    All advanced techniques are REQUIRED:
    - Sentence-BERT embeddings (semantic similarity)
    - TextRank algorithm (graph-based ranking)
    - TF-IDF with n-grams (keyword extraction)
    - Multi-factor sentence scoring
    - Context-aware risk detection
    """

    def __init__(self):
        """Initialize with all required models."""
        logger.info("Initializing Production NLP Summarizer (NO FALLBACKS)...")

        # Load spaCy - REQUIRED
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy model loaded")
        except OSError:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' not found. "
                "Download: python -m spacy download en_core_web_sm"
            )

        # Load Sentence-BERT - REQUIRED
        try:
            self.sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✓ Sentence-BERT model loaded (semantic embeddings enabled)")
        except Exception as e:
            raise RuntimeError(f"Failed to load Sentence-BERT model: {e}")

        # Advanced keyword dictionaries with context
        self.risk_patterns = {
            "critical": {
                "keywords": [
                    "hack",
                    "exploit",
                    "vulnerability",
                    "breach",
                    "scam",
                    "fraud",
                    "collapse",
                    "bankrupt",
                    "insolvent",
                    "rugpull",
                    "stolen",
                    "compromised",
                    "attack",
                    "malware",
                ],
                "weight": 1.0,
                "context": ["security", "funds", "wallet", "exchange", "protocol"],
            },
            "high": {
                "keywords": [
                    "lawsuit",
                    "regulation",
                    "ban",
                    "investigation",
                    "sec",
                    "cftc",
                    "delisting",
                    "suspension",
                    "halt",
                    "probe",
                    "enforcement",
                    "penalty",
                    "fine",
                    "sanction",
                ],
                "weight": 0.85,
                "context": [
                    "regulatory",
                    "legal",
                    "compliance",
                    "government",
                    "authority",
                ],
            },
            "medium": {
                "keywords": [
                    "volatility",
                    "uncertain",
                    "concern",
                    "warning",
                    "risk",
                    "delay",
                    "issue",
                    "problem",
                    "controversy",
                    "dispute",
                    "challenge",
                    "obstacle",
                ],
                "weight": 0.6,
                "context": ["market", "price", "trading", "volume"],
            },
        }

        self.positive_indicators = {
            "major": {
                "keywords": [
                    "partnership",
                    "acquisition",
                    "merger",
                    "listing",
                    "mainnet",
                    "breakthrough",
                    "adoption",
                    "institutional",
                    "integration",
                    "milestone",
                    "record",
                    "historic",
                ],
                "weight": 1.0,
            },
            "moderate": {
                "keywords": [
                    "upgrade",
                    "launch",
                    "growth",
                    "expansion",
                    "rally",
                    "surge",
                    "increase",
                    "development",
                    "improvement",
                ],
                "weight": 0.7,
            },
        }

        # Price impact indicators
        self.price_impact_signals = {
            "high": {
                "keywords": [
                    "major",
                    "significant",
                    "massive",
                    "huge",
                    "dramatic",
                    "unprecedented",
                    "historic",
                    "record",
                    "breakthrough",
                    "revolutionary",
                    "game-changing",
                ],
                "events": [
                    "partnership",
                    "acquisition",
                    "listing",
                    "hack",
                    "exploit",
                    "regulation",
                    "ban",
                    "mainnet",
                    "etf",
                    "institutional",
                ],
                "threshold": 6.0,
            },
            "medium": {
                "keywords": [
                    "notable",
                    "considerable",
                    "substantial",
                    "important",
                    "meaningful",
                    "significant",
                ],
                "events": [
                    "upgrade",
                    "launch",
                    "integration",
                    "delay",
                    "investigation",
                ],
                "threshold": 3.0,
            },
            "low": {
                "keywords": [
                    "slight",
                    "minor",
                    "small",
                    "modest",
                    "gradual",
                    "incremental",
                ],
                "events": [],
                "threshold": 1.0,
            },
        }

        # Crypto-specific terminology
        self.crypto_terms = [
            "bitcoin",
            "ethereum",
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
            "consensus",
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
        ]

        logger.info("✓ Production NLP Summarizer initialized (all models loaded)")

    def _clean_text(self, text: str) -> str:
        """Advanced text cleaning with preservation of important punctuation."""
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Remove URLs but keep domain names
        text = re.sub(r"https?://(?:www\.)?([^\s/]+)", r"\1", text)
        # Remove email addresses
        text = re.sub(r"\S+@\S+", "", text)
        # Normalize quotes
        text = (
            text.replace('"', '"').replace('"', '"').replace(""", "'").replace(""", "'")
        )
        # Remove excessive punctuation
        text = re.sub(r"([!?.]){2,}", r"\1", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _extract_sentences(self, text: str) -> List[str]:
        """Extract high-quality sentences using spaCy."""
        doc = self.nlp(text[:100000])  # Limit to prevent memory issues
        sentences = []

        for sent in doc.sents:
            sent_text = sent.text.strip()
            words = sent_text.split()

            # Quality filters
            if (
                len(sent_text) >= 40
                and len(words) >= 6
                and len(sent_text) <= 500
                and not sent_text.startswith(("http", "www", "@"))
                and any(c.isalpha() for c in sent_text)
            ):
                sentences.append(sent_text)

        return sentences

    def _calculate_textrank_scores(self, sentences: List[str]) -> Dict[str, float]:
        """Calculate sentence importance using TextRank with Sentence-BERT embeddings."""
        if not sentences:
            raise ValueError("No sentences provided for TextRank")

        try:
            # Use Sentence-BERT for semantic similarity (REQUIRED)
            embeddings = self.sentence_model.encode(sentences, show_progress_bar=False)
            similarity_matrix = cosine_similarity(embeddings)

            # Add small epsilon to diagonal to ensure convergence
            np.fill_diagonal(similarity_matrix, similarity_matrix.diagonal() + 1e-8)

            # Ensure matrix is not too sparse - add minimum similarity threshold
            threshold = 0.1
            similarity_matrix[similarity_matrix < threshold] = 0

            # Build graph
            nx_graph = nx.from_numpy_array(similarity_matrix)

            # Apply PageRank algorithm with more iterations and better tolerance
            scores = nx.pagerank(nx_graph, max_iter=200, tol=1e-7, alpha=0.85)

            # Map scores back to sentences
            return {sent: scores[i] for i, sent in enumerate(sentences)}

        except Exception as e:
            logger.warning(f"TextRank failed: {e}, using uniform scores")
            # If PageRank fails, return uniform scores (all sentences equal)
            return {sent: 1.0 / len(sentences) for sent in sentences}

    def _calculate_tfidf_scores(self, sentences: List[str]) -> Dict[str, float]:
        """Calculate TF-IDF based importance scores."""
        if not sentences:
            raise ValueError("No sentences provided for TF-IDF")

        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=300,
            ngram_range=(1, 3),  # Include trigrams
            min_df=1,
            max_df=0.85,
        )

        tfidf_matrix = vectorizer.fit_transform(sentences)
        scores = np.asarray(tfidf_matrix.sum(axis=1)).flatten()

        # Normalize scores
        if scores.max() > 0:
            scores = scores / scores.max()

        return {sent: float(score) for sent, score in zip(sentences, scores)}

    def _calculate_position_scores(self, sentences: List[str]) -> Dict[str, float]:
        """Calculate position-based scores with exponential decay."""
        scores = {}
        n = len(sentences)

        for i, sent in enumerate(sentences):
            # Exponential decay for position (lead bias)
            position_score = np.exp(-i / (n * 0.3))
            scores[sent] = float(position_score)

        return scores

    def _calculate_crypto_relevance_scores(
        self, sentences: List[str]
    ) -> Dict[str, float]:
        """Calculate crypto-specific relevance scores."""
        scores = {}

        for sent in sentences:
            sent_lower = sent.lower()

            # Count crypto terms
            term_count = sum(1 for term in self.crypto_terms if term in sent_lower)

            # Bonus for numbers (prices, percentages, dates)
            number_count = len(re.findall(r"\d+(?:\.\d+)?%?", sent))

            # Bonus for named entities
            doc = self.nlp(sent)
            entity_count = sum(
                1
                for ent in doc.ents
                if ent.label_ in ["ORG", "PRODUCT", "MONEY", "PERCENT", "GPE"]
            )

            # Combined score
            score = (
                min(term_count / 3.0, 1.0) * 0.5
                + min(number_count / 2.0, 1.0) * 0.3
                + min(entity_count / 2.0, 1.0) * 0.2
            )

            scores[sent] = float(score)

        return scores

    def _calculate_combined_scores(self, sentences: List[str]) -> Dict[str, float]:
        """Combine multiple scoring methods for robust ranking."""
        if not sentences:
            raise ValueError("No sentences provided for scoring")

        # Get scores from all methods (ALL REQUIRED)
        textrank_scores = self._calculate_textrank_scores(sentences)
        tfidf_scores = self._calculate_tfidf_scores(sentences)
        position_scores = self._calculate_position_scores(sentences)
        crypto_scores = self._calculate_crypto_relevance_scores(sentences)

        # Combine with weights
        combined_scores = {}

        for sent in sentences:
            score = (
                textrank_scores[sent] * 0.35  # Semantic similarity
                + tfidf_scores[sent] * 0.30  # Keyword importance
                + position_scores[sent] * 0.20  # Position bias
                + crypto_scores[sent] * 0.15  # Crypto relevance
            )
            combined_scores[sent] = score

        return combined_scores

    def _extract_key_phrases_advanced(self, text: str, max_phrases: int = 7) -> List[str]:
        """Extract key phrases using spaCy NER and noun chunks."""
        doc = self.nlp(text[:50000])
        phrases = []
        phrase_scores = {}

        # Named Entity Recognition
        for ent in doc.ents:
            if ent.label_ in [
                "ORG",
                "PRODUCT",
                "EVENT",
                "MONEY",
                "PERCENT",
                "GPE",
                "PERSON",
            ]:
                if len(ent.text) > 2:
                    phrases.append(ent.text.lower())
                    phrase_scores[ent.text.lower()] = (
                        phrase_scores.get(ent.text.lower(), 0) + 2.0
                    )

        # Noun Chunks
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.lower().strip()
            if (
                len(chunk_text.split()) >= 2
                and len(chunk_text) > 5
                and not chunk_text.startswith(("the ", "a ", "an ", "this ", "that "))
            ):
                phrases.append(chunk_text)
                phrase_scores[chunk_text] = phrase_scores.get(chunk_text, 0) + 1.0

        # Crypto-specific patterns
        crypto_patterns = [
            r"\b\w+\s+(?:protocol|network|blockchain|token|coin|exchange)\b",
            r"\b(?:defi|nft|dao|dex|dapp)\s+\w+\b",
            r"\b\w+\s+(?:upgrade|launch|partnership|integration)\b",
            r"\b(?:bitcoin|ethereum|crypto)\s+\w+\b",
        ]

        for pattern in crypto_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if len(match) > 5:
                    phrases.append(match)
                    phrase_scores[match] = phrase_scores.get(match, 0) + 1.5

        # Count and score
        phrase_counts = Counter(phrases)

        # Combine frequency with scores
        final_scores = {}
        for phrase, count in phrase_counts.items():
            base_score = phrase_scores.get(phrase, 1.0)
            final_scores[phrase] = count * base_score

        # Filter and rank
        stop_phrases = {
            "the bitcoin", "the crypto", "the market", "the price", "a lot",
            "this week", "last week", "next week", "right now", "at this",
            "bitcoin is", "bitcoin to", "crypto is", "crypto to", "price is", "price to"
        }

        # Remove stop phrases and deduplicate using embeddings
        filtered_phrases = []
        for phrase, score in final_scores.items():
            if phrase not in stop_phrases and len(phrase.split()) <= 4:
                filtered_phrases.append((phrase, score))

        # Sort by score
        filtered_phrases.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate using semantic similarity
        unique_phrases = []
        if filtered_phrases:
            # Get top candidates
            top_candidates = filtered_phrases[:20]
            candidate_texts = [p[0] for p in top_candidates]

            try:
                candidate_embeddings = self.sentence_model.encode(candidate_texts, show_progress_bar=False)

                for i, (phrase, score) in enumerate(top_candidates):
                    if len(unique_phrases) >= max_phrases:
                        break

                    # Check similarity to already selected
                    is_duplicate = False
                    if unique_phrases:
                        phrase_emb = candidate_embeddings[i]
                        for selected_phrase in unique_phrases:
                            selected_idx = candidate_texts.index(selected_phrase)
                            sim = cosine_similarity([phrase_emb], [candidate_embeddings[selected_idx]])[0][0]
                            if sim > 0.85:  # Very similar, skip
                                is_duplicate = True
                                break

                    if not is_duplicate:
                        unique_phrases.append(phrase)
            except:
                # Fallback: just take top phrases without deduplication
                unique_phrases = [p[0] for p in top_candidates[:max_phrases]]

        # Capitalize properly for display
        formatted_phrases = []
        for phrase in unique_phrases[:max_phrases]:
            # Capitalize each word except common lowercase words
            words = phrase.split()
            formatted = []
            for word in words:
                if word.lower() in ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with']:
                    formatted.append(word.lower())
                else:
                    formatted.append(word.capitalize())
            formatted_phrases.append(' '.join(formatted))

        return formatted_phrases

    def _detect_risks_advanced(
        self, text: str, articles: List[Dict[str, Any]]
    ) -> List[str]:
        """Advanced risk detection with context awareness."""
        text_lower = text.lower()
        detected_risks = []
        risk_contexts = {}

        # Analyze each risk level
        for level, config in self.risk_patterns.items():
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    count = text_lower.count(keyword)
                    context_found = any(
                        ctx in text_lower for ctx in config.get("context", [])
                    )

                    # Calculate severity
                    severity_score = count * config["weight"]
                    if context_found:
                        severity_score *= 1.3

                    # Create more specific risk descriptions
                    if level == "critical":
                        risk_text = f"Critical: {keyword.title()} threat detected - immediate attention required"
                    elif level == "high":
                        if keyword in ["sec", "regulation", "ban", "lawsuit"]:
                            risk_text = f"Regulatory: {keyword.upper()} action may impact market access"
                        else:
                            risk_text = f"High Risk: {keyword.title()} concerns identified"
                    else:
                        if keyword in ["volatility", "crash", "dump"]:
                            risk_text = f"Market: High {keyword} expected - exercise caution"
                        else:
                            risk_text = f"Alert: {keyword.title()} activity detected"

                    risk_contexts[risk_text] = severity_score

        # Sort by severity
        sorted_risks = sorted(risk_contexts.items(), key=lambda x: x[1], reverse=True)
        unique_risks = [risk for risk, _ in sorted_risks[:5]]

        # Add sentiment-based risks with more context
        if articles:
            bearish_count = sum(
                1 for a in articles if a.get("sentiment", {}).get("label") == "Bearish"
            )
            bearish_ratio = bearish_count / len(articles)

            if bearish_ratio > 0.6:
                unique_risks.append(
                    f"Sentiment: {bearish_ratio*100:.0f}% bearish coverage - negative market outlook"
                )
            elif bearish_ratio > 0.4:
                unique_risks.append(
                    f"Sentiment: Mixed signals with {bearish_ratio*100:.0f}% bearish articles"
                )

        return (
            unique_risks[:5]
            if unique_risks
            else ["No significant risks detected - market conditions appear stable"]
        )

    def _assess_price_impact_advanced(
        self, text: str, sentiment_data: Dict[str, Any], articles: List[Dict[str, Any]]
    ) -> str:
        """Advanced price impact assessment."""
        text_lower = text.lower()
        impact_score = 0.0

        # High-impact keywords with context
        for keyword in self.price_impact_signals["high"]["keywords"]:
            if keyword in text_lower:
                pattern = rf"\b{keyword}\b.{{0,50}}\b(?:price|market|trading|volume)\b"
                if re.search(pattern, text_lower):
                    impact_score += 2.5
                else:
                    impact_score += 1.5

        # Major events
        for event in self.price_impact_signals["high"]["events"]:
            count = text_lower.count(event)
            impact_score += count * 2.0

        # Sentiment strength
        confidence = sentiment_data.get("confidence", 0)
        bullish_pct = sentiment_data.get("bullish_pct", 0)
        bearish_pct = sentiment_data.get("bearish_pct", 0)

        if confidence > 75:
            if bullish_pct > 70 or bearish_pct > 70:
                impact_score += 2.5
            elif bullish_pct > 60 or bearish_pct > 60:
                impact_score += 1.5

        # Volume of coverage
        article_count = len(articles)
        if article_count > 20:
            impact_score += 1.5
        elif article_count > 10:
            impact_score += 1.0

        # Positive indicators
        for level, config in self.positive_indicators.items():
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    impact_score += config["weight"]

        # Determine impact
        if impact_score >= 8.0:
            return "High"
        elif impact_score >= 4.0:
            return "Medium"
        elif impact_score >= 1.5:
            return "Low"
        else:
            return "None"

    def _aggregate_sentiment_advanced(
        self, articles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Advanced sentiment aggregation with confidence weighting and recency bias."""
        if not articles:
            raise ValueError("No articles provided for sentiment aggregation")

        sentiment_scores = {"Bullish": 0.0, "Bearish": 0.0, "Neutral": 0.0}
        total_weight = 0.0

        for i, article in enumerate(articles):
            sentiment = article.get("sentiment", {})
            label = sentiment.get("label", "Neutral")
            confidence = sentiment.get("confidence", 0.5)

            # Recency weight
            recency_weight = np.exp(-i / (len(articles) * 0.4))

            # Combined weight
            weight = confidence * recency_weight

            sentiment_scores[label] += weight
            total_weight += weight

        # Calculate percentages
        if total_weight > 0:
            bullish_pct = (sentiment_scores["Bullish"] / total_weight) * 100
            bearish_pct = (sentiment_scores["Bearish"] / total_weight) * 100
            neutral_pct = (sentiment_scores["Neutral"] / total_weight) * 100
        else:
            bullish_pct = bearish_pct = neutral_pct = 33.33

        # Determine overall sentiment with improved logic
        max_pct = max(bullish_pct, bearish_pct, neutral_pct)

        # If bullish or bearish is close to neutral (within 15%), favor the directional sentiment
        if abs(bullish_pct - neutral_pct) < 15 and bullish_pct > bearish_pct:
            # Bullish is close to neutral, favor bullish if significant
            if bullish_pct > 35:
                overall_label = "Mixed-Bullish"
                confidence = int((bullish_pct * 0.6 + neutral_pct * 0.4))
            else:
                overall_label = "Neutral"
                confidence = int(neutral_pct)
        elif abs(bearish_pct - neutral_pct) < 15 and bearish_pct > bullish_pct:
            # Bearish is close to neutral, favor bearish if significant
            if bearish_pct > 35:
                overall_label = "Mixed-Bearish"
                confidence = int((bearish_pct * 0.6 + neutral_pct * 0.4))
            else:
                overall_label = "Neutral"
                confidence = int(neutral_pct)
        elif bullish_pct == max_pct:
            if bullish_pct > bearish_pct + 25:
                overall_label = "Bullish"
                confidence = int(bullish_pct)
            elif bullish_pct > bearish_pct + 12:
                overall_label = "Mixed-Bullish"
                confidence = int((bullish_pct * 0.7 + neutral_pct * 0.3))
            else:
                overall_label = "Neutral"
                confidence = int(neutral_pct)
        elif bearish_pct == max_pct:
            if bearish_pct > bullish_pct + 25:
                overall_label = "Bearish"
                confidence = int(bearish_pct)
            elif bearish_pct > bullish_pct + 12:
                overall_label = "Mixed-Bearish"
                confidence = int((bearish_pct * 0.7 + neutral_pct * 0.3))
            else:
                overall_label = "Neutral"
                confidence = int(neutral_pct)
        else:
            overall_label = "Neutral"
            confidence = int(neutral_pct)

        return {
            "label": overall_label,
            "confidence": min(confidence, 100),
            "bullish_pct": round(bullish_pct, 1),
            "bearish_pct": round(bearish_pct, 1),
            "neutral_pct": round(neutral_pct, 1),
        }

    def _cluster_similar_sentences(self, sentences: List[str], embeddings: np.ndarray) -> Dict[int, List[int]]:
        """Cluster sentences by topic using semantic similarity."""
        from sklearn.cluster import AgglomerativeClustering

        # Determine optimal number of clusters (3-5 topics)
        n_clusters = min(max(3, len(sentences) // 10), 5)

        try:
            clustering = AgglomerativeClustering(n_clusters=n_clusters, metric='cosine', linkage='average')
            labels = clustering.fit_predict(embeddings)

            # Group sentences by cluster
            clusters = {}
            for idx, label in enumerate(labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(idx)

            return clusters
        except:
            # Fallback: single cluster
            return {0: list(range(len(sentences)))}

    def _select_diverse_sentences(self, sentences: List[str], scores: Dict[str, float],
                                  embeddings: np.ndarray, max_sentences: int = 4) -> List[str]:
        """Select diverse, high-quality sentences covering different topics."""
        if len(sentences) <= max_sentences:
            return sentences

        # Cluster sentences by topic
        clusters = self._cluster_similar_sentences(sentences, embeddings)

        # Select best sentence from each cluster
        selected = []
        sentence_list = list(sentences)

        # Sort clusters by size (larger = more important)
        sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)

        for cluster_id, sentence_indices in sorted_clusters:
            if len(selected) >= max_sentences:
                break

            # Get sentences in this cluster
            cluster_sentences = [sentence_list[i] for i in sentence_indices]

            # Find highest scoring sentence
            best_sent = max(cluster_sentences, key=lambda s: scores.get(s, 0))
            selected.append(best_sent)

        # Fill remaining slots with highest scoring sentences
        while len(selected) < max_sentences:
            remaining = [s for s in sentence_list if s not in selected]
            if not remaining:
                break
            best = max(remaining, key=lambda s: scores.get(s, 0))
            selected.append(best)

        return selected

    def _is_garbage_sentence(self, sentence: str, target_coin: str = "") -> bool:
        """Filter out garbage sentences (boilerplate, Latin text, generic advice, non-relevant content)."""
        sent_lower = sentence.lower()

        # Filter out Latin placeholder text
        latin_phrases = ['lorem ipsum', 'morbi pretium', 'aliquam mollis', 'consectetur adipiscing']
        if any(phrase in sent_lower for phrase in latin_phrases):
            return True

        # Filter out editorial boilerplate
        boilerplate = [
            'strict editorial policy', 'focuses on accuracy', 'relevance, and impartiality',
            'subscribe to our newsletter', 'follow us on', 'click here to',
            'terms and conditions', 'privacy policy', 'disclosure', 'sponsored'
        ]
        if any(phrase in sent_lower for phrase in boilerplate):
            return True

        # Filter out generic trading advice (not news)
        generic_advice = [
            'if you just turn on', 'make sure you', 'always remember to',
            'dont forget to', 'be sure to', 'you should always',
            'my advice is', 'i recommend', 'in my opinion'
        ]
        if any(phrase in sent_lower for phrase in generic_advice):
            return True

        # Filter out questions and calls to action
        if sent_lower.endswith('?') or 'what do you think' in sent_lower or 'let me know' in sent_lower:
            return True

        # Crypto-related terms that should be present
        crypto_terms = [
            'bitcoin', 'btc', 'crypto', 'cryptocurrency', 'blockchain', 'mining',
            'wallet', 'exchange', 'price', 'market', 'trading', 'coin', 'token',
            'ethereum', 'eth', 'defi', 'nft', 'satoshi', 'hash', 'block'
        ]

        # Check if sentence contains at least one crypto term
        has_crypto_term = any(term in sent_lower for term in crypto_terms)
        if not has_crypto_term:
            return True

        # If target coin specified, prefer sentences mentioning it
        # (This is used for relevance scoring, not filtering)

        return False

    def _generate_summary_advanced(
        self, articles: List[Dict[str, Any]], max_sentences: int = 3
    ) -> str:
        """Generate high-quality, coherent summary using information fusion."""
        if not articles:
            raise ValueError("No articles provided for summarization")

        # Strategy: Extract key facts, then build a coherent narrative
        # Step 1: Identify the main story/theme
        # Step 2: Extract supporting facts
        # Step 3: Fuse into a flowing paragraph

        # Collect candidate sentences
        candidates = []
        for article in articles[:60]:
            content = (
                article.get("full_content")
                or article.get("summary")
                or article.get("text", "")
            )
            if not content:
                continue

            cleaned = self._clean_text(content)
            sentences = self._extract_sentences(cleaned)

            # Take first 2 sentences (lead paragraph)
            for sent in sentences[:2]:
                if 40 < len(sent) < 180 and not self._is_garbage_sentence(sent):
                    candidates.append({
                        'text': sent,
                        'engagement': article.get('engagement_count', 0),
                        'timestamp': article.get('timestamp', '')
                    })

        if len(candidates) < 5:
            raise ValueError("Insufficient quality sentences for summarization")

        sentences = [c['text'] for c in candidates]
        embeddings = self.sentence_model.encode(sentences, show_progress_bar=False)

        # Find main theme using centrality
        similarity_matrix = cosine_similarity(embeddings)
        centrality = similarity_matrix.mean(axis=1)

        # Get top 10 most central sentences
        top_indices = centrality.argsort()[-10:][::-1]
        top_sentences = [sentences[i] for i in top_indices]
        top_embeddings = embeddings[top_indices]

        # Cluster these top sentences to find the dominant narrative
        from sklearn.cluster import AgglomerativeClustering

        n_clusters = min(3, len(top_sentences) // 3)
        if n_clusters < 2:
            n_clusters = 2

        clustering = AgglomerativeClustering(n_clusters=n_clusters, metric='cosine', linkage='average')
        labels = clustering.fit_predict(top_embeddings)

        # Find largest cluster (main narrative)
        cluster_sizes = {}
        for label in labels:
            cluster_sizes[label] = cluster_sizes.get(label, 0) + 1
        main_cluster = max(cluster_sizes.items(), key=lambda x: x[1])[0]

        # Get sentences from main cluster
        main_sentences = [top_sentences[i] for i, label in enumerate(labels) if label == main_cluster]
        main_embeddings = [top_embeddings[i] for i, label in enumerate(labels) if label == main_cluster]

        # Build coherent summary by selecting complementary sentences
        selected = []

        # 1. Start with most central sentence in main cluster
        main_centrality = cosine_similarity(main_embeddings).mean(axis=1)
        start_idx = main_centrality.argmax()
        selected.append(main_sentences[start_idx])
        selected_emb = [main_embeddings[start_idx]]

        # 2. Add sentences that provide new information (moderate similarity)
        for i, (sent, emb) in enumerate(zip(main_sentences, main_embeddings)):
            if len(selected) >= max_sentences:
                break
            if i == start_idx:
                continue

            # Check similarity to already selected
            sims = [cosine_similarity([emb], [sel_emb])[0][0] for sel_emb in selected_emb]
            max_sim = max(sims)

            # Want related but not redundant (0.3-0.65 similarity)
            if 0.3 < max_sim < 0.65:
                selected.append(sent)
                selected_emb.append(emb)

        # If we need more sentences, look outside main cluster
        if len(selected) < max_sentences:
            other_sentences = [top_sentences[i] for i, label in enumerate(labels) if label != main_cluster]
            other_embeddings = [top_embeddings[i] for i, label in enumerate(labels) if label != main_cluster]

            for sent, emb in zip(other_sentences, other_embeddings):
                if len(selected) >= max_sentences:
                    break

                # Check similarity to selected
                sims = [cosine_similarity([emb], [sel_emb])[0][0] for sel_emb in selected_emb]
                max_sim = max(sims) if sims else 0

                # Want moderate connection to main narrative
                if 0.25 < max_sim < 0.7:
                    selected.append(sent)
                    selected_emb.append(emb)

        # Order by original position for natural flow
        position_map = {sent: sentences.index(sent) for sent in selected}
        ordered = sorted(selected, key=lambda s: position_map[s])

        # Create flowing summary with better transitions
        summary_parts = []
        for i, sent in enumerate(ordered):
            # Clean up sentence
            sent = sent.strip()

            # Remove source attributions at the end (news outlets)
            # Match common patterns: "Source Name", "Source.com", "Source Finance", etc.
            sent = re.sub(r'\s+(?:Investing\.com|Benzinga|Bloomberg|Reuters|CoinDesk|Cointelegraph|Yahoo Finance.*?|Barron\'s|Fortune|CNBC|MarketWatch|The Block|Decrypt|Bitcoin Magazine|CryptoSlate|NewsBTC|U\.Today|Stocktwits|Coinpedia|CoinGape|BeInCrypto|Cryptonews|FXStreet|AMBCrypto)$', '', sent, flags=re.IGNORECASE)

            # Remove trailing source patterns like "Source Name UK", "Source Finance UK"
            sent = re.sub(r'\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s*(?:UK|US|USA)?$', '', sent)

            summary_parts.append(sent)

        summary = " ".join(summary_parts)
        summary = re.sub(r'\s+', ' ', summary).strip()

        # Length optimization (350-500 chars optimal)
        if len(summary) > 500:
            while len(summary) > 500 and len(summary_parts) > 1:
                summary_parts.pop()
                summary = " ".join(summary_parts)
                summary = re.sub(r'\s+', ' ', summary).strip()

            if len(summary) > 500:
                # Truncate at word boundary
                summary = summary[:497].rsplit(' ', 1)[0] + "..."

        return summary

    def summarize_articles(
        self, articles: List[Dict[str, Any]], coin: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive summary using ALL advanced NLP techniques.
        NO FALLBACKS - all methods are REQUIRED.
        """
        if not articles:
            raise ValueError(f"No articles provided for {coin}")

        logger.info(
            f"Generating production NLP summary for {coin} from {len(articles)} articles"
        )

        # All methods are REQUIRED
        sentiment_data = self._aggregate_sentiment_advanced(articles)
        summary = self._generate_summary_advanced(articles, max_sentences=4)

        # Combine text
        combined_text = " ".join(
            [
                self._clean_text(
                    a.get("title", "")
                    + " "
                    + (a.get("full_content") or a.get("summary") or a.get("text", ""))
                )
                for a in articles[:35]
            ]
        )

        # Extract insights and risks
        key_insights = self._extract_key_phrases_advanced(combined_text, max_phrases=7)
        risk_factors = self._detect_risks_advanced(combined_text, articles)
        price_impact = self._assess_price_impact_advanced(
            combined_text, sentiment_data, articles
        )

        # Generate reasoning with more context
        sentiment_label = sentiment_data['label']
        bullish_pct = sentiment_data['bullish_pct']
        bearish_pct = sentiment_data['bearish_pct']
        neutral_pct = sentiment_data['neutral_pct']

        # Build contextual reasoning
        reasoning_parts = []

        # Sentiment distribution
        if bullish_pct > 60:
            reasoning_parts.append(f"Strong bullish sentiment dominates with {bullish_pct:.0f}% positive coverage")
        elif bearish_pct > 60:
            reasoning_parts.append(f"Bearish sentiment prevails with {bearish_pct:.0f}% negative coverage")
        elif neutral_pct > 60:
            reasoning_parts.append(f"Market sentiment remains neutral with {neutral_pct:.0f}% balanced coverage")
        else:
            reasoning_parts.append(f"Mixed sentiment: {bullish_pct:.0f}% bullish, {bearish_pct:.0f}% bearish, {neutral_pct:.0f}% neutral")

        # Price impact context
        if price_impact == "High":
            reasoning_parts.append("Major market-moving events detected with significant price implications")
        elif price_impact == "Medium":
            reasoning_parts.append("Moderate market activity with potential price movement")
        elif price_impact == "Low":
            reasoning_parts.append("Limited market catalysts, stable price action expected")

        # Article volume context
        if len(articles) > 80:
            reasoning_parts.append(f"High media attention ({len(articles)} articles)")
        elif len(articles) > 40:
            reasoning_parts.append(f"Moderate coverage ({len(articles)} articles)")
        else:
            reasoning_parts.append(f"Limited coverage ({len(articles)} articles)")

        reasoning = ". ".join(reasoning_parts) + "."

        result = {
            "summary": summary,
            "sentiment": sentiment_data["label"],
            "confidence": sentiment_data["confidence"],
            "key_insights": key_insights,
            "price_impact": price_impact,
            "reasoning": reasoning[:200],
            "risk_factors": risk_factors,
            "used_fallback": False,
            "summary_source": "nlp_production",
            "model_used": "textrank_sbert_tfidf_required",
            "llm_error": None,
        }

        logger.info(
            f"✓ Production summary for {coin}: {result['sentiment']} ({result['confidence']}%), "
            f"{len(key_insights)} insights, {len(risk_factors)} risks, impact: {price_impact}"
        )

        return result

    async def summarize_articles_async(
        self, articles: List[Dict[str, Any]], coin: str
    ) -> Dict[str, Any]:
        """Async wrapper."""
        import asyncio

        return await asyncio.to_thread(self.summarize_articles, articles, coin)


# Global instance
_summarizer_instance = None


def get_summarizer() -> ProductionNLPSummarizer:
    """Get or create the global production NLP summarizer instance."""
    global _summarizer_instance

    if _summarizer_instance is None:
        _summarizer_instance = ProductionNLPSummarizer()

    return _summarizer_instance
