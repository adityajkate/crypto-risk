import React from 'react';
import { Database, Cpu, Layers } from 'lucide-react';

const AboutPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto space-y-12 pb-12">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-white">Methodology & Data Sources</h1>
        <p className="text-slate-400 text-lg">How Crypto-Risk Lens calculates risk in a chaotic market.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        <div className="glass-panel p-6 rounded-xl text-center">
          <div className="w-12 h-12 bg-blue-500/10 text-blue-400 rounded-lg flex items-center justify-center mx-auto mb-4">
            <Database size={24} />
          </div>
          <h3 className="font-bold text-white mb-2">On-Chain Data</h3>
          <p className="text-sm text-slate-400">Direct integration with Bitcoin and Ethereum nodes to track whale wallet movements and exchange inflows/outflows.</p>
        </div>
        <div className="glass-panel p-6 rounded-xl text-center">
          <div className="w-12 h-12 bg-purple-500/10 text-purple-400 rounded-lg flex items-center justify-center mx-auto mb-4">
            <Cpu size={24} />
          </div>
          <h3 className="font-bold text-white mb-2">ML Sentiment</h3>
          <p className="text-sm text-slate-400">Natural Language Processing (BERT models) analyzing over 50,000 news articles and tweets daily for emotional tone.</p>
        </div>
        <div className="glass-panel p-6 rounded-xl text-center">
          <div className="w-12 h-12 bg-cyan-500/10 text-cyan-400 rounded-lg flex items-center justify-center mx-auto mb-4">
            <Layers size={24} />
          </div>
          <h3 className="font-bold text-white mb-2">GARCH Modeling</h3>
          <p className="text-sm text-slate-400">Institutional-grade volatility forecasting using Generalized Autoregressive Conditional Heteroskedasticity models.</p>
        </div>
      </div>

      <div className="glass-panel p-8 rounded-xl space-y-6">
        <h2 className="text-2xl font-bold text-white">The Risk Score Algorithm</h2>
        <div className="space-y-4 text-slate-300">
          <p>
            Our proprietary Risk Score (0-100) is a weighted average of four primary components:
          </p>
          <ul className="list-disc list-inside space-y-2 ml-4">
            <li><strong className="text-white">Volatility (30%):</strong> 30-day realized volatility vs implied volatility.</li>
            <li><strong className="text-white">Sentiment (20%):</strong> Deviation from neutral sentiment baseline.</li>
            <li><strong className="text-white">Liquidity (25%):</strong> Order book depth and slippage metrics.</li>
            <li><strong className="text-white">Macro (25%):</strong> Correlation with DXY (Dollar Index) and S&P 500.</li>
          </ul>
          <p className="pt-4 text-sm text-slate-500 border-t border-slate-800">
            Disclaimer: Risk scores are calculated using machine learning models trained on historical data. Past performance does not guarantee future results. This tool is for informational purposes only and should not be considered financial advice.
          </p>
        </div>
      </div>
    </div>
  );
};

export default AboutPage;