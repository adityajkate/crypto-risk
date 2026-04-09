import React, { useState, useMemo, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { ArrowUpRight, ArrowDownRight, TrendingUp, AlertTriangle, Zap, DollarSign, Activity, BarChart3, Shield } from 'lucide-react';
import RiskGauge from '../components/RiskGauge';
import CoinSearch from '../components/CoinSearch';
import PriceChart from '../components/PriceChart';
import IndicatorTooltip from '../components/IndicatorTooltip';
import { useCrypto } from '../context/CryptoContext';
import { apiClient, TechnicalIndicators } from '../services/apiClient';
import { formatLargeNumber, formatPercentage, formatPrice, formatDecimal, formatIndicator } from '../utils/formatters';

const Dashboard: React.FC = () => {
  const { currency, coinId, setCurrency, setCoinId, analysis, priceData: apiPriceData, loading, error } = useCrypto();
  const [indicators, setIndicators] = useState<TechnicalIndicators | null>(null);
  const [logoError, setLogoError] = useState(false);
  const [hideLogo, setHideLogo] = useState(false);

  // Debug logging
  console.log('Dashboard render:', {
    loading,
    hasApiPriceData: !!apiPriceData,
    hasAnalysis: !!analysis,
    apiPriceData,
    analysis
  });

  // Prefer CoinGecko image from API; fallback to symbol-based icon CDN.
  const symbol = apiPriceData?.symbol?.toLowerCase();
  const fallbackLogo = symbol ? `https://assets.coincap.io/assets/icons/${symbol}@2x.png` : '';
  const coinLogo = logoError ? fallbackLogo : (apiPriceData?.image || fallbackLogo);

  // Reset logo error when coin changes
  React.useEffect(() => {
    setLogoError(false);
    setHideLogo(false);
  }, [coinId]);

  // Fetch technical indicators
  useEffect(() => {
    const fetchIndicators = async () => {
      try {
        const data = await apiClient.getIndicators(coinId, 30);
        if (data.indicators) {
          setIndicators(data.indicators);
        }
      } catch (error) {
        console.error('Failed to fetch indicators:', error);
      }
    };

    if (coinId) {
      fetchIndicators();
    }
  }, [coinId]);

  const handleCoinSelect = (id: string, name: string) => {
    setCurrency(name);
    setCoinId(id);
  };

  // Risk distribution data from backend
  const distributionData = useMemo(() => {
    const probs = analysis?.risk_analysis?.risk_assessment?.probabilities;
    return probs ? [
      { name: 'Low Risk', value: probs.low * 100, color: '#10b981' },
      { name: 'Medium Risk', value: probs.medium * 100, color: '#f59e0b' },
      { name: 'High Risk', value: probs.high * 100, color: '#ef4444' }
    ].filter(item => item.value > 0) : [];
  }, [analysis]);

  // Extract real data from API
  const basePrice = apiPriceData?.current_price || 0;
  const riskScore = analysis?.risk_analysis?.risk_assessment?.risk_score
    || (analysis?.risk_analysis?.risk_assessment?.probabilities?.high || 0) * 100
    || 0;
  const isPositive = (apiPriceData?.price_change_percentage_24h || 0) > 0;
  const priceChange24h = apiPriceData?.price_change_percentage_24h?.toFixed(2) || '0.00';
  const volatility = (analysis?.risk_analysis?.volatility_forecast?.predicted_volatility_7d
    || analysis?.risk_analysis?.volatility_forecast?.predicted_volatility
    || analysis?.risk_analysis?.risk_assessment?.features?.volatility_30d
    || 0) * 100;

  const getRegime = (score: number) => {
    if (score < 30) return { label: 'Stable', color: 'text-emerald-600' };
    if (score < 70) return { label: 'Speculative', color: 'text-yellow-600' };
    return { label: 'High Risk', color: 'text-red-600' };
  };

  const regime = getRegime(riskScore);

  if (loading && !apiPriceData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading market data...</p>
        </div>
      </div>
    );
  }

  if (error && !apiPriceData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertTriangle className="text-red-500 mx-auto mb-4" size={48} />
          <p className="text-red-600 font-semibold mb-2">Failed to load data</p>
          <p className="text-slate-600 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  // Don't render if we don't have price data
  if (!apiPriceData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading market data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {coinLogo && !hideLogo && (
            <img
              src={coinLogo}
              alt={currency}
              className="w-10 h-10 sm:w-12 sm:h-12 rounded-full border-2 border-slate-200"
              onError={() => {
                if (!logoError && fallbackLogo && coinLogo !== fallbackLogo) {
                  setLogoError(true);
                  return;
                }
                setHideLogo(true);
              }}
            />
          )}
          <div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-slate-900">Market Overview</h1>
            <p className="text-slate-600 text-xs sm:text-sm mt-1">
              Real-time analysis for <span className="text-teal-700 font-semibold">{currency}</span>
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center w-full lg:w-auto">
          <CoinSearch onSelectCoin={handleCoinSelect} />

          <div className="flex items-center justify-center sm:justify-start">
            <span className="inline-flex px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200 items-center gap-2">
              <svg className="w-2 h-2" viewBox="0 0 8 8" fill="currentColor">
                <circle cx="4" cy="4" r="4" />
              </svg>
              Live
            </span>
          </div>
        </div>
      </header>

      {/* Price Analytics Section */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Price Analytics</h2>

        {/* Top Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label={`${currency} Price`}
            value={formatPrice(basePrice)}
            change={`${isPositive ? '+' : ''}${formatPercentage(parseFloat(priceChange24h))}`}
            isPositive={isPositive}
            icon={<DollarSign size={20} />}
            iconBg="bg-teal-50"
            iconColor="text-teal-700"
          />
          <StatCard
            label="24h Volume"
            value={formatLargeNumber(apiPriceData?.total_volume || 0)}
            change={`${formatPercentage((apiPriceData?.total_volume || 0) / (apiPriceData?.market_cap || 1) * 100)} of cap`}
            isPositive={true}
            icon={<BarChart3 size={20} />}
            iconBg="bg-teal-50"
            iconColor="text-teal-700"
          />
          <StatCard
            label="Market Cap"
            value={formatLargeNumber(apiPriceData?.market_cap || 0)}
            change={`Rank #${apiPriceData?.market_cap_rank || 'N/A'}`}
            isPositive={true}
            icon={<TrendingUp size={20} />}
            iconBg="bg-teal-50"
            iconColor="text-teal-700"
          />
          <StatCard
            label="Volatility (7d)"
            value={formatPercentage(volatility)}
            change={volatility > 10 ? 'High' : volatility > 5 ? 'Medium' : 'Low'}
            isPositive={volatility < 5}
            icon={<Activity size={20} />}
            iconBg="bg-teal-50"
            iconColor="text-teal-700"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Main Price Chart */}
        <div className="lg:col-span-2 bg-white rounded-lg p-5 card-shadow">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-5">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">{currency}/USD Price Chart</h3>
              <p className="text-sm text-slate-500 mt-1">7-day historical price movement</p>
            </div>
          </div>
          <PriceChart coinId={coinId} currentPrice={basePrice} />
        </div>

        {/* Risk Analytics Section */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Risk Analytics</h2>

          {/* Risk Gauge */}
          <div className="bg-white rounded-lg p-5 card-shadow flex flex-col items-center justify-center">
            <h3 className="text-lg font-semibold text-slate-900 w-full mb-2">Current Risk Level</h3>
            <RiskGauge value={riskScore} label={regime.label} />
            <div className="mt-6 w-full">
              <div className="text-center mb-4">
                <div className="text-3xl font-bold text-slate-900 mb-1 font-mono">{Math.round(riskScore)}<span className="text-lg text-slate-500">/100</span></div>
                <div className={`text-base font-semibold ${regime.color} mb-2`}>{regime.label}</div>
                <p className="text-sm text-slate-600 leading-relaxed">
                  {regime.label === 'Stable'
                    ? 'Low volatility, strong liquidity, neutral sentiment.'
                    : regime.label === 'Speculative'
                    ? 'Moderate volatility, mixed signals, elevated caution.'
                    : 'High volatility, weak liquidity, negative sentiment.'}
                </p>
              </div>
            </div>
          </div>

          {/* Risk Distribution */}
          {distributionData.length > 0 && (
            <div className="bg-white rounded-lg p-5 card-shadow">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Risk Distribution</h3>
              <div className="h-[160px] flex items-center justify-center relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={distributionData}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={70}
                      startAngle={90}
                      endAngle={-270}
                      dataKey="value"
                    >
                      {distributionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => `${formatPercentage(value, 1)}`} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="text-center">
                    <div className="text-xs text-slate-500 font-medium">Dominant</div>
                    <div className="text-sm font-bold text-slate-900">
                      {distributionData.reduce((max, item) => item.value > max.value ? item : max).name.replace(' Risk', '')}
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-4 space-y-3">
                {distributionData.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="text-slate-700 font-medium">{item.name}</span>
                    </div>
                    <span className="font-bold text-slate-900 font-mono">{formatPercentage(item.value, 1)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Technical Indicators */}
      {indicators && (
        <div className="bg-white rounded-lg p-5 card-shadow">
          <div className="mb-5">
            <h3 className="text-lg font-semibold text-slate-900">Technical Indicators</h3>
            <p className="text-sm text-slate-500 mt-1">TA-Lib powered analysis</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Momentum Indicators */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-200">Momentum</h4>
              <IndicatorRow label="RSI (14)" value={formatDecimal(indicators.momentum_indicators.rsi_14, 2)} tooltip="Relative Strength Index: Measures momentum on a scale of 0-100. Below 30 is oversold, above 70 is overbought." />
              <IndicatorRow label="Stochastic RSI" value={formatDecimal(indicators.momentum_indicators.stoch_rsi, 2)} tooltip="Stochastic RSI: More sensitive version of RSI. Values above 0.8 indicate overbought, below 0.2 indicate oversold." />
              <IndicatorRow label="MACD" value={formatDecimal(indicators.momentum_indicators.macd, 2)} tooltip="Moving Average Convergence Divergence: Shows relationship between two moving averages. Positive values suggest upward momentum." />
              <IndicatorRow label="MACD Signal" value={formatDecimal(indicators.momentum_indicators.macd_signal, 2)} tooltip="MACD Signal Line: 9-day EMA of MACD. Crossovers with MACD line indicate potential buy/sell signals." />
              <IndicatorRow label="MACD Histogram" value={formatDecimal(indicators.momentum_indicators.macd_hist, 2)} tooltip="MACD Histogram: Difference between MACD and signal line. Shows momentum strength and potential reversals." />
              <IndicatorRow label="Momentum" value={formatDecimal(indicators.momentum_indicators.momentum, 2)} tooltip="Rate of Change: Measures speed of price movement. Positive values indicate upward momentum." />
              <IndicatorRow label="ROC" value={formatDecimal(indicators.momentum_indicators.roc, 2)} tooltip="Rate of Change: Percentage change in price over a period. Helps identify overbought/oversold conditions." />
            </div>

            {/* Trend Indicators */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-200">Trend</h4>
              <IndicatorRow label="ADX" value={formatDecimal(indicators.trend_indicators.adx, 2)} />
              <IndicatorRow label="Aroon Oscillator" value={formatDecimal(indicators.trend_indicators.aroon_osc, 2)} />
              <IndicatorRow label="CCI" value={formatDecimal(indicators.trend_indicators.cci, 2)} />
              <IndicatorRow label="TRIX" value={formatDecimal(indicators.trend_indicators.trix, 4)} />
            </div>

            {/* Volatility Indicators */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-200">Volatility</h4>
              <IndicatorRow label="ATR (14)" value={formatDecimal(indicators.volatility_indicators.atr_14, 2)} tooltip="Average True Range: Measures market volatility. Higher values indicate greater price volatility." />
              <IndicatorRow label="BB Width" value={formatDecimal(indicators.volatility_indicators.bb_width, 4)} tooltip="Bollinger Band Width: Measures the distance between upper and lower bands. Wider bands indicate higher volatility." />
              <IndicatorRow label="Volatility (7d)" value={formatPercentage(indicators.volatility_indicators.volatility_7d * 100, 2)} tooltip="7-Day Volatility: Standard deviation of returns over 7 days. Higher values indicate more price fluctuation." />
              <IndicatorRow label="Volatility (30d)" value={formatPercentage(indicators.volatility_indicators.volatility_30d * 100, 2)} tooltip="30-Day Volatility: Standard deviation of returns over 30 days. Provides longer-term volatility perspective." />
            </div>

            {/* Volume Indicators */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-200">Volume</h4>
              <IndicatorRow label="OBV" value={formatLargeNumber(indicators.volume_indicators.obv)} tooltip="On-Balance Volume: Cumulative volume indicator. Rising OBV suggests buying pressure, falling suggests selling pressure." />
              <IndicatorRow label="MFI" value={formatDecimal(indicators.volume_indicators.mfi, 2)} tooltip="Money Flow Index: Volume-weighted RSI. Above 80 is overbought, below 20 is oversold." />
              <IndicatorRow label="Volume SMA Ratio" value={formatDecimal(indicators.volume_indicators.volume_sma_ratio, 2)} tooltip="Volume to SMA Ratio: Current volume compared to average. Values above 1 indicate higher than average volume." />
            </div>

            {/* Oscillators */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-200">Oscillators</h4>
              <IndicatorRow label="Williams %R" value={formatDecimal(indicators.oscillators.willr, 2)} />
              <IndicatorRow label="Ultimate Oscillator" value={formatDecimal(indicators.oscillators.ultosc, 2)} />
              <IndicatorRow label="Balance of Power" value={formatDecimal(indicators.oscillators.bop, 4)} />
            </div>

            {/* Price Action */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-200">Price Action</h4>
              <IndicatorRow label="Drawdown" value={formatPercentage(indicators.price_action.drawdown, 2)} />
              <IndicatorRow label="Max Drawdown (30d)" value={formatPercentage(indicators.price_action.max_drawdown_30d, 2)} />
              <IndicatorRow label="Price/SMA50 Ratio" value={formatDecimal(indicators.price_action.price_sma50_ratio, 4)} />
              <IndicatorRow label="Returns (1d)" value={formatPercentage(indicators.price_action.returns_1d, 2)} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const IndicatorRow: React.FC<{ label: string; value: string; tooltip?: string }> = ({ label, value, tooltip }) => (
  <div className="flex justify-between items-center text-sm gap-4">
    <span className="text-slate-500 flex items-center">
      {tooltip ? (
        <IndicatorTooltip label={label} description={tooltip} />
      ) : (
        label
      )}
    </span>
    <span className="font-semibold text-slate-900 font-mono tabular-nums">{value}</span>
  </div>
);

interface StatCardProps {
  label: string;
  value: string;
  change: string;
  isPositive: boolean;
  icon: React.ReactNode;
  iconBg?: string;
  iconColor?: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, change, isPositive, icon, iconBg = 'bg-slate-100', iconColor = 'text-slate-600' }) => (
  <div className="bg-white p-4 rounded-lg card-shadow card-shadow-hover">
    <div className="flex justify-between items-start mb-2">
      <span className="text-slate-500 text-sm font-medium">{label}</span>
      <span className={`p-2 rounded-lg ${iconBg} ${iconColor}`}>
        {icon}
      </span>
    </div>
    <div className="mb-2">
      <span className="text-2xl font-bold text-slate-900 font-mono tabular-nums">{value}</span>
    </div>
    <div className="flex items-center text-sm font-medium">
      {change.includes('%') && (isPositive ? <ArrowUpRight size={14} className="mr-1"/> : <ArrowDownRight size={14} className="mr-1"/>)}
      <span className={change.includes('%') ? (isPositive ? 'text-emerald-600 font-mono tabular-nums' : 'text-red-600 font-mono tabular-nums') : 'text-slate-500 tabular-nums'}>{change}</span>
    </div>
  </div>
);

export default Dashboard;
