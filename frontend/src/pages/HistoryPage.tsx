import React from 'react';
import { GitCommit, AlertCircle, TrendingUp } from 'lucide-react';
import { useCrypto } from '../context/CryptoContext';

const HistoryPage: React.FC = () => {
  const { currency, analysis, priceData, loading, error } = useCrypto();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading pattern data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="text-red-400 mx-auto mb-4" size={48} />
          <p className="text-red-400 font-semibold mb-2">Failed to load pattern data</p>
          <p className="text-slate-400 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header>
         <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <GitCommit className="text-cyan-400" />
            Pattern Recognition: <span className="text-slate-300">{currency}</span>
         </h1>
         <p className="text-slate-400 mt-2 max-w-2xl">
            Historical pattern analysis and fractal projection models.
         </p>
      </header>

      {/* Feature Coming Soon Card */}
      <div className="glass-panel p-8 rounded-xl border border-slate-800 text-center">
        <div className="max-w-2xl mx-auto">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-cyan-500/10 border border-cyan-500/20 mb-6">
            <TrendingUp className="text-cyan-400" size={32} />
          </div>

          <h2 className="text-2xl font-bold text-white mb-4">
            Fractal Pattern Recognition Coming Soon
          </h2>

          <p className="text-slate-400 text-lg leading-relaxed mb-6">
            Advanced pattern recognition and fractal projection models are currently in development.
            This feature will overlay current market structure against historical fractals to forecast probable price action.
          </p>

          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 text-left">
            <h3 className="text-white font-semibold mb-3">Planned Features:</h3>
            <ul className="space-y-2 text-slate-300 text-sm">
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-1">•</span>
                <span>Historical cycle matching algorithm with similarity scoring</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-1">•</span>
                <span>Fractal projection models based on past market cycles (2013, 2017, 2020)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-1">•</span>
                <span>Multi-timeframe pattern correlation analysis</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-1">•</span>
                <span>Price action forecasting with confidence intervals</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-1">•</span>
                <span>Change-point detection using PELT algorithm</span>
              </li>
            </ul>
          </div>

          <div className="mt-6 text-sm text-slate-500">
            This feature requires additional backend infrastructure for pattern matching and time-series analysis.
          </div>
        </div>
      </div>

      {/* Current Market Regime Info */}
      {analysis?.risk_analysis?.market_regime && (
        <div className="glass-panel p-6 rounded-xl border border-slate-800">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Current Market Regime</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-800/30 p-4 rounded-lg border border-slate-700">
              <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-2">
                Regime State
              </div>
              <div className="text-xl font-bold text-cyan-400">
                {analysis.risk_analysis.market_regime.regime_name || 'Unknown'}
              </div>
            </div>
            <div className="bg-slate-800/30 p-4 rounded-lg border border-slate-700">
              <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-2">
                Description
              </div>
              <div className="text-sm text-slate-300">
                {analysis.risk_analysis.market_regime.description || 'No description available'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HistoryPage;
