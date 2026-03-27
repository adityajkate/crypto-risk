import React, { useEffect, useRef, useState, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, TrendingUp, Activity,
  Layers, BarChart3, ChevronRight, Zap, PlayCircle, BarChart, Eye, Search, Database, Brain,
  FileText, Bell, Share2, Calendar, Cpu, SlidersHorizontal, Target, BellRing, LayoutDashboard,
  Link2, MessageSquare
} from 'lucide-react';
import { DitheringShader } from '../components/ui/dithering-shader';
import { GlobeDemo } from '../components/GlobeDemo';
import TrueFocus from '../components/ui/TrueFocus';
import RotatingText from '../components/ui/RotatingText';
import Grainient from '../components/ui/Grainient';
import { Highlighter } from '../components/ui/highlighter';
import LightRays from '../components/ui/LightRays';
import { AnimatedBeam } from '../components/ui/AnimatedBeam';

/* --- UTILITIES --- */
function useIsScrolled(threshold: number = 50) {
  const [isScrolled, setIsScrolled] = useState(false);
  useEffect(() => {
    let ticking = false;
    const updateScroll = () => {
      setIsScrolled(window.scrollY > threshold);
      ticking = false;
    };
    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(updateScroll);
        ticking = true;
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    updateScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, [threshold]);
  return isScrolled;
}

function useIntersectionObserver(options: IntersectionObserverInit = { threshold: 0.1, rootMargin: '0px' }, once: boolean = true) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true);
        if (once && ref.current) observer.unobserve(ref.current);
      } else if (!once) {
        setIsVisible(false);
      }
    }, options);
    const curr = ref.current;
    if (curr) observer.observe(curr);
    return () => { if (curr) observer.unobserve(curr); };
  }, [options, once]);

  return { ref, isVisible };
}

/* --- LOGOS & ICONS --- */

const Logo: React.FC<{ size?: number, hideText?: boolean }> = ({ size = 24, hideText = false }) => (
  <Link to="/" className="flex items-center gap-3 group cursor-pointer">
    <div className="relative">
      <Zap
        className="text-[#0d9488] transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:rotate-[15deg] group-hover:scale-110"
        size={size}
        strokeWidth={2.5}
        fill="currentColor"
      />
      <div className="absolute inset-0 bg-[#0d9488] blur-xl opacity-0 group-hover:opacity-40 transition-opacity duration-700" />
    </div>
    {!hideText && (
      <span className="text-xl font-bold tracking-tight text-[#0f172a]">
        CryptoRisk Lens
      </span>
    )}
  </Link>
);


const BTCIcon = () => (
  <img src="https://cdn.jsdelivr.net/gh/coinwink/cryptocurrency-logos@master/coins/128x128/1.png" alt="BTC" className="w-full h-full object-contain" />
);

const ETHIcon = () => (
  <img src="https://cdn.jsdelivr.net/gh/coinwink/cryptocurrency-logos@master/coins/128x128/1027.png" alt="ETH" className="w-full h-full object-contain" />
);

const SOLIcon = () => (
  <img src="https://cdn.jsdelivr.net/gh/coinwink/cryptocurrency-logos@master/coins/128x128/5426.png" alt="SOL" className="w-full h-full object-contain" />
);

const XRPIcon = () => (
  <img src="https://cdn.jsdelivr.net/gh/coinwink/cryptocurrency-logos@master/coins/128x128/52.png" alt="XRP" className="w-full h-full object-contain" />
);

/* --- BACKGROUNDS & ATMOSPHERE --- */

