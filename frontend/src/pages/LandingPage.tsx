import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Activity, ShieldCheck, BarChart2 } from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';

const LandingPage: React.FC = () => {
  return (
    <div className="relative min-h-screen flex flex-col text-black overflow-hidden bg-white">
      <AnimatedBackground />

      {/* Navigation */}
      <nav className="relative z-10 w-full max-w-7xl mx-auto px-6 py-6 flex justify-between items-center">
        <div className="text-2xl font-bold tracking-tighter flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse" />
          </div>
          Crypto<span className="text-cyan-400">Risk</span> Lens
        </div>
        <div className="flex gap-8 text-sm font-medium text-black">
          <a href="#features" className="hover:text-black transition-colors">Features</a>
          <a href="#about" className="hover:text-black transition-colors">Methodology</a>
        </div>
      </nav>

      {/* Hero Content */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-4 sm:px-6">
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-zinc-300 text-black text-xs font-medium uppercase tracking-wider mb-4">
            Live Market Analysis v2.0
          </div>

          <h1 className="text-5xl md:text-7xl font-semibold tracking-tight text-black leading-[1.1]">
            Understand Crypto Risk <br />
            with Data, Not Hype.
          </h1>

          <p className="text-lg md:text-xl text-black max-w-2xl mx-auto leading-relaxed">
            Professional-grade volatility modeling, sentiment analysis, and risk metrics for digital asset investors.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4">
            <Link
              to="/dashboard"
              className="group relative px-8 py-4 bg-white border border-black text-black font-semibold rounded-lg transition-all transform hover:scale-105 flex items-center gap-2"
            >
              Explore Dashboard
              <ArrowRight className="group-hover:translate-x-1 transition-transform" size={20} />
            </Link>

            <Link
              to="/risk"
              className="px-8 py-4 bg-white border border-zinc-300 hover:bg-zinc-100 text-black font-medium rounded-lg transition-all"
            >
              View Market Risk
            </Link>
          </div>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto mt-24 w-full">
          <FeatureCard
            icon={<ShieldCheck className="text-black" size={32} />}
            title="Risk Regime Detection"
            desc="Identify whether the market is in a stable, speculative, or crash-prone regime."
          />
          <FeatureCard
            icon={<Activity className="text-black" size={32} />}
            title="Volatility Forecasting"
            desc="Predictive models based on historical volatility clusters and on-chain activity."
          />
          <FeatureCard
            icon={<BarChart2 className="text-black" size={32} />}
            title="Sentiment Analysis"
            desc="NLP analysis of global news and social signals to gauge market emotion."
          />
        </div>
      </main>

      <footer className="relative z-10 py-8 text-center text-black text-sm">
        2024 Crypto-Risk Lens. Data is for informational purposes only.
      </footer>
    </div>
  );
};

const FeatureCard: React.FC<{icon: React.ReactNode, title: string, desc: string}> = ({ icon, title, desc }) => (
  <div className="glass-card p-6 rounded-xl text-left hover:border-zinc-300 transition-colors group">
    <div className="mb-4 p-3 bg-white rounded-lg inline-block group-hover:scale-105 transition-transform duration-300 border border-zinc-300">
      {icon}
    </div>
    <h3 className="text-lg font-semibold text-black mb-2">{title}</h3>
    <p className="text-black text-sm leading-relaxed">{desc}</p>
  </div>
);

export default LandingPage;

