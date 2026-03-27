import React, { useEffect, useState } from 'react';
import { MessageSquare, Twitter, Globe, TrendingUp, AlertCircle, Info, X, ExternalLink, Clock, ThumbsUp, FileText, Sparkles, TrendingDown, Minus, Newspaper, Users } from 'lucide-react';
import { useCrypto } from '../context/CryptoContext';
import { apiClient } from '../services/apiClient';

interface ArticleSentiment {
  label?: string;
  confidence?: number;
  polarity?: number;
  scores?: Record<string, number>;
}

interface Article {
  id: string;
  title: string;
  summary: string;
  full_content: string;
  source_type: string;
  source: string;
  timestamp: string;
  url: string;
  platform_id: string;
  engagement_count: number;
  image_url?: string;
  sentiment?: ArticleSentiment | null;
  needs_full_fetch?: boolean;
}

interface SentimentMetrics {
  total_mentions: number;
  sentiment_polarity: number | null;
  sentiment_label: string | null;
  unified_score: number | null;
  layer_a_weight: number;
  layer_b_weight: number;
  bullish_percentage: number | null;
  bearish_percentage: number | null;
  neutral_percentage: number | null;
}

interface SentimentResponse {
  coin: string;
  global_metrics: SentimentMetrics;
  clusters: any[];
  last_updated: string;
  data_window_minutes: number;
}

interface SummaryData {
  coin: string;
  summary: string;
  article_count: number;
  layer_a_count: number;
  layer_b_count: number;
  key_topics?: string[];
  key_insights?: string[];
  sentiment?: string;
  sentiment_label: string | null;
  unified_score: number | null;
  confidence?: number;
  price_impact?: string;
  reasoning?: string;
  risk_factors?: string[];
  bullish_percentage: number | null;
  bearish_percentage: number | null;
  neutral_percentage: number | null;
  recent_articles: Article[];
  summary_source?: string;
}

interface SentimentCacheSnapshot {
  articles: Article[];
  sentimentMetrics: SentimentMetrics | null;
  summaryData: SummaryData | null;
  updatedAt: string;
}

const CACHE_PREFIX = 'sentiment-page-cache:';

const getCacheKey = (coinId: string) => `${CACHE_PREFIX}${coinId}`;

const readSentimentCache = (coinId: string): SentimentCacheSnapshot | null => {
  if (!coinId) return null;

  try {
    const raw = sessionStorage.getItem(getCacheKey(coinId));
    if (!raw) return null;
    return JSON.parse(raw) as SentimentCacheSnapshot;
  } catch (error) {
    console.warn('Failed to read sentiment cache', error);
    return null;
  }
};

const writeSentimentCache = (
  coinId: string,
  snapshot: Omit<SentimentCacheSnapshot, 'updatedAt'>
) => {
  if (!coinId) return;

  try {
    sessionStorage.setItem(
      getCacheKey(coinId),
      JSON.stringify({
        ...snapshot,
        updatedAt: new Date().toISOString(),
      })
    );
  } catch (error) {
    console.warn('Failed to write sentiment cache', error);
  }
};

const hasMeaningfulMetrics = (metrics: SentimentMetrics | null) => {
  if (!metrics) return false;

  return (
    metrics.total_mentions > 0 ||
    metrics.sentiment_label !== null ||
    metrics.unified_score !== null ||
    metrics.sentiment_polarity !== null
  );
};