// Super soft, highly minimal background mesh
const Atmosphere = React.memo(() => {
  return (
    <>
      <div className="fixed inset-0 bg-white -z-50" />

      {/* Dynamic Animated Soft Gradients */}
      <div
        className="fixed top-[-20%] left-[-10%] w-[80vw] h-[80vw] rounded-full opacity-[0.25] pointer-events-none animate-blob"
        style={{
          background: 'radial-gradient(circle, rgba(13,148,136,0.1) 0%, rgba(13,148,136,0) 60%)',
          filter: 'blur(100px)',
        }}
      />
      <div
        className="fixed top-[10%] right-[-20%] w-[90vw] h-[90vw] rounded-full opacity-[0.2] pointer-events-none animate-blob animation-delay-2000"
        style={{
          background: 'radial-gradient(circle, rgba(16,185,129,0.1) 0%, rgba(16,185,129,0) 60%)',
          filter: 'blur(120px)',
        }}
      />

      {/* Vercel/Linear style grid */}
      <div
        className="fixed inset-0 pointer-events-none -z-40"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(0,0,0,0.02) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0,0,0,0.02) 1px, transparent 1px)
          `,
          backgroundSize: '80px 80px',
        }}
      >
        {/* Fades grid out at bottom */}
        <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent opacity-80" />
      </div>
    </>
  );
});

/* --- SHARED UI COMPOSITES --- */

const GlassBadge: React.FC<{ text: string, pulse?: boolean }> = ({ text, pulse }) => (
  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/80 backdrop-blur-3xl border border-black/5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] animate-slide-up-fade">
    {pulse && <span className="relative flex h-2 w-2">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#0d9488] opacity-75"></span>
      <span className="relative inline-flex rounded-full h-2 w-2 bg-[#0d9488]"></span>
    </span>}
    <span className="text-[11px] font-bold text-[#334155] tracking-[0.1em] uppercase">{text}</span>
  </div>
);

const PremiumBtn: React.FC<{ to: string, primary?: boolean, icon?: ReactNode, children: ReactNode }> = ({ to, primary, icon, children }) => {
  if (primary) {
    return (
      <Link
        to={to}
        className="group relative inline-flex items-center justify-center h-14 px-8 text-sm font-semibold text-white bg-[#0d9488] rounded-xl overflow-hidden shadow-md shadow-[#0d9488]/20 transition-all duration-300 hover:shadow-lg hover:shadow-[#0d9488]/40 hover:-translate-y-0.5"
      >
        <div className="absolute inset-0 bg-gradient-to-r from-[#0d9488] to-[#14b8a6] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        <span className="relative z-10 flex items-center gap-2">
          {children} {icon}
        </span>
      </Link>
    );
  }

  return (
    <Link
      to={to}
      className="group relative inline-flex items-center justify-center h-14 px-8 text-sm font-semibold text-[#0d9488] bg-white rounded-xl overflow-hidden transition-all duration-300 shadow-sm border border-[#0d9488]/20 hover:border-[#0d9488]/40 hover:shadow-md hover:shadow-[#0d9488]/10 hover:-translate-y-0.5"
    >
      <div className="absolute inset-x-0 bottom-0 h-0 group-hover:h-full bg-[#0d9488]/5 transition-all duration-300" />
      <span className="relative z-10 flex items-center gap-2">
        {children} {icon}
      </span>
    </Link>
  );
};

/* --- HERO SECTION --- */

const HeroSection: React.FC = () => {
  const { ref, isVisible } = useIntersectionObserver({ threshold: 0 }, false);

  return (
    <section ref={ref} className="relative min-h-[100svh] flex flex-col justify-center items-center overflow-hidden px-6 pt-20">

      {/* Grainient Background - Only render when visible to save mobile battery */}
      <div className="absolute inset-0 w-full h-full pointer-events-none z-0">
        {isVisible && (
          <Grainient
            color1="#e0fdf4"
            color2="#99f6e4"
            color3="#f0fdfa"
            timeSpeed={0.15}
            colorBalance={0.1}
            warpStrength={1.2}
            warpFrequency={4}
            warpSpeed={1.5}
            warpAmplitude={60}
            blendAngle={15}
            blendSoftness={0.08}
            rotationAmount={300}
            noiseScale={2}
            grainAmount={0.06}
            grainScale={2}
            grainAnimated={false}
            contrast={1.2}
            gamma={1}
            saturation={0.9}
            zoom={0.95}
          />
        )}
      </div>

      <div className="relative z-10 max-w-4xl w-full mx-auto flex flex-col items-center text-center mt-12 lg:mt-0">
        <GlassBadge text="Intelligent Risk Analysis" pulse />

        <div className="mt-8 mb-6 relative">
          <h1 className="text-[clamp(3rem,6vw,5.5rem)] font-bold leading-[1.05] tracking-[-0.03em] text-[#0f172a] drop-shadow-sm">
            <span className="block animate-slide-up-fade" style={{ animationDelay: '100ms' }}>
              Navigate the{' '}
              <span className="relative inline-block border border-[#0EA5A4] px-3 mx-1 text-[#0F172A]" style={{ backgroundColor: 'rgba(245,158,11,0.1)' }}>
                market
                <span className="absolute h-2 w-2 bg-[#14B8A6] top-0 left-0 -translate-x-1/2 -translate-y-1/2" />
                <span className="absolute h-2 w-2 bg-[#14B8A6] top-0 right-0 translate-x-1/2 -translate-y-1/2" />
                <span className="absolute h-2 w-2 bg-[#14B8A6] bottom-0 left-0 -translate-x-1/2 translate-y-1/2" />
                <span className="absolute h-2 w-2 bg-[#14B8A6] bottom-0 right-0 translate-x-1/2 translate-y-1/2" />
              </span>
            </span>
            <span className="block animate-slide-up-fade" style={{ animationDelay: '250ms' }}>
              with{' '}
              <Highlighter action="underline" color="#f59e0b" strokeWidth={4} animationDuration={600} iterations={2} delay={900}>
                absolute clarity.
              </Highlighter>
            </span>
          </h1>
        </div>

        <p className="text-lg md:text-xl text-[#475569] font-medium max-w-2xl leading-relaxed animate-slide-up-fade" style={{ animationDelay: '400ms' }}>
          Stop guessing. We transform complex volatility, technicals, and sentiment into beautifully simple risk metrics you can trust.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mt-12 animate-slide-up-fade w-full sm:w-auto" style={{ animationDelay: '550ms' }}>
          <PremiumBtn to="/dashboard" primary icon={<ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />}>
            Enter Dashboard
          </PremiumBtn>
          <PremiumBtn to="/sentiment" icon={<PlayCircle size={16} className="text-[#0d9488]" />}>
            View Market Sentiment
          </PremiumBtn>
        </div>
      </div>

    </section>
  );
};


/* --- FEATURE GRID SECTION --- */

const RevealCard: React.FC<{
  children: ReactNode;
  delay: number;
  className?: string;
}> = ({ children, delay, className = '' }) => {
  const { ref, isVisible } = useIntersectionObserver({ threshold: 0.1 });

  return (
    <div
      ref={ref}
      className={`
                relative bg-white rounded-3xl border border-black/[0.04] p-8 md:p-10
                shadow-sm hover:shadow-[0_20px_40px_rgba(0,0,0,0.04)]
                transition-all duration-700 ease-out-expo
                ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}
                ${className}
            `}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
};

const MinimalBentoSection: React.FC = () => {
  const { ref, isVisible } = useIntersectionObserver({ threshold: 0 }, false);

  return (
    <section className="relative z-10 w-full bg-white" ref={ref}>
      <div className="py-20 md:py-32 px-4 md:px-6 max-w-7xl mx-auto">
        <div className="mb-12 md:mb-20 grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 items-end">
          <div>
            <h2 className="text-4xl md:text-5xl font-bold tracking-[-0.03em] text-[#0f172a] leading-[1.1]">
              Smart risk insights.<br />
              <span className="text-[#0d9488]">Crypto clarity.</span>
            </h2>
          </div>
          <div>
            <p className="text-[#475569] text-lg font-medium leading-relaxed max-w-lg md:ml-auto">
              Real market intelligence shouldn't be complicated. We process millions of data points, so you see precisely what matters.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 auto-rows-min">

          {/* Trend Detection - Spans 4 cols */}
          <RevealCard className="md:col-span-4 group overflow-hidden" delay={0}>
            <div className="absolute inset-0 bg-gradient-to-br from-[#0d9488]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

            <div className="flex flex-col h-full relative z-10 w-full">
              <div className="w-12 h-12 rounded-xl bg-[#fafafa] border border-black/5 flex items-center justify-center text-[#0d9488] mb-6 shadow-sm">
                <Eye size={22} />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-[#0f172a] mb-2">ML Models</h3>
                <p className="text-[#475569] font-medium text-sm leading-relaxed">Powered by an ensemble of purpose-built models for risk, regime, volatility, and clustering.</p>
              </div>

              {/* RotatingText model names */}
              <div className="mt-8 flex items-center gap-3 flex-wrap text-base font-medium text-[#475569]">
                <span>Powered by</span>
                <RotatingText
                  texts={['XGBoost', 'HMM', 'Quantile Regression', 'K-Means', 'PCA']}
                  mainClassName="px-4 py-1.5 bg-[#0d9488]/10 text-[#0d9488] text-lg font-bold rounded-lg overflow-hidden"
                  staggerFrom="last"
                  initial={{ y: '100%' }}
                  animate={{ y: 0 }}
                  exit={{ y: '-120%' }}
                  staggerDuration={0.025}
                  splitLevelClassName="overflow-hidden"
                  transition={{ type: 'spring', damping: 30, stiffness: 400 }}
                  rotationInterval={2000}
                />
              </div>
            </div>
          </RevealCard>

          {/* Market Analysis Dashboard - Spans 8 cols */}
          <RevealCard className="md:col-span-8 group overflow-hidden" delay={150}>
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(16,185,129,0.05),transparent_60%)] opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />

            <div className="relative z-10 flex flex-col md:flex-row gap-10 items-center h-full">
              <div className="flex-1">
                <div className="w-12 h-12 rounded-xl bg-[#fafafa] border border-black/5 flex items-center justify-center text-[#0d9488] mb-6 shadow-sm relative overflow-hidden group-hover:border-[#0d9488]/30 transition-colors duration-500">
                  <Search size={22} className="relative z-10 text-[#0d9488] group-hover:text-[#10b981] transition-colors duration-500" />
                </div>
                <h3 className="text-3xl font-bold tracking-tighter text-[#0f172a] mb-3">Trend Detection</h3>
                <p className="text-[#475569] font-medium leading-relaxed max-w-sm">Automatically identifies market momentum—whether bull, bear, or completely sideways.</p>
              </div>

              {/* TrueFocus Animation */}
              <div className="w-full md:w-[350px] relative mt-6 md:mt-0 flex items-center justify-center">
                <TrueFocus
                  sentence="Bullish Bearish Neutral"
                  manualMode={false}
                  blurAmount={6}
                  borderColor="#0d9488"
                  glowColor="rgba(13,148,136,0.4)"
                  animationDuration={0.5}
                  pauseBetweenAnimations={2}
                  wordColors={['#10b981', '#ef4444', '#94a3b8']}
                />
              </div>
            </div>
          </RevealCard>

          {/* Smarter Indicators - Spans 12 cols */}
          <RevealCard className="md:col-span-12 group overflow-hidden" delay={0}>
            <div className="absolute right-0 top-0 w-1/2 h-full bg-[radial-gradient(circle_at_center,rgba(20,184,166,0.05),transparent_70%)] group-hover:opacity-100 opacity-0 transition-opacity duration-700" />

            <div className="relative z-10 flex flex-col md:flex-row gap-10 items-center h-full">
              <div className="flex-1">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#0d9488]/10 to-transparent border border-[#0d9488]/10 flex items-center justify-center text-[#0d9488] mb-6">
                  <Database size={22} />
                </div>
                <h3 className="text-2xl font-bold text-[#0f172a] mb-3">Real-Time Market Data</h3>
                <p className="text-[#475569] font-medium leading-relaxed">Live cryptocurrency price data, market metrics, and sentiment analysis from global exchanges and news sources.</p>
              </div>

              {/* Globe Demonstration replacing beam */}
              <div className="w-full md:w-[650px] h-[350px] md:h-[500px] relative z-20 flex items-center justify-center mt-8 md:mt-0">
                {isVisible && <GlobeDemo />}
              </div>
            </div>
          </RevealCard>


        </div>
      </div>
    </section>
  );
};

// 3. Immersive Typography Marquee Banner
const CryptoMarquee: React.FC = () => {
  const coins = [
    { ticker: "BTC", label: "BITCOIN", id: 1 },
    { ticker: "ETH", label: "ETHEREUM", id: 1027 },
    { ticker: "SOL", label: "SOLANA", id: 5426 },
    { ticker: "XRP", label: "RIPPLE", id: 52 },
    { ticker: "BNB", label: "BINANCE", id: 1839 },
    { ticker: "ADA", label: "CARDANO", id: 2010 },
    { ticker: "DOGE", label: "DOGECOIN", id: 74 },
    { ticker: "AVAX", label: "AVALANCHE", id: 5805 },
    { ticker: "MATIC", label: "POLYGON", id: 3890 },
    { ticker: "DOT", label: "POLKADOT", id: 6636 },
    { ticker: "LINK", label: "CHAINLINK", id: 1975 },
    { ticker: "UNI", label: "UNISWAP", id: 7083 },
    { ticker: "ATOM", label: "COSMOS", id: 3794 },
    { ticker: "LTC", label: "LITECOIN", id: 2 },
    { ticker: "NEAR", label: "NEAR", id: 6535 },
    { ticker: "APT", label: "APTOS", id: 21794 },
    { ticker: "ARB", label: "ARBITRUM", id: 11841 },
    { ticker: "OP", label: "OPTIMISM", id: 11840 },
    { ticker: "INJ", label: "INJECTIVE", id: 7226 },
    { ticker: "SUI", label: "SUI", id: 20947 },
    { ticker: "TIA", label: "CELESTIA", id: 22861 },
    { ticker: "JUP", label: "JUPITER", id: 29210 },
    { ticker: "WIF", label: "DOGWIFHAT", id: 28752 },
    { ticker: "PEPE", label: "PEPE", id: 24478 },
    { ticker: "SHIB", label: "SHIBA INU", id: 5994 },
    { ticker: "TRX", label: "TRON", id: 1958 },
    { ticker: "XLM", label: "STELLAR", id: 512 },
    { ticker: "HBAR", label: "HEDERA", id: 4642 },
    { ticker: "FIL", label: "FILECOIN", id: 2280 },
    { ticker: "AAVE", label: "AAVE", id: 7278 },
    { ticker: "MKR", label: "MAKER", id: 1518 },
    { ticker: "CRV", label: "CURVE", id: 6538 },
    { ticker: "GMX", label: "GMX", id: 11857 },
    { ticker: "LDO", label: "LIDO", id: 8000 },
    { ticker: "FTM", label: "FANTOM", id: 3513 },
    { ticker: "ICP", label: "INTERNET COMPUTER", id: 8916 },
    { ticker: "SEI", label: "SEI", id: 23149 },
    { ticker: "PYTH", label: "PYTH", id: 28177 },
    { ticker: "FLOKI", label: "FLOKI", id: 10804 },
    { ticker: "ETC", label: "ETHEREUM CLASSIC", id: 1321 },
    { ticker: "ALGO", label: "ALGORAND", id: 4030 },
    { ticker: "VET", label: "VECHAIN", id: 3077 },
    { ticker: "SAND", label: "SANDBOX", id: 6210 },
    { ticker: "AXS", label: "AXIE", id: 6783 },
    { ticker: "COMP", label: "COMPOUND", id: 5692 },
    { ticker: "SNX", label: "SYNTHETIX", id: 2586 },
    { ticker: "DYDX", label: "DYDX", id: 11156 },
    { ticker: "RPL", label: "ROCKETPOOL", id: 2943 },
    { ticker: "BCH", label: "BITCOIN CASH", id: 1831 },
    { ticker: "MANA", label: "DECENTRALAND", id: 1966 },
  ];

  const iconUrl = (ticker: string) =>
    `https://assets.coincap.io/assets/icons/${ticker.toLowerCase()}@2x.png`;

  return (
    <section className="py-24 relative z-10 bg-white overflow-hidden flex">
      <div className="absolute left-0 top-0 bottom-0 w-32 md:w-64 bg-gradient-to-r from-white to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-32 md:w-64 bg-gradient-to-l from-white to-transparent z-10 pointer-events-none" />

      <div className="flex whitespace-nowrap animate-marquee w-max">
        {[...Array(2)].map((_, i) => (
          <div key={i} className="flex items-center">
            {coins.map((coin, j) => (
              <div key={j} className="flex items-center gap-4 md:gap-6 mx-6 md:mx-12 group cursor-pointer transition-transform duration-500 hover:scale-[1.03]">
                <div className="w-10 h-10 md:w-14 md:h-14 opacity-30 grayscale group-hover:grayscale-0 group-hover:opacity-100 transition-all duration-500 flex-shrink-0">
                  <img
                    src={iconUrl(coin.ticker)}
                    alt={coin.ticker}
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      const target = e.currentTarget;
                      target.style.display = 'none';
                      const parent = target.parentElement;
                      if (parent && !parent.querySelector('.ticker-fallback')) {
                        const fallback = document.createElement('div');
                        fallback.className = 'ticker-fallback w-full h-full rounded-full bg-[#0d9488]/20 flex items-center justify-center text-[#0d9488] font-black text-[10px]';
                        fallback.textContent = coin.ticker.slice(0, 3);
                        parent.appendChild(fallback);
                      }
                    }}
                  />
                </div>
                <span
                  className="text-[2.5rem] md:text-[5rem] font-black tracking-[-0.04em] text-transparent transition-all duration-500 group-hover:text-[#0f172a]"
                  style={{ WebkitTextStroke: '2px rgba(15,23,42,0.25)' }}
                >
                  {coin.label}
                </span>
                <span className="text-[#0f172a]/15 text-3xl md:text-5xl font-thin">·</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

const Circle = React.forwardRef<
  HTMLDivElement,
  { className?: string; children?: ReactNode; label?: string; accent?: boolean }
>(({ className, children, label, accent }, ref) => (
  <div className="flex flex-col items-center gap-2.5">
    <div
      ref={ref}
      className={`z-10 flex items-center justify-center rounded-full border-2 ${accent
        ? 'size-20 bg-[#0f172a] border-[#0f172a] text-white shadow-[0_0_32px_rgba(15,23,42,0.25)]'
        : 'size-14 bg-white border-black/10 text-[#0f172a] p-3 shadow-[0_2px_12px_rgba(0,0,0,0.06)]'
        } ${className ?? ''}`}
    >
      {children}
    </div>
    {label && (
      <span className="text-sm font-medium text-[#0f172a] tracking-tight whitespace-nowrap">{label}</span>
    )}
  </div>
));
Circle.displayName = 'Circle';

const ArchitectureDiagram: React.FC = () => {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const pricesRef = React.useRef<HTMLDivElement>(null);
  const onchainRef = React.useRef<HTMLDivElement>(null);
  const sentimentRef = React.useRef<HTMLDivElement>(null);
  const featuresRef = React.useRef<HTMLDivElement>(null);
  const mlRef = React.useRef<HTMLDivElement>(null);
  const engineRef = React.useRef<HTMLDivElement>(null);
  const riskRef = React.useRef<HTMLDivElement>(null);
  const dashRef = React.useRef<HTMLDivElement>(null);

  return (
    <div
      ref={containerRef}
      className="relative flex h-[360px] w-full items-center justify-center overflow-hidden px-4 py-10"
    >
      <div className="flex w-full max-w-4xl flex-row items-center justify-between">

        {/* Stage 1 — Inputs */}
        <div className="flex flex-col items-center gap-8">
          <Circle ref={pricesRef} label="Prices"><TrendingUp size={22} strokeWidth={1.75} /></Circle>
          <Circle ref={onchainRef} label="On-Chain"><Link2 size={22} strokeWidth={1.75} /></Circle>
          <Circle ref={sentimentRef} label="Sentiment"><MessageSquare size={22} strokeWidth={1.75} /></Circle>
        </div>

        {/* Stage 2 — Features */}
        <div className="flex flex-col items-center">
          <Circle ref={featuresRef} label="Features"><SlidersHorizontal size={22} strokeWidth={1.75} /></Circle>
        </div>

        {/* Stage 3 — ML Models */}
        <div className="flex flex-col items-center">
          <Circle ref={mlRef} label="ML Models"><Cpu size={22} strokeWidth={1.75} /></Circle>
        </div>

        {/* Stage 4 — Risk Engine (hub) */}
        <div className="flex flex-col items-center">
          <Circle ref={engineRef} label="Risk Engine" accent><Zap size={26} strokeWidth={1.75} /></Circle>
        </div>

        {/* Stage 5 — Outputs */}
        <div className="flex flex-col items-center gap-8">
          <Circle ref={riskRef} label="Risk Score"><Target size={22} strokeWidth={1.75} /></Circle>
          <Circle ref={dashRef} label="Dashboard"><LayoutDashboard size={22} strokeWidth={1.75} /></Circle>
        </div>
      </div>

      {/* Inputs → Features */}
      <AnimatedBeam containerRef={containerRef} fromRef={pricesRef} toRef={featuresRef} curvature={-45} duration={4} delay={0} gradientStartColor="#0f172a" gradientStopColor="#334155" pathColor="#0f172a" />
      <AnimatedBeam containerRef={containerRef} fromRef={onchainRef} toRef={featuresRef} duration={4.5} delay={0.4} gradientStartColor="#0f172a" gradientStopColor="#334155" pathColor="#0f172a" />
      <AnimatedBeam containerRef={containerRef} fromRef={sentimentRef} toRef={featuresRef} curvature={45} duration={5} delay={0.8} gradientStartColor="#0f172a" gradientStopColor="#334155" pathColor="#0f172a" />

      {/* Features → ML Models */}
      <AnimatedBeam containerRef={containerRef} fromRef={featuresRef} toRef={mlRef} duration={3.5} delay={0} gradientStartColor="#0f172a" gradientStopColor="#334155" pathColor="#0f172a" pathWidth={2} />

      {/* ML Models → Risk Engine */}
      <AnimatedBeam containerRef={containerRef} fromRef={mlRef} toRef={engineRef} duration={3.5} delay={0.2} gradientStartColor="#0f172a" gradientStopColor="#334155" pathColor="#0f172a" pathWidth={2.5} />

      {/* Risk Engine → Outputs */}
      <AnimatedBeam containerRef={containerRef} fromRef={engineRef} toRef={riskRef} curvature={-45} duration={4} delay={0} gradientStartColor="#0f172a" gradientStopColor="#334155" pathColor="#0f172a" />
      <AnimatedBeam containerRef={containerRef} fromRef={engineRef} toRef={dashRef} curvature={45} duration={5} delay={0.8} gradientStartColor="#0f172a" gradientStopColor="#334155" pathColor="#0f172a" />
    </div>
  );
};

// 4. Data Flow Minimal Pipeline
const PipelineSection: React.FC = () => {
  const { ref, isVisible } = useIntersectionObserver({ threshold: 0 }, false);

  return (
    <section ref={ref} className="relative z-10 w-full overflow-hidden bg-white">
      <div className="absolute inset-0 z-0">
        {isVisible && (
          <LightRays
            raysOrigin="top-center"
            raysColor="#0d9488"
            raysSpeed={1}
            lightSpread={0.8}
            rayLength={4}
            followMouse={false}
            mouseInfluence={0}
            noiseAmount={0}
            distortion={0}
            pulsating={false}
            fadeDistance={1.2}
            saturation={1}
          />
        )}
      </div>
      <div className="relative z-10 w-full max-w-4xl mx-auto px-6 flex flex-col items-center text-center pt-20 pb-12">
        <GlassBadge text="System Flow" pulse />
        <h2 className="text-4xl md:text-5xl font-bold tracking-[-0.03em] text-[#0f172a] mt-6 mb-4">
          Data doesn't sleep.
        </h2>
        <p className="text-[#475569] text-lg font-medium leading-relaxed max-w-2xl mb-12">
          From raw market feeds to clear dashboard visuals in milliseconds. Constant updates. Constant edge.
        </p>
        <ArchitectureDiagram />
      </div>
    </section>
  );
};



/* --- LAYOUT COMPONENT --- */

const LandingPage: React.FC = () => {
  const isScrolled = useIsScrolled(50);
  const { ref, isVisible } = useIntersectionObserver({ threshold: 0 }, false);

  const styles = `
    @keyframes slideUpFade {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes marquee {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    @keyframes marquee-reverse {
        0% { transform: translateX(-50%); }
        100% { transform: translateX(0); }
    }
    @keyframes marquee-vertical {
        0% { transform: translateY(0); }
        100% { transform: translateY(-50%); }
    }
    @keyframes blob {
        0% { transform: translate(0px, 0px) scale(1); }
        33% { transform: translate(30px, -50px) scale(1.1); }
        66% { transform: translate(-20px, 20px) scale(0.9); }
        100% { transform: translate(0px, 0px) scale(1); }
    }
    .animate-blob { animation: blob 15s infinite alternate ease-in-out; will-change: transform; }
    .animation-delay-2000 { animation-delay: 2s; }
    .animate-slide-up-fade { animation: slideUpFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; }
    .animate-marquee { animation: marquee 60s linear infinite; will-change: transform; }
    .animate-marquee-reverse { animation: marquee-reverse 40s linear infinite; }
    .animate-marquee-vertical { animation: marquee-vertical 8s linear infinite; }
    .ease-out-expo { transition-timing-function: cubic-bezier(0.16, 1, 0.3, 1); }
  `;

  return (
    <div className="bg-white min-h-screen text-[#0f172a] font-sans selection:bg-[#0d9488]/20 selection:text-[#0d9488] overflow-hidden">

      <style dangerouslySetInnerHTML={{ __html: styles }} />

      <Atmosphere />

      <nav className={`fixed top-0 left-0 right-0 z-50 w-full transition-all duration-500 ease-out ${isScrolled ? 'pt-4 px-4' : 'pt-6 px-6'}`}>
        <div
          className="mx-auto flex justify-between items-center origin-top transition-all duration-500 ease-out will-change-transform"
          style={{
            maxWidth: isScrolled ? '900px' : '1280px',
            backgroundColor: isScrolled ? 'rgba(255, 255, 255, 0.4)' : 'transparent',
            backdropFilter: isScrolled ? 'blur(24px)' : 'blur(0px)',
            WebkitBackdropFilter: isScrolled ? 'blur(24px)' : 'blur(0px)',
            border: isScrolled ? '1px solid rgba(255, 255, 255, 0.4)' : '1px solid transparent',
            borderRadius: isScrolled ? '9999px' : '16px',
            padding: isScrolled ? '12px 24px' : '16px 24px',
            boxShadow: isScrolled ? '0 8px 32px rgba(0,0,0,0.06)' : 'none'
          }}
        >
          <Logo />

          <div className="flex items-center gap-6 text-sm font-semibold">
            <Link to="/sentiment" className="text-[#475569] hover:text-[#0d9488] transition-colors duration-300 hidden md:block">Sentiments</Link>
            <Link to="/dashboard" className="relative group px-5 py-2.5 rounded-xl bg-[#0d9488] text-white shadow-md shadow-[#0d9488]/20 hover:shadow-lg hover:shadow-[#0d9488]/40 hover:-translate-y-0.5 transition-all duration-300 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-[#0d9488] to-[#14b8a6] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <span className="relative z-10">Go to Dashboard</span>
            </Link>
          </div>
        </div>
      </nav>

      <main>
        <HeroSection />
        <MinimalBentoSection />
        <CryptoMarquee />
        <PipelineSection />
      </main>

      <footer ref={ref} className="relative z-10 bg-white py-20 px-6 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none opacity-[0.15] mix-blend-multiply z-0">
          {isVisible && (
            <DitheringShader
              shape="wave"
              type="8x8"
              colorBack="#ffffff"
              colorFront="#0d9488"
              pxSize={3}
              speed={0.4}
            />
          )}
        </div>
        <div className="max-w-[1280px] mx-auto relative z-10 flex flex-col md:flex-row justify-between items-center md:items-end gap-10">
          <div className="flex flex-col items-center md:items-start text-center md:text-left gap-4">
            <Logo />
            <p className="text-[#475569] font-medium max-w-sm">The cleanest standard for intelligent crypto risk analysis. Stop guessing, start knowing.</p>
          </div>

          <div className="flex flex-col items-center md:items-end gap-2 text-sm">
            <span className="text-[#475569] font-medium">Built by</span>
            <div className="flex flex-wrap items-center justify-center md:justify-end gap-3 font-semibold text-[#0f172a] tracking-tight">
              <span className="hover:text-[#0d9488] transition-colors cursor-default">Aditya Kate</span>
              <span className="text-[#0d9488]/30">•</span>
              <span className="hover:text-[#0d9488] transition-colors cursor-default">Tanmay Harmalkar</span>
              <span className="text-[#0d9488]/30">•</span>
              <span className="hover:text-[#0d9488] transition-colors cursor-default">Suman Manik</span>
            </div>
          </div>
        </div>
      </footer>

    </div>
  );
};

export default LandingPage;
