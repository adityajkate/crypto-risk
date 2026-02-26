const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  timestamp: string;
}

export interface PriceData {
  current_price: number;
  market_cap: number;
  total_volume: number;
  price_change_24h: number;
  price_change_percentage_24h: number;
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
  current_price: PriceData;
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

export interface NewsPost {
  title: string;
  url: string;
  published_at: string;
  source: string;
  currencies: string[];
  votes: {
    positive: number;
    negative: number;
  };
}

export interface SentimentData {
  currency: string;
  sentiment_score: number;
  bullish_count?: number;
  bearish_count?: number;
  important_count?: number;
  positive_count?: number;
  negative_count?: number;
  neutral_count?: number;
  total_posts?: number;
  total_positive_votes?: number;
  total_negative_votes?: number;
  recent_posts?: NewsPost[];
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

class ApiService {
  private async fetchApi<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    const result: ApiResponse<T> = await response.json();
    return result.data;
  }

  async getCoinPrice(coinId: string): Promise<PriceData> {
    return this.fetchApi<PriceData>(`/api/v1/coin/${coinId}/price`);
  }

  async getCoinAnalysis(coinId: string, days: number = 30): Promise<CoinAnalysis> {
    return this.fetchApi<CoinAnalysis>(`/api/v1/coin/${coinId}/analysis?days=${days}`);
  }

  async getCoinRisk(coinId: string, days: number = 30): Promise<{ coin_id: string; risk_assessment: RiskAnalysis['risk_assessment'] }> {
    return this.fetchApi(`/api/v1/coin/${coinId}/risk?days=${days}`);
  }

  async getTrendingCoins(): Promise<{ trending_coins: TrendingCoin[]; count: number }> {
    return this.fetchApi(`/api/v1/trending`);
  }

  async getGlobalMarket(): Promise<GlobalMarket> {
    return this.fetchApi<GlobalMarket>(`/api/v1/global`);
  }

  async getNews(currencies?: string, filterType: string = 'hot', limit: number = 20): Promise<{ posts: NewsPost[]; count: number; filter: string }> {
    const params = new URLSearchParams({ filter_type: filterType, limit: limit.toString() });
    if (currencies) params.append('currencies', currencies);
    return this.fetchApi(`/api/v1/news?${params.toString()}`);
  }

  async getSentiment(currency: string): Promise<SentimentData> {
    return this.fetchApi<SentimentData>(`/api/v1/sentiment/${currency}`);
  }

  async getIndicators(coinId: string, days: number = 30): Promise<{ coin_id: string; indicators: TechnicalIndicators; timestamp: string }> {
    return this.fetchApi(`/api/v1/coin/${coinId}/indicators?days=${days}`);
  }

  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  }

  async getMarketChart(coinId: string, days: number = 7): Promise<{ prices: number[][]; volumes: number[][] }> {
    const response = await fetch(
      `https://api.coingecko.com/api/v3/coins/${coinId}/market_chart?vs_currency=usd&days=${days}`
    );
    return response.json();
  }
}

export const apiService = new ApiService();
