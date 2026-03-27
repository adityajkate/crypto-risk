/**
 * Enhanced API Client with retry logic, timeout, and request cancellation
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const REQUEST_TIMEOUT = parseInt(import.meta.env.VITE_REQUEST_TIMEOUT || '30000');
const MAX_RETRIES = parseInt(import.meta.env.VITE_MAX_RETRIES || '3');
const RETRY_DELAY_BASE = 1000; // 1 second

interface RequestOptions {
  timeout?: number;
  retries?: number;
  signal?: AbortSignal;
}

interface ApiResponse<T> {
  success: boolean;
  data: T;
  timestamp: string;
}

// Type definitions
export interface PriceData {
  id: string;
  symbol: string;
  name: string;
  image?: string | null;
  current_price: number;
  market_cap: number;
  total_volume: number;
  price_change_24h: number;
  price_change_percentage_24h: number;
  market_cap_rank: number;
  circulating_supply: number;
  total_supply: number;
  ath: number;
  atl: number;
  last_updated: string;
}

export interface RiskAnalysis {
  risk_assessment: {
    risk_level: number;
    risk_label: string;
    confidence: number;
    risk_score?: number;
    probabilities?: {
      low: number;
      medium: number;
      high: number;
    };
    features?: {
      volatility_30d: number;
      rsi_14: number;
      drawdown: number;
      returns_1d: number;
    };
  };
  volatility_forecast?: {
    predicted_volatility_7d?: number;
    predicted_volatility?: number;
    current_volatility_7d?: number;
  };
  market_cluster?: {
    cluster_id: number;
    cluster_name: string;
  };
  market_regime?: {
    regime: string;
  };
}

export interface CoinAnalysis {
  coin_id: string;
  current_price: {
    id: string;
    symbol: string;
    name: string;
    image?: string | null;
    current_price: number;
    market_cap: number;
    total_volume: number;
    price_change_24h: number;
    price_change_percentage_24h: number;
    market_cap_rank: number;
    circulating_supply: number;
    total_supply: number;
    ath: number;
    atl: number;
    last_updated: string;
  };
  risk_analysis: RiskAnalysis;
  data_points: number;
  analysis_period_days: number;
}

export interface TrendingCoin {
  id: string;
  name: string;
  symbol: string;
  market_cap_rank: number;
  price_btc: number;
}

export interface GlobalMarket {
  total_market_cap: number;
  total_volume: number;
  market_cap_change_percentage_24h: number;
  active_cryptocurrencies: number;
}

export interface TechnicalIndicators {
  momentum_indicators: {
    rsi_14: number;
    stoch_rsi: number;
    macd: number;
    macd_signal: number;
    macd_hist: number;
    momentum: number;
    roc: number;
  };
  trend_indicators: {
    adx: number;
    aroon_osc: number;
    cci: number;
    trix: number;
  };
  volatility_indicators: {
    atr_14: number;
    bb_width: number;
    bb_upper: number;
    bb_lower: number;
    volatility_7d: number;
    volatility_30d: number;
  };
  volume_indicators: {
    obv: number;
    mfi: number;
    volume_sma_ratio: number;
  };
  oscillators: {
    willr: number;
    ultosc: number;
    bop: number;
  };
  price_action: {
    drawdown: number;
    max_drawdown_30d: number;
    price_sma50_ratio: number;
    returns_1d: number;
  };
}

class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public userMessage?: string,
    public isAborted: boolean = false
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class EnhancedApiClient {
  private requestCache = new Map<string, Promise<any>>();
  private abortControllers = new Map<string, AbortController>();

  /**
   * Fetch with retry logic, timeout, and request deduplication
   */
  private async fetchWithRetry<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const {
      timeout = REQUEST_TIMEOUT,
      retries = MAX_RETRIES,
      signal
    } = options;

    const cacheKey = endpoint;

    // Request deduplication - return existing promise if same request is in flight
    if (this.requestCache.has(cacheKey)) {
      return this.requestCache.get(cacheKey);
    }

    const requestPromise = this.executeRequest<T>(endpoint, timeout, retries, signal);
    this.requestCache.set(cacheKey, requestPromise);

    try {
      const result = await requestPromise;
      return result;
    } finally {
      // Clean up cache after request completes
      this.requestCache.delete(cacheKey);
    }
  }

  private async executeRequest<T>(
    endpoint: string,
    timeout: number,
    retries: number,
    externalSignal?: AbortSignal
  ): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
      // Create AbortController for this attempt
      const controller = new AbortController();
      const requestId = `${endpoint}-${Date.now()}`;
      this.abortControllers.set(requestId, controller);

      // Combine external signal with timeout
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      // If external signal is aborted, abort this request too
      if (externalSignal) {
        externalSignal.addEventListener('abort', () => controller.abort());
      }

      try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
          },
        });

        clearTimeout(timeoutId);
        this.abortControllers.delete(requestId);

        if (!response.ok) {
          throw new ApiError(
            `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            this.getUserFriendlyMessage(response.status)
          );
        }

        const result: ApiResponse<T> = await response.json();
        return result.data;

      } catch (error) {
        clearTimeout(timeoutId);
        this.abortControllers.delete(requestId);

        // Don't retry if request was cancelled
        if (error instanceof Error && error.name === 'AbortError') {
          if (externalSignal?.aborted) {
            throw new ApiError('Request cancelled', undefined, 'Request was cancelled', true);
          }
          throw new ApiError('Request timeout', 408, 'Request took too long. Please try again.', false);
        }

        lastError = error as Error;

        // Don't retry on client errors (4xx except 408, 429)
        if (error instanceof ApiError && error.statusCode) {
          if (error.statusCode >= 400 && error.statusCode < 500 &&
              error.statusCode !== 408 && error.statusCode !== 429) {
            throw error;
          }
        }

        // If this was the last attempt, throw the error
        if (attempt === retries) {
          break;
        }

        // Exponential backoff: 1s, 2s, 4s
        const delay = RETRY_DELAY_BASE * Math.pow(2, attempt);
        await this.sleep(delay);
      }
    }

    // All retries failed
    throw new ApiError(
      lastError?.message || 'Request failed after retries',
      undefined,
      'Connection failed. Please check your internet and try again.'
    );
  }

  private getUserFriendlyMessage(statusCode: number): string {
    switch (statusCode) {
      case 400:
        return 'Invalid request. Please check your input.';
      case 401:
        return 'Authentication required.';
      case 403:
        return 'Access denied.';
      case 404:
        return 'Resource not found. Try a different coin symbol.';
      case 429:
        return 'Too many requests. Please wait a moment.';
      case 500:
        return 'Server error. Retrying automatically...';
      case 503:
        return 'Service temporarily unavailable. Please try again later.';
      default:
        return 'An error occurred. Please try again.';
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Cancel all pending requests
   */
  public cancelAll(): void {
    this.abortControllers.forEach(controller => controller.abort());
    this.abortControllers.clear();
    this.requestCache.clear();
  }

  /**
   * Cancel a specific request by endpoint
   */
  public cancel(endpoint: string): void {
    this.abortControllers.forEach((controller, key) => {
      if (key.startsWith(endpoint)) {
        controller.abort();
        this.abortControllers.delete(key);
      }
    });
    this.requestCache.delete(endpoint);
  }

  // API Methods

  async getCoinPrice(coinId: string, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/coin/${coinId}/price`, { signal });
  }

  async getCoinAnalysis(coinId: string, days: number = 30, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/coin/${coinId}/analysis?days=${days}`, { signal });
  }

  async getCoinRisk(coinId: string, days: number = 30, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/coin/${coinId}/risk?days=${days}`, { signal });
  }

  async getTrendingCoins(signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/trending`, { signal });
  }

  async getGlobalMarket(signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/global`, { signal });
  }

  async getSentiment(currency: string, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/sentiment/${currency}`, { signal });
  }

  async getIndicators(coinId: string, days: number = 30, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/coin/${coinId}/indicators?days=${days}`, { signal });
  }

  async getOHLC(coinId: string, days: number = 7, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/coin/${coinId}/ohlc?days=${days}`, { signal });
  }

  async getSentimentRaw(currency: string, limit: number = 100, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/sentiment/${currency}/raw?limit=${limit}`, { signal });
  }

  async getSentimentArticle(currency: string, articleId: string, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/sentiment/${currency}/article/${articleId}`, { signal });
  }

  async getSentimentSummary(currency: string, signal?: AbortSignal) {
    // NLP summarization can take longer than typical API calls
    return this.fetchWithRetry(`/api/v1/sentiment/${currency}/summary`, { signal, timeout: 60000 });
  }

  async searchCoins(query: string, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/coins/search?query=${encodeURIComponent(query)}`, { signal });
  }

  async getTopCoins(limit: number = 20, signal?: AbortSignal) {
    return this.fetchWithRetry(`/api/v1/coins/top?limit=${limit}`, { signal });
  }

  getImageProxyUrl(imageUrl: string): string {
    return `${API_BASE_URL}/api/v1/proxy/image?url=${encodeURIComponent(imageUrl)}`;
  }

  async healthCheck(signal?: AbortSignal) {
    const response = await fetch(`${API_BASE_URL}/health`, { signal });
    return response.json();
  }
}

export const apiClient = new EnhancedApiClient();
export { ApiError };
export type { ApiResponse };
