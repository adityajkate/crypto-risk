import React, { useMemo, useState } from 'react';
import { ResponsiveContainer, AreaChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import { AlertCircle, ArrowRight, Shield, Zap, X, Activity, TrendingDown, Target, Info } from 'lucide-react';
import { useCrypto } from '../context/CryptoContext';
import { getSeed } from '../utils/dataHelpers';

const RiskPage: React.FC = () => {
  const { currency, analysis, priceData, loading, error } = useCrypto();
  const [showModal, setShowModal] = useState(false);

  const { volatilityData, riskFactors, alertLevel, metrics, highVolThreshold } = useMemo(() => {
    const seed = getSeed(currency);

    // Use real volatility if available, otherwise use mock
    const realVolatility = (analysis?.risk_analysis?.volatility_forecast?.predicted_volatility_7d
      || analysis?.risk_analysis?.volatility_forecast?.predicted_volatility
      || analysis?.risk_analysis?.risk_assessment?.features?.volatility_30d
      || 0) * 100;
    const volBase = realVolatility > 0 ? realVolatility : (seed % 25) + 25;
    const highVolThreshold = volBase + 15;

    const vData = Array.from({ length: 30 }, (_, i) => {
      // Create smoother, more realistic curves
      const iv = volBase + Math.sin((i + seed) / 4) * 12 + (Math.random() * 2);
      const rv = (volBase - 5) + Math.cos((i + seed) / 5) * 8 + (Math.random() * 2);
      
      return {
        date: i === 29 ? 'Today' : `T-${29 - i}`,
        impliedVolatility: parseFloat(iv.toFixed(2)),
        realizedVolatility: parseFloat(rv.toFixed(2)),
        // Calculate the premium (IV - RV)
        premium: parseFloat((iv - rv).toFixed(2))
      };
    });

    const factors = [
      { name: 'Liquidity Risk', score: (seed % 40) + 20, status: 'Low', desc: 'Ability to exit positions without slippage.' },
      { name: 'Regulatory Risk', score: (seed % 60) + 20, status: 'High', desc: 'Exposure to upcoming policy changes.' },
      { name: 'Exchange Risk', score: (seed % 50) + 10, status: 'Medium', desc: 'Stability of centralized venues.' },
      { name: 'Macro Correlation', score: (seed % 70) + 20, status: 'Critical', desc: 'Sensitivity to traditional market moves.' },
    ];

    factors.forEach(f => {
      if(f.score < 30) f.status = 'Low';
      else if(f.score < 50) f.status = 'Medium';
      else if(f.score < 75) f.status = 'High';
      else f.status = 'Critical';
    });

    const mockPrice = priceData?.current_price || (seed % 50000) + 500;
    const metrics = {
        openInterest: ((seed % 200) + 50).toFixed(0),
        liquidationPrice: (mockPrice * 0.85).toLocaleString(undefined, {maximumFractionDigits: 2}),
        lsRatio: (0.5 + (seed % 40) / 100).toFixed(2),
        fundingRate: (0.01 + (seed % 5)/100).toFixed(4)
    };

    // Determine alert level based on real risk score
    const riskScore = analysis?.risk_analysis?.risk_assessment?.risk_score
      || (analysis?.risk_analysis?.risk_assessment?.probabilities?.high || 0) * 100
      || 0;
    const alertLevel = riskScore > 70 ? 2 : riskScore > 50 ? 1 : 0;

    return { volatilityData: vData, riskFactors: factors, alertLevel, metrics, highVolThreshold };
  }, [currency, analysis, priceData]);

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
          Deep dive into market stability. Compare what the market <em>expects</em> to happen (Implied) vs what is <em>actually</em> happening (Realized).
        </p>
      </header>

      {/* Main Volatility Chart */}
      <div className="glass-panel p-6 rounded-xl border border-slate-800">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
           <div>
             <h3 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
               Volatility Trend Analysis
               <div className="group relative">
                 <Info size={14} className="text-slate-500 cursor-help" />
                 <div className="absolute left-0 bottom-full mb-2 w-64 p-2 bg-slate-900 border border-slate-700 rounded text-xs text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    Implied Volatility (IV) represents the market's forecast of a likely movement. Realized Volatility (RV) is the actual historical movement.
                 </div>
               </div>
             </h3>
             <p className="text-sm text-slate-400 mt-1">
               <span className="text-purple-400 font-bold">Implied Volatility</span> (Forward-looking) vs <span className="text-cyan-400 font-bold">Realized Volatility</span> (Backward-looking)
             </p>
           </div>
           
           <div className="flex items-center gap-4 text-xs bg-slate-800/50 p-2 rounded-lg">
             <div className="flex items-center gap-2">
               <span className="w-3 h-3 rounded-sm bg-purple-500/50 border border-purple-500"></span>
               <span className="text-slate-300">Market Fear (IV)</span>
             </div>
             <div className="flex items-center gap-2">
               <span className="w-3 h-0.5 bg-cyan-400"></span>
               <span className="text-slate-300">Actual Moves (RV)</span>
             </div>
           </div>
        </div>

        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={volatilityData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorIV" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} minTickGap={30} />
              <YAxis 
                stroke="#64748b" 
                fontSize={12} 
                tickLine={false} 
                axisLine={false} 
                label={{ value: 'Annualized Volatility %', angle: -90, position: 'insideLeft', fill: '#64748b', style: { textAnchor: 'middle' } }} 
              />
              <Tooltip 
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl">
                        <p className="text-slate-300 text-xs mb-2">{label}</p>
                        <div className="space-y-1">
                          <p className="text-purple-400 text-sm font-bold flex justify-between gap-4">
                            <span>Implied (Expected):</span>
                            <span>{payload[0].value}%</span>
                          </p>
                          <p className="text-cyan-400 text-sm font-bold flex justify-between gap-4">
                            <span>Realized (Actual):</span>
                            <span>{payload[1].value}%</span>
                          </p>
                          <div className="border-t border-slate-700 my-1 pt-1">
                             <p className="text-slate-400 text-xs flex justify-between gap-4">
                               <span>Premium (Spread):</span>
                               <span className={(payload[0].payload.premium || 0) > 0 ? 'text-emerald-400' : 'text-red-400'}>
                                 {(payload[0].payload.premium || 0) > 0 ? '+' : ''}{payload[0].payload.premium}%
                               </span>
                             </p>
                          </div>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine y={highVolThreshold} stroke="#ef4444" strokeDasharray="3 3" label={{ value: 'High Risk Threshold', fill: '#ef4444', fontSize: 10, position: 'insideTopRight' }} />
              
              <Area 
                type="monotone" 
                dataKey="impliedVolatility" 
                stroke="#8b5cf6" 
                strokeWidth={3} 
                fillOpacity={1} 
                fill="url(#colorIV)" 
                activeDot={{ r: 6, strokeWidth: 0 }}
              />
              <Line 
                type="monotone" 
                dataKey="realizedVolatility" 
                stroke="#06b6d4" 
                strokeWidth={2} 
                dot={false} 
                strokeDasharray="4 4" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        
        <div className="mt-4 flex gap-4 overflow-x-auto pb-2">
            <div className="min-w-[200px] p-3 rounded bg-slate-800/30 border border-slate-800 text-xs text-slate-400">
                <span className="block font-bold text-slate-200 mb-1">Spread Positive (+Premium)</span>
                Market expects turbulence to increase. Options are expensive.
            </div>
            <div className="min-w-[200px] p-3 rounded bg-slate-800/30 border border-slate-800 text-xs text-slate-400">
                <span className="block font-bold text-slate-200 mb-1">Spread Negative (-Discount)</span>
                Market expects calm, but price is moving violently. High surprise risk.
            </div>
        </div>
      </div>

      {/* Risk Factors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {riskFactors.map((factor) => (
          <div key={factor.name} className="glass-panel p-5 rounded-xl border-l-4 border-l-transparent hover:border-l-cyan-500 transition-all group">
            <div className="flex justify-between items-start mb-3">
              <h4 className="font-bold text-slate-200 group-hover:text-cyan-400 transition-colors">{factor.name}</h4>
              <Badge status={factor.status} />
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mb-3 overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-1000 ${factor.score > 70 ? 'bg-red-500' : factor.score > 40 ? 'bg-yellow-500' : 'bg-emerald-500'}`} 
                style={{ width: `${factor.score}%` }}
              />
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">{factor.desc}</p>
          </div>
        ))}
      </div>

      {/* Alert Section */}
      {alertLevel > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center gap-4 transition-all hover:bg-red-500/15">
          <div className="p-3 bg-red-500/20 rounded-full text-red-400 animate-pulse">
            <AlertCircle size={24} />
          </div>
          <div className="flex-1">
            <h4 className="text-lg font-bold text-red-200">High Leverage Alert Detected for {currency}</h4>
            <p className="text-red-200/70 text-sm mt-1">Open Interest in derivatives markets has exceeded historical thresholds relative to market cap. A liquidation cascade is probable if price drops below critical support.</p>
          </div>
          <button 
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-200 rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 whitespace-nowrap"
          >
            View Analysis <ArrowRight size={16} />
          </button>
        </div>
      )}

      {/* Analysis Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm transition-opacity" onClick={() => setShowModal(false)} />
          <div className="relative bg-slate-900 border border-slate-700 rounded-xl p-6 md:p-8 max-w-xl w-full shadow-2xl transform transition-all scale-100">
            <button 
              onClick={() => setShowModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
            
            <div className="flex items-center gap-3 mb-2">
              <Shield className="text-red-500" size={24} />
              <h2 className="text-2xl font-bold text-white">Risk Analysis Report</h2>
            </div>
            <p className="text-slate-400 mb-6">Detailed breakdown of the triggered leverage alert for <span className="text-cyan-400 font-bold">{currency}</span>.</p>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                 <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                   <Activity size={12} /> Open Interest
                 </div>
                 <div className="text-2xl font-bold text-white">${metrics.openInterest}M</div>
                 <div className="text-red-400 text-xs mt-1 font-medium">Overextended</div>
              </div>
              <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                 <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                   <Target size={12} /> Est. Liq. Price
                 </div>
                 <div className="text-2xl font-bold text-white">${metrics.liquidationPrice}</div>
                 <div className="text-yellow-400 text-xs mt-1 font-medium">Key Support Level</div>
              </div>
              <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                 <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                   <TrendingDown size={12} /> Long/Short Ratio
                 </div>
                 <div className="text-2xl font-bold text-white">{metrics.lsRatio}</div>
                 <div className="text-slate-400 text-xs mt-1">Market Sentiment</div>
              </div>
              <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                 <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                   <Zap size={12} /> Funding Rate
                 </div>
                 <div className="text-2xl font-bold text-white">{metrics.fundingRate}%</div>
                 <div className="text-emerald-400 text-xs mt-1">Positive Bias</div>
              </div>
            </div>

            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
              <h4 className="font-bold text-red-200 mb-2 text-sm uppercase">Threat Assessment</h4>
              <p className="text-sm text-red-200/80 leading-relaxed">
                The confluence of high open interest (${metrics.openInterest}M) and a positive funding rate ({metrics.fundingRate}%) indicates a crowded long trade. A price drop below ${metrics.liquidationPrice} could trigger a cascading liquidation event, resulting in a rapid -15% to -20% correction.
              </p>
            </div>

            <div className="flex justify-end">
              <button 
                onClick={() => setShowModal(false)}
                className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium transition-colors text-sm"
              >
                Dismiss Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const Badge: React.FC<{status: string}> = ({ status }) => {
  const colors = {
    Low: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    Medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    High: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    Critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  };
  return (
    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${colors[status as keyof typeof colors]}`}>
      {status}
    </span>
  );
};

export default RiskPage;