const SentimentPage: React.FC = () => {
  const { currency, coinId, loading: contextLoading } = useCrypto();
  const [articles, setArticles] = useState<Article[]>([]);
  const [sentimentMetrics, setSentimentMetrics] = useState<SentimentMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [loadingArticle, setLoadingArticle] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const visibleDataRef = React.useRef(false);

  useEffect(() => {
    const cached = readSentimentCache(coinId);

    setSelectedArticle(null);
    setShowModal(false);
    setShowSummary(false);
    setSummaryError(null);
    setError(null);

    if (cached) {
      setArticles(cached.articles ?? []);
      setSentimentMetrics(cached.sentimentMetrics ?? null);
      setSummaryData(cached.summaryData ?? null);
      return;
    }

    setArticles([]);
    setSentimentMetrics(null);
    setSummaryData(null);
  }, [coinId]);

  useEffect(() => {
    if (!coinId) return;

    if (articles.length === 0 && !sentimentMetrics && !summaryData) {
      return;
    }

    writeSentimentCache(coinId, {
      articles,
      sentimentMetrics,
      summaryData,
    });
  }, [articles, coinId, sentimentMetrics, summaryData]);

  useEffect(() => {
    visibleDataRef.current =
      articles.length > 0 || sentimentMetrics !== null || summaryData !== null;
  }, [articles, sentimentMetrics, summaryData]);

  useEffect(() => {
    const controller = new AbortController();

    const fetchSentimentData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [metricsData, articlesData]: [any, any] = await Promise.all([
          apiClient.getSentiment(coinId, controller.signal),
          apiClient.getSentimentRaw(coinId, 100, controller.signal),
        ]);

        const nextMetrics = metricsData.global_metrics ?? null;
        const nextArticles = articlesData.articles ?? [];
        const hasFreshPayload =
          nextArticles.length > 0 ||
          hasMeaningfulMetrics(nextMetrics) ||
          !visibleDataRef.current;

        if (hasFreshPayload) {
          setSentimentMetrics(nextMetrics);
          setArticles(nextArticles);
        }
      } catch (err: any) {
        // Don't show error if request was cancelled
        if (err?.isAborted !== true && err?.name !== 'AbortError') {
          setError(err?.userMessage || err?.message || 'Failed to fetch sentiment data');
          console.error('Error fetching sentiment:', err);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchSentimentData();

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchSentimentData();
      }
    }, 30000);
    return () => {
      clearInterval(interval);
      controller.abort();
    };
  }, [coinId]);

  const handleArticleClick = async (article: Article) => {
    setSelectedArticle(article);
    setShowModal(true);
    setLoadingArticle(true);

    try {
      const articleDetail: any = await apiClient.getSentimentArticle(coinId, article.id);
      setSelectedArticle(articleDetail);
    } catch (err) {
      console.error('Error fetching article detail:', err);
    } finally {
      setLoadingArticle(false);
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedArticle(null);
    setLoadingArticle(false);
  };


  const handleGenerateSummary = async () => {
    setLoadingSummary(true);
    setSummaryError(null);
    try {
      const data: any = await apiClient.getSentimentSummary(coinId);
      setSummaryData(data);
      setShowSummary(true);
    } catch (err: any) {
      console.error('Error fetching summary:', err);
      setSummaryError(err?.userMessage || err?.message || 'Failed to generate summary. Please try again.');
    } finally {
      setLoadingSummary(false);
    }
  };

  const closeSummary = () => {
    setShowSummary(false);
  };

  const getSourceIcon = (platformId: string) => {
    switch (platformId) {
      case 'twitter':
        return <Twitter size={16} className="text-blue-600" />;
      case 'reddit':
        return <MessageSquare size={16} className="text-orange-600" />;
      case 'bitcointalk':
        return <Globe size={16} className="text-yellow-600" />;
      default:
        return <Globe size={16} className="text-teal-600" />;
    }
  };

  const getSourceBadgeColor = (sourceType: string) => {
    return sourceType === 'layer_a'
      ? 'bg-teal-50 text-teal-700 border-teal-200'
      : 'bg-cyan-50 text-cyan-700 border-cyan-200';
  };

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);

    if (diffHours > 0) return `${diffHours}h ago`;
    return `${diffMins}m ago`;
  };

  const getProxiedImageUrl = (imageUrl: string | undefined) => {
    if (!imageUrl) return null;
    // Use backend proxy to avoid CORS issues
    return apiClient.getImageProxyUrl(imageUrl);
  };

  const hasVisibleData = articles.length > 0 || sentimentMetrics !== null || summaryData !== null;
  const isUnavailableSummary = summaryData?.summary_source === 'unavailable';

  if ((loading || contextLoading) && !hasVisibleData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading real-time sentiment data...</p>
        </div>
      </div>
    );
  }

  if (error && !hasVisibleData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="text-red-500 mx-auto mb-4" size={48} />
          <p className="text-red-600 font-semibold mb-2">Failed to load sentiment data</p>
          <p className="text-slate-600 text-sm">{error}</p>
          <p className="text-slate-500 text-xs mt-2">Make sure the backend is running and scrapers are active</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        {error && hasVisibleData && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Showing cached sentiment data while the latest refresh failed.
          </div>
        )}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-slate-900">Real-Time Sentiment</h1>
            <p className="text-slate-600 text-xs sm:text-sm mt-1">
              Live news, social media, and forum posts for <span className="text-teal-700 font-semibold">{currency}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerateSummary}
              disabled={loadingSummary || articles.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg transition-all font-medium shadow-sm"
            >
              {loadingSummary ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Summarizing...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Analyze Summary
                </>
              )}
            </button>
            <div className="flex items-center justify-center">
              <span className="inline-flex px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200 items-center gap-2">
                <svg className="w-2 h-2" viewBox="0 0 8 8" fill="currentColor">
                  <circle cx="4" cy="4" r="4" />
                </svg>
                Live
              </span>
            </div>
          </div>
        </header>

        {/* Summary Error Banner */}
        {summaryError && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="text-red-600 flex-shrink-0" />
              <span>{summaryError}</span>
            </div>
            <button
              onClick={() => setSummaryError(null)}
              aria-label="Dismiss summary error"
              className="text-red-400 hover:text-red-600 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Metrics Cards */}
        {sentimentMetrics && (
          <div>
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Sentiment Metrics</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-lg card-shadow">
                <div className="text-slate-500 text-sm font-medium mb-2">Sentiment</div>
                {sentimentMetrics.sentiment_label ? (
                  <div className={`text-2xl font-bold font-mono tabular-nums ${sentimentMetrics.sentiment_label === 'Bullish' ? 'text-green-600' :
                      sentimentMetrics.sentiment_label === 'Bearish' ? 'text-red-600' :
                        'text-slate-600'
                    }`}>
                    {sentimentMetrics.sentiment_label}
                  </div>
                ) : (
                  <div className="text-lg text-slate-400 italic">Analyzing...</div>
                )}
              </div>
              <div className="bg-white p-4 rounded-lg card-shadow">
                <div className="text-slate-500 text-sm font-medium mb-2">Total Mentions</div>
                <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums">
                  {sentimentMetrics.total_mentions}
                </div>
              </div>
              <div className="bg-white p-4 rounded-lg card-shadow">
                <div className="text-slate-500 text-sm font-medium mb-2">Bullish</div>
                {sentimentMetrics.bullish_percentage !== null && sentimentMetrics.bullish_percentage !== undefined ? (
                  <div className="text-2xl font-bold text-green-600 font-mono tabular-nums">
                    {sentimentMetrics.bullish_percentage.toFixed(0)}%
                  </div>
                ) : (
                  <div className="text-lg text-slate-400 italic">Analyzing...</div>
                )}
              </div>
              <div className="bg-white p-4 rounded-lg card-shadow">
                <div className="text-slate-500 text-sm font-medium mb-2">Bearish</div>
                {sentimentMetrics.bearish_percentage !== null && sentimentMetrics.bearish_percentage !== undefined ? (
                  <div className="text-2xl font-bold text-red-600 font-mono tabular-nums">
                    {sentimentMetrics.bearish_percentage.toFixed(0)}%
                  </div>
                ) : (
                  <div className="text-lg text-slate-400 italic">Analyzing...</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Articles Feed */}
        <div className="bg-white rounded-lg card-shadow p-5">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Live News Feed</h2>
              <p className="text-xs text-slate-500 mt-1">Real-time articles from news sites and social media</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-slate-700 bg-slate-100 px-3 py-1 rounded-full">
                {articles.length} articles
              </span>
              {articles.length > 0 && articles.length < 10 && (
                <span className="text-xs text-slate-500 italic">
                  More articles loading...
                </span>
              )}
            </div>
          </div>

          {articles.length === 0 ? (
            <div className="text-center py-12">
              <div className="animate-pulse mb-4">
                <MessageSquare className="text-teal-600 mx-auto mb-3" size={48} />
              </div>
              <p className="text-slate-900 font-semibold mb-2">No articles yet for {currency}</p>
              <p className="text-slate-600 text-sm">
                Scrapers are collecting data. Check back in a moment.
              </p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
              {articles.map((article) => (
                <div
                  key={article.id}
                  onClick={() => handleArticleClick(article)}
                  className="bg-slate-50 p-4 rounded-lg border border-slate-200 hover:border-teal-500 hover:shadow-md transition-all cursor-pointer group"
                >
                  <div className="flex gap-4">
                    {/* Article Image */}
                    {article.image_url && (
                      <div className="flex-shrink-0 w-32 h-24 rounded-lg overflow-hidden bg-slate-200">
                        <img
                          src={article.image_url}
                          alt={article.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            // Try proxy if direct URL fails
                            if (!target.src.includes('/api/v1/proxy/image')) {
                              target.src = getProxiedImageUrl(article.image_url) || '';
                            } else {
                              target.style.display = 'none';
                            }
                          }}
                        />
                      </div>
                    )}

                    {/* Article Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          {getSourceIcon(article.platform_id)}
                          <span className="text-xs font-semibold text-slate-700 uppercase">
                            {article.source.replace('_', ' ').replace('rss', '')}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded border font-medium ${getSourceBadgeColor(article.source_type)}`}>
                            {article.source_type === 'layer_a' ? (
                              <span className="flex items-center gap-1">
                                <Newspaper size={12} />
                                News
                              </span>
                            ) : (
                              <span className="flex items-center gap-1">
                                <Users size={12} />
                                Social
                              </span>
                            )}
                          </span>
                          {/* Sentiment Badge */}
                          {article.sentiment && article.sentiment.label && (
                            <span className={`text-xs px-2 py-0.5 rounded font-medium flex items-center gap-1 ${article.sentiment.label === 'Bullish' ? 'bg-green-100 text-green-700 border border-green-300' :
                                article.sentiment.label === 'Bearish' ? 'bg-red-100 text-red-700 border border-red-300' :
                                  'bg-gray-100 text-gray-700 border border-gray-300'
                              }`}>
                              {article.sentiment.label === 'Bullish' ? (
                                <>
                                  <TrendingUp size={12} />
                                  Bullish
                                </>
                              ) : article.sentiment.label === 'Bearish' ? (
                                <>
                                  <TrendingDown size={12} />
                                  Bearish
                                </>
                              ) : (
                                <>
                                  <Minus size={12} />
                                  Neutral
                                </>
                              )}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-slate-500 text-xs whitespace-nowrap">
                          <Clock size={12} />
                          {formatTimeAgo(article.timestamp)}
                        </div>
                      </div>

                      <h3 className="text-slate-900 font-semibold mb-1 group-hover:text-teal-700 transition-colors line-clamp-2">
                        {article.title || article.summary.substring(0, 100)}
                      </h3>
                      <p className="text-slate-600 text-sm line-clamp-2">
                        {article.summary}
                      </p>

                      <div className="flex items-center gap-4 mt-2">
                        {article.engagement_count > 0 && (
                          <div className="flex items-center gap-1 text-slate-500 text-xs">
                            <ThumbsUp size={12} />
                            <span>{article.engagement_count} engagement</span>
                          </div>
                        )}
                        {article.sentiment && article.sentiment.confidence && (
                          <div className="flex items-center gap-1 text-slate-500 text-xs">
                            <span>Confidence: {(article.sentiment.confidence * 100).toFixed(0)}%</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Article Modal */}
        {showModal && selectedArticle && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={closeModal}>
            <div
              className="bg-white rounded-lg shadow-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="flex items-start justify-between p-6 border-b border-slate-200">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-3 flex-wrap">
                    {getSourceIcon(selectedArticle.platform_id)}
                    <span className="text-sm font-semibold text-slate-700 uppercase">
                      {selectedArticle.source.replace('_', ' ').replace('rss', '')}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded border font-medium ${getSourceBadgeColor(selectedArticle.source_type)}`}>
                      {selectedArticle.source_type === 'layer_a' ? (
                        <span className="flex items-center gap-1">
                          <Newspaper size={12} />
                          News
                        </span>
                      ) : (
                        <span className="flex items-center gap-1">
                          <Users size={12} />
                          Social
                        </span>
                      )}
                    </span>
                    {/* Sentiment Badge */}
                    {selectedArticle.sentiment && selectedArticle.sentiment.label && (
                      <span className={`text-sm px-3 py-1 rounded-full font-semibold flex items-center gap-1.5 ${selectedArticle.sentiment.label === 'Bullish' ? 'bg-green-100 text-green-700' :
                          selectedArticle.sentiment.label === 'Bearish' ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-700'
                        }`}>
                        {selectedArticle.sentiment.label === 'Bullish' ? (
                          <>
                            <TrendingUp size={14} />
                            Bullish
                          </>
                        ) : selectedArticle.sentiment.label === 'Bearish' ? (
                          <>
                            <TrendingDown size={14} />
                            Bearish
                          </>
                        ) : (
                          <>
                            <Minus size={14} />
                            Neutral
                          </>
                        )}
                        {selectedArticle.sentiment.confidence &&
                          ` (${(selectedArticle.sentiment.confidence * 100).toFixed(0)}%)`
                        }
                      </span>
                    )}
                  </div>
                  <h2 className="text-2xl font-bold text-slate-900">
                    {selectedArticle.title || 'Article'}
                  </h2>
                  <div className="flex items-center gap-4 mt-2 text-sm text-slate-600">
                    <span className="flex items-center gap-1">
                      <Clock size={14} />
                      {formatTimeAgo(selectedArticle.timestamp)}
                    </span>
                    {selectedArticle.engagement_count > 0 && (
                      <span className="flex items-center gap-1">
                        <ThumbsUp size={14} />
                        {selectedArticle.engagement_count} engagement
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={closeModal}
                  aria-label="Close article dialog"
                  className="text-slate-400 hover:text-slate-900 transition-colors p-2"
                >
                  <X size={24} />
                </button>
              </div>

              {/* Modal Content */}
              <div className="flex-1 overflow-y-auto p-6">
                {loadingArticle && (
                  <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    Loading full article content...
                  </div>
                )}

                {/* Article Image */}
                {selectedArticle.image_url && (
                  <div className="mb-6 rounded-lg overflow-hidden bg-slate-100">
                    <img
                      src={selectedArticle.image_url}
                      alt={selectedArticle.title}
                      className="w-full h-auto max-h-96 object-contain"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        // Try proxy if direct URL fails
                        if (!target.src.includes('/api/v1/proxy/image')) {
                          target.src = getProxiedImageUrl(selectedArticle.image_url) || '';
                        } else {
                          target.style.display = 'none';
                        }
                      }}
                    />
                  </div>
                )}

                <div className="prose prose-slate max-w-none">
                {selectedArticle.full_content.split(/\n{2,}/).map((paragraph, index) => {
                  const text = paragraph.trim();
                  if (!text) return null;
                  return (
                    <p key={index} className="text-slate-700 leading-relaxed mb-5 whitespace-pre-line">
                      {text}
                    </p>
                  );
                })}
              </div>

                {!loadingArticle && (selectedArticle.source_type === 'layer_a' || selectedArticle.platform_id === 'google_news') && selectedArticle.full_content.length < 500 && (
                  <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    <div className="flex items-start gap-2">
                      <AlertCircle size={16} className="mt-0.5 shrink-0" />
                      <div>
                        <p className="font-semibold">Only summary available</p>
                        <p className="mt-1">We could not extract the full article body automatically. Please click <span className="font-semibold">View Original Source</span> below to read the complete article on the publisher's site.</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-6 border-t border-slate-200 flex justify-between items-center bg-slate-50">
                <a
                  href={selectedArticle.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-teal-700 hover:text-teal-800 transition-colors text-sm font-medium"
                >
                  <ExternalLink size={16} />
                  View Original Source
                </a>
                <button
                  onClick={closeModal}
                  className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-900 rounded-lg transition-colors font-medium"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Summary Modal */}
        {showSummary && summaryData && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={closeSummary}>
            <div
              className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Summary Header */}
              <div className="flex items-start justify-between p-6 border-b border-slate-200 bg-teal-50">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="text-teal-700" size={24} />
                    <h2 className="text-2xl font-bold text-slate-900">
                      News Summary: {summaryData.coin.toUpperCase()}
                    </h2>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-slate-600">
                    <span className="font-medium">{summaryData.article_count} articles analyzed</span>
                    {summaryData.sentiment_label && (
                      <>
                        <span>•</span>
                        <span>Sentiment: <span className={`font-semibold ${summaryData.sentiment_label === 'Bullish' ? 'text-emerald-600' :
                            summaryData.sentiment_label === 'Bearish' ? 'text-red-600' :
                              'text-slate-700'
                          }`}>{summaryData.sentiment_label}</span></span>
                      </>
                    )}
                    {summaryData.unified_score !== null && (
                      <>
                        <span>•</span>
                        <span>Score: <span className="font-semibold text-teal-700 font-mono">{summaryData.unified_score.toFixed(2)}</span></span>
                      </>
                    )}
                  </div>
                </div>
                <button
                  onClick={closeSummary}
                  aria-label="Close summary dialog"
                  className="text-slate-400 hover:text-slate-900 transition-colors p-2"
                >
                  <X size={24} />
                </button>
              </div>

              {/* Summary Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Main Summary */}
                <div className="bg-slate-50 p-6 rounded-lg border border-slate-200">
                  <h3 className="text-lg font-semibold text-slate-900 mb-3 flex items-center gap-2">
                    <FileText size={20} className="text-teal-700" />
                    Overview
                  </h3>
                  <p className="text-slate-700 leading-relaxed text-pretty">
                    {summaryData.summary}
                  </p>
                </div>

                {isUnavailableSummary && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-900">
                    <div className="flex items-start gap-3">
                      <AlertCircle size={18} className="mt-0.5 shrink-0 text-amber-700" />
                      <div>
                        <p className="font-semibold text-balance">AI summary unavailable</p>
                        <p className="mt-1 text-amber-800 text-pretty">
                          The backend did not generate a summary for this request.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Key Insights */}
                {summaryData.key_insights && summaryData.key_insights.length > 0 && (
                  <div className="bg-slate-50 p-6 rounded-lg border border-slate-200">
                    <h3 className="text-lg font-semibold text-slate-900 mb-3 flex items-center gap-2">
                      <Sparkles size={20} className="text-teal-700" />
                      Key Insights
                    </h3>
                    <div className="space-y-2">
                      {summaryData.key_insights.map((insight, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <span className="text-teal-700 font-semibold mt-1">•</span>
                          <span className="text-slate-700 text-pretty">{insight}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* LLM Analysis Details */}
              {!isUnavailableSummary && summaryData.sentiment && summaryData.confidence !== undefined && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-white p-4 rounded-lg card-shadow">
                      <div className="text-slate-500 text-sm font-medium mb-1">Sentiment Analysis</div>
                      <div className={`text-xl font-bold ${summaryData.sentiment === 'Bullish' || summaryData.sentiment === 'Mixed-Bullish' ? 'text-emerald-600' :
                          summaryData.sentiment === 'Bearish' || summaryData.sentiment === 'Mixed-Bearish' ? 'text-red-600' :
                            'text-slate-600'
                        }`}>
                        {summaryData.sentiment}
                      </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg card-shadow">
                      <div className="text-slate-500 text-sm font-medium mb-1">Confidence</div>
                      <div className="text-xl font-bold text-teal-700 font-mono tabular-nums">
                        {summaryData.confidence}%
                      </div>
                    </div>
                    {summaryData.price_impact && (
                      <div className="bg-white p-4 rounded-lg card-shadow">
                        <div className="text-slate-500 text-sm font-medium mb-1">Price Impact</div>
                        <div className={`text-xl font-bold ${summaryData.price_impact === 'High' ? 'text-red-600' :
                            summaryData.price_impact === 'Medium' ? 'text-orange-600' :
                              'text-slate-600'
                          }`}>
                          {summaryData.price_impact}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Reasoning */}
              {!isUnavailableSummary && summaryData.reasoning && (
                  <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
                    <h3 className="text-lg font-semibold text-slate-900 mb-3 flex items-center gap-2">
                      <Info size={20} className="text-blue-700" />
                      Analysis Reasoning
                    </h3>
                    <p className="text-slate-700 leading-relaxed text-pretty">
                      {summaryData.reasoning}
                    </p>
                  </div>
                )}

                {/* Risk Factors */}
                {summaryData.risk_factors && summaryData.risk_factors.length > 0 && (
                  <div className="bg-red-50 p-6 rounded-lg border border-red-200">
                    <h3 className="text-lg font-semibold text-slate-900 mb-3 flex items-center gap-2">
                      <AlertCircle size={20} className="text-red-700" />
                      Risk Factors
                    </h3>
                    <div className="space-y-2">
                      {summaryData.risk_factors.map((risk, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <span className="text-red-700 font-semibold mt-1">⚠</span>
                          <span className="text-slate-700 text-pretty">{risk}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Source Breakdown */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white p-4 rounded-lg card-shadow">
                    <div className="text-slate-500 text-sm font-medium mb-1">Authoritative Sources</div>
                    <div className="text-2xl font-bold text-teal-700 font-mono tabular-nums">
                      {summaryData.layer_a_count}
                    </div>
                  </div>
                  <div className="bg-white p-4 rounded-lg card-shadow">
                    <div className="text-slate-500 text-sm font-medium mb-1">Social Signals</div>
                    <div className="text-2xl font-bold text-cyan-700 font-mono tabular-nums">
                      {summaryData.layer_b_count}
                    </div>
                  </div>
                </div>

                {/* Sentiment Distribution */}
                {summaryData.bullish_percentage !== null && summaryData.bearish_percentage !== null && (
                  <div className="bg-slate-50 p-6 rounded-lg border border-slate-200">
                    <h3 className="text-lg font-semibold text-slate-900 mb-3">Sentiment Distribution</h3>
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-green-700 font-medium">Bullish</span>
                          <span className="text-slate-600 font-mono">{summaryData.bullish_percentage.toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-slate-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full transition-all"
                            style={{ width: `${summaryData.bullish_percentage}%` }}
                          ></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-red-700 font-medium">Bearish</span>
                          <span className="text-slate-600 font-mono">{summaryData.bearish_percentage.toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-slate-200 rounded-full h-2">
                          <div
                            className="bg-red-600 h-2 rounded-full transition-all"
                            style={{ width: `${summaryData.bearish_percentage}%` }}
                          ></div>
                        </div>
                      </div>
                      {summaryData.neutral_percentage !== null && (
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-slate-700 font-medium">Neutral</span>
                            <span className="text-slate-600 font-mono">{summaryData.neutral_percentage.toFixed(1)}%</span>
                          </div>
                          <div className="w-full bg-slate-200 rounded-full h-2">
                            <div
                              className="bg-slate-600 h-2 rounded-full transition-all"
                              style={{ width: `${summaryData.neutral_percentage}%` }}
                            ></div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Recent Articles Preview */}
                {summaryData.recent_articles.length > 0 && (
                  <div className="bg-slate-50 p-6 rounded-lg border border-slate-200">
                    <h3 className="text-lg font-semibold text-slate-900 mb-3">Recent Headlines</h3>
                    <div className="space-y-2">
                      {summaryData.recent_articles.map((article, index) => (
                        <div key={index} className="flex items-start gap-2 text-sm">
                          <span className="text-teal-700 font-semibold">•</span>
                          <span className="text-slate-700 text-pretty">{article.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Summary Footer */}
              <div className="p-6 border-t border-slate-200 flex justify-end bg-slate-50">
                <button
                  onClick={closeSummary}
                  className="px-6 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition-all font-medium shadow-sm"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default SentimentPage;
