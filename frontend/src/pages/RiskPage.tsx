import React, { useMemo, useState, useEffect } from 'react';
import { ResponsiveContainer, AreaChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import { AlertCircle, Shield, Info } from 'lucide-react';
import { useCrypto } from '../context/CryptoContext';

const RiskPage: React.FC = () => {
  const { currency, analysis, priceData, loading, error } = useCrypto();

  // Extract real volatility data from backend
  const volatilityData = useMemo(() => {
    const predicted = analysis?.risk_analysis?.volatility_forecast?.predicted_volatility_7d || 0;
    const current7d = analysis?.risk_analysis?.volatility_forecast?.current_volatility_7d || 0;
    const current30d = analysis?.risk_analysis?.volatility_forecast?.current_volatility_30d || 0;

    if (!predicted && !current7d && !current30d) {
      return null;
    }

    // Create a simple 3-point chart showing current and predicted volatility
    return [
      {
        label: 'Current (7d)',
        volatility: (current7d * 100).toFixed(2)
      },
      {
        label: 'Current (30d)',
        volatility: (current30d * 100).toFixed(2)
      },
      {
        label: 'Predicted (7d)',
        volatility: (predicted * 100).toFixed(2)
      }
    ];
  }, [analysis]);

  // Extract real risk factors from backend
  const riskFactors = useMemo(() => {
    if (!analysis?.risk_analysis?.risk_assessment) return null;

    const features = analysis.risk_analysis.risk_assessment.features;
    if (!features) return null;

    return [
      {
        name: 'Volatility Risk',
        score: Math.min((features.volatility_30d || 0) * 1000, 100),
        value: `${((features.volatility_30d || 0) * 100).toFixed(2)}%`,
        desc: '30-day realized volatility indicates price instability.'
      },
      {
        name: 'Drawdown Risk',
        score: Math.min(Math.abs(features.drawdown || 0), 100),
        value: `${(features.drawdown || 0).toFixed(2)}%`,
        desc: 'Current drawdown from all-time high.'
      },
      {
        name: 'Momentum Risk',
        score: Math.min(Math.abs(features.returns_1d || 0) * 10, 100),
        value: `${(features.returns_1d || 0).toFixed(2)}%`,
        desc: '1-day price change indicates short-term momentum.'
      },
      {
        name: 'RSI Indicator',
        score: Math.abs((features.rsi_14 || 50) - 50) * 2,
        value: (features.rsi_14 || 0).toFixed(2),
        desc: 'RSI above 70 is overbought, below 30 is oversold.'
      }
    ];
  }, [analysis]);

  // Determine alert level based on real risk score
  const alertLevel = useMemo(() => {
    const riskScore = analysis?.risk_analysis?.risk_assessment?.risk_score
      || (analysis?.risk_analysis?.risk_assessment?.probabilities?.high || 0) * 100
      || 0;
    return riskScore > 70 ? 2 : riskScore > 50 ? 1 : 0;
  }, [analysis]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading risk data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="text-red-400 mx-auto mb-4" size={48} />
          <p className="text-red-400 font-semibold mb-2">Failed to load risk data</p>
          <p className="text-slate-400 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 relative">
      <header>
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Shield className="text-cyan-400" />
          Risk & Volatility Insights: <span className="text-slate-300">{currency}</span>
        </h1>
        <p className="text-slate-400 mt-2 max-w-2xl">
          Real-time risk analysis powered by machine learning models trained on historical market data.
        </p>
      </header>

      {/* Volatility Metrics */}
      {volatilityData && (
        <div className="glass-panel p-6 rounded-xl border border-slate-800">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                Volatility Metrics
                <div className="group relative">
                  <Info size={14} className="text-slate-500 cursor-help" />
                  <div className="absolute left-0 bottom-full mb-2 w-64 p-2 bg-slate-900 border border-slate-700 rounded text-xs text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    Volatility measures the degree of price variation. Higher volatility indicates greater risk and uncertainty.
                  </div>
                </div>
              </h3>
              <p className="text-sm text-slate-400 mt-1">
                Current and predicted volatility from ML models
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {volatilityData.map((item, idx) => (
              <div key={idx} className="bg-slate-800/30 p-4 rounded-lg border border-slate-700">
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-2">
                  {item.label}
                </div>
                <div className="text-2xl font-bold text-white">{item.volatility}%</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk Factors Grid */}
      {riskFactors && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {riskFactors.map((factor) => (
            <div key={factor.name} className="glass-panel p-5 rounded-xl border-l-4 border-l-transparent hover:border-l-cyan-500 transition-all group">
              <div className="flex justify-between items-start mb-3">
                <h4 className="font-bold text-slate-200 group-hover:text-cyan-400 transition-colors">{factor.name}</h4>
                <span className="text-xs font-mono text-cyan-400">{factor.value}</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mb-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ${factor.score > 70 ? 'bg-red-500' : factor.score > 40 ? 'bg-yellow-500' : 'bg-emerald-500'}`}
                  style={{ width: `${Math.min(factor.score, 100)}%` }}
                />
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{factor.desc}</p>
            </div>
          ))}
        </div>
      )}

      {/* Alert Section */}
      {alertLevel > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center gap-4 transition-all hover:bg-red-500/15">
          <div className="p-3 bg-red-500/20 rounded-full text-red-400 animate-pulse">
            <AlertCircle size={24} />
          </div>
          <div className="flex-1">
            <h4 className="text-lg font-bold text-red-200">High Risk Alert Detected for {currency}</h4>
            <p className="text-red-200/70 text-sm mt-1">
              The ML risk classifier has identified elevated risk levels based on technical indicators, volatility patterns, and market regime analysis.
            </p>
          </div>
        </div>
      )}

      {/* Data Unavailable Notice */}
      <div className="bg-slate-800/30 border border-slate-700 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <Info className="text-slate-400 shrink-0 mt-1" size={20} />
          <div>
            <h4 className="text-slate-200 font-semibold mb-2">Additional Metrics Coming Soon</h4>
            <p className="text-slate-400 text-sm leading-relaxed">
              Advanced derivatives metrics (Open Interest, Liquidation Levels, Funding Rates, Long/Short Ratios)
              require integration with exchange APIs and are not yet available. Current risk analysis is based on
              spot market data and technical indicators.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskPage;
