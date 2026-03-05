import React, { useEffect, useState } from 'react';
import { MessageSquare, Twitter, Globe, TrendingUp, AlertCircle, Info, X, ExternalLink, Clock, ThumbsUp, FileText, Sparkles } from 'lucide-react';
import { useCrypto } from '../context/CryptoContext';
import { apiClient } from '../services/apiClient';

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
}

interface SentimentMetrics {
  weighted_event_score: number;
  total_mentions: number;
  layer_a_weight: number;
  layer_b_weight: number;
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
  key_topics: string[];
  sentiment: string;
  event_score: number;
  recent_articles: Article[];
}

const SentimentPage: React.FC = () => {
  const { currency, coinId, loading: contextLoading } = useCrypto();
  const [articles, setArticles] = useState<Article[]>([]);
  const [sentimentMetrics, setSentimentMetrics] = useState<SentimentMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    const fetchSentimentData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch sentiment metrics
        const metricsData = await apiClient.getSentiment(coinId, controller.signal);
        setSentimentMetrics(metricsData.global_metrics);

        // Fetch raw articles
        const articlesData = await apiClient.getSentimentRaw(coinId, 100, controller.signal);
        setArticles(articlesData.articles);

        // If no articles yet, show info message instead of error
        if (articlesData.articles.length === 0) {
          setError(null); // Clear any previous errors
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
    const interval = setInterval(fetchSentimentData, 30000);
    return () => {
      clearInterval(interval);
      controller.abort();
    };
  }, [coinId]);

  const handleArticleClick = (article: Article) => {
    setSelectedArticle(article);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedArticle(null);
  };

  const handleGenerateSummary = async () => {
    setLoadingSummary(true);
    try {
      const data = await apiClient.getSentimentSummary(coinId);
      setSummaryData(data);
      setShowSummary(true);
    } catch (err) {
      console.error('Error fetching summary:', err);
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

  if (loading || contextLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading real-time sentiment data...</p>
        </div>
      </div>
    );
  }

  if (error) {
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
    <div className="space-y-6">
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
                Generating...
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Generate Summary
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

      {/* Metrics Cards */}
      {sentimentMetrics && (
        <div>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Sentiment Metrics</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-lg card-shadow">
              <div className="text-slate-500 text-sm font-medium mb-2">Event Score</div>
              <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums">
                {sentimentMetrics.weighted_event_score.toFixed(2)}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg card-shadow">
              <div className="text-slate-500 text-sm font-medium mb-2">Total Mentions</div>
              <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums">
                {sentimentMetrics.total_mentions}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg card-shadow">
              <div className="text-slate-500 text-sm font-medium mb-2">Authoritative</div>
              <div className="text-2xl font-bold text-teal-700 font-mono tabular-nums">
                {(sentimentMetrics.layer_a_weight * 100).toFixed(0)}%
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg card-shadow">
              <div className="text-slate-500 text-sm font-medium mb-2">Social Signals</div>
              <div className="text-2xl font-bold text-cyan-700 font-mono tabular-nums">
                {(sentimentMetrics.layer_b_weight * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Articles Feed */}
      <div className="bg-white rounded-lg card-shadow p-5">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Live Feed</h2>
          <span className="text-sm text-slate-500">{articles.length} articles</span>
        </div>

        {articles.length === 0 ? (
          <div className="text-center py-12">
            <div className="animate-pulse mb-4">
              <MessageSquare className="text-teal-600 mx-auto mb-3" size={48} />
            </div>
            <p className="text-slate-900 font-semibold mb-2">Collecting data for {currency}...</p>
            <p className="text-slate-600 text-sm">
              Scrapers are now tracking this coin. Articles will appear within 5-15 minutes.
            </p>
            <p className="text-slate-500 text-xs mt-2">
              This page auto-refreshes every 30 seconds
            </p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
            {articles.map((article) => (
              <div
                key={article.id}
                onClick={() => handleArticleClick(article)}
                className="bg-slate-50 p-4 rounded-lg border border-slate-200 hover:border-teal-500 hover:shadow-sm transition-all cursor-pointer group"
              >
                <div className="flex gap-4">
                  {/* Article Image */}
                  {article.image_url && (
                    <div className="flex-shrink-0 w-32 h-24 rounded-lg overflow-hidden bg-slate-200">
                      <img
                        src={getProxiedImageUrl(article.image_url) || ''}
                        alt={article.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    </div>
                  )}

                  {/* Article Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        {getSourceIcon(article.platform_id)}
                        <span className="text-xs font-semibold text-slate-700 uppercase">
                          {article.source.replace('_', ' ')}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded border font-medium ${getSourceBadgeColor(article.source_type)}`}>
                          {article.source_type === 'layer_a' ? 'Authoritative' : 'Early Signal'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-slate-500 text-xs whitespace-nowrap">
                        <Clock size={12} />
                        {formatTimeAgo(article.timestamp)}
                      </div>
                    </div>

                    <h3 className="text-slate-900 font-semibold mb-1 group-hover:text-teal-700 transition-colors">
                      {article.title || article.summary.substring(0, 100)}
                    </h3>
                    <p className="text-slate-600 text-sm line-clamp-2">
                      {article.summary}
                    </p>

                    {article.engagement_count > 0 && (
                      <div className="flex items-center gap-1 mt-2 text-slate-500 text-xs">
                        <ThumbsUp size={12} />
                        <span>{article.engagement_count} engagement</span>
                      </div>
                    )}
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
                <div className="flex items-center gap-2 mb-2">
                  {getSourceIcon(selectedArticle.platform_id)}
                  <span className="text-sm font-semibold text-slate-700 uppercase">
                    {selectedArticle.source.replace('_', ' ')}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded border font-medium ${getSourceBadgeColor(selectedArticle.source_type)}`}>
                    {selectedArticle.source_type === 'layer_a' ? 'Authoritative' : 'Early Signal'}
                  </span>
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
                      {selectedArticle.engagement_count}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={closeModal}
                className="text-slate-400 hover:text-slate-900 transition-colors p-2"
              >
                <X size={24} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Article Image */}
              {selectedArticle.image_url && (
                <div className="mb-6 rounded-lg overflow-hidden">
                  <img
                    src={getProxiedImageUrl(selectedArticle.image_url) || ''}
                    alt={selectedArticle.title}
                    className="w-full max-h-96 object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                </div>
              )}

              <div className="prose prose-slate max-w-none">
                <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">
                  {selectedArticle.full_content}
                </p>
              </div>
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
                  <span>•</span>
                  <span className="capitalize">Sentiment: <span className={`font-semibold ${
                    summaryData.sentiment === 'bullish' ? 'text-emerald-600' :
                    summaryData.sentiment === 'bearish' ? 'text-red-600' :
                    'text-slate-700'
                  }`}>{summaryData.sentiment}</span></span>
                  <span>•</span>
                  <span>Event Score: <span className="font-semibold text-teal-700 font-mono">{summaryData.event_score.toFixed(2)}</span></span>
                </div>
              </div>
              <button
                onClick={closeSummary}
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
                <p className="text-slate-700 leading-relaxed">
                  {summaryData.summary}
                </p>
              </div>

              {/* Key Topics */}
              {summaryData.key_topics.length > 0 && (
                <div className="bg-slate-50 p-6 rounded-lg border border-slate-200">
                  <h3 className="text-lg font-semibold text-slate-900 mb-3">Key Topics</h3>
                  <div className="flex flex-wrap gap-2">
                    {summaryData.key_topics.map((topic, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-teal-50 text-teal-700 rounded-full text-sm border border-teal-200 font-medium"
                      >
                        {topic}
                      </span>
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

              {/* Recent Articles Preview */}
              {summaryData.recent_articles.length > 0 && (
                <div className="bg-slate-50 p-6 rounded-lg border border-slate-200">
                  <h3 className="text-lg font-semibold text-slate-900 mb-3">Recent Headlines</h3>
                  <div className="space-y-2">
                    {summaryData.recent_articles.map((article, index) => (
                      <div key={index} className="flex items-start gap-2 text-sm">
                        <span className="text-teal-700 font-semibold">•</span>
                        <span className="text-slate-700">{article.title}</span>
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
  );
};

export default SentimentPage;
