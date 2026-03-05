import React, { useEffect, useRef, useState, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, TrendingUp, Activity,
  Layers, BarChart3, ChevronRight, Zap, PlayCircle, BarChart, Eye, Search, Database, Brain
} from 'lucide-react';
import { DitheringShader } from '../components/ui/dithering-shader';

/* --- UTILITIES --- */
function useScrollPosition() {
  const [scrollY, setScrollY] = useState(0);
  useEffect(() => {
    let ticking = false;
    const updateScrollY = () => {
      setScrollY(window.scrollY);
      ticking = false;
    };
    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(updateScrollY);
        ticking = true;
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    updateScrollY();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return scrollY;
}

function useIntersectionObserver(options: IntersectionObserverInit = { threshold: 0.1, rootMargin: '0px' }) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true);
        if (ref.current) observer.unobserve(ref.current);
      }
    }, options);
    const curr = ref.current;
    if (curr) observer.observe(curr);
    return () => { if (curr) observer.unobserve(curr); };
  }, [options]);

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
      <div className="fixed inset-0 bg-[#FAFAFA] -z-50" />

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
        <div className="absolute inset-0 bg-gradient-to-t from-[#FAFAFA] via-transparent to-transparent opacity-80" />
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
        className="group relative inline-flex items-center justify-center h-14 px-8 text-sm font-semibold text-white bg-[#0f172a] rounded-xl overflow-hidden shadow-lg shadow-[#0f172a]/20 transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5"
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
      className="group relative inline-flex items-center justify-center h-14 px-8 text-sm font-semibold text-[#0f172a] bg-white rounded-xl overflow-hidden transition-all duration-300 shadow-sm border border-black/5 hover:border-black/10 hover:shadow-md hover:-translate-y-0.5"
    >
      <div className="absolute inset-x-0 bottom-0 h-0 group-hover:h-full bg-black/[0.02] transition-all duration-300" />
      <span className="relative z-10 flex items-center gap-2">
        {children} {icon}
      </span>
    </Link>
  );
};

/* --- HERO SECTION --- */

const HeroSection: React.FC = () => {
  return (
    <section className="relative min-h-[100svh] flex flex-col justify-center items-center overflow-hidden px-6 pt-20">

      {/* Floating Network Background */}
      <div className="absolute inset-0 w-full h-full pointer-events-none z-0 overflow-hidden flex items-center justify-center">
        <div className="w-[100vw] h-[100vw] md:w-[60vw] md:h-[60vw] border border-black/[0.03] rounded-full animate-[spin_60s_linear_infinite]" />
        <div className="absolute w-[80vw] h-[80vw] md:w-[40vw] md:h-[40vw] border border-black/[0.04] border-dashed rounded-full animate-[spin_40s_linear_infinite_reverse]" />
        <div className="absolute w-[60vw] h-[60vw] md:w-[20vw] md:h-[20vw] border border-black/[0.05] rounded-full animate-[spin_20s_linear_infinite]" />
      </div>

      <div className="relative z-10 max-w-4xl w-full mx-auto flex flex-col items-center text-center mt-12 lg:mt-0">
        <GlassBadge text="Intelligent Risk Analysis" pulse />

        <div className="mt-8 mb-6 relative">
          <h1 className="text-[clamp(3rem,6vw,5.5rem)] font-bold leading-[1.05] tracking-[-0.03em] text-[]] drop-shadow-sm">
            <span className="block animate-slide-up-fade" style={{ animationDelay: '100ms' }}>
              Navigate the market
            </span>
            <span className="inline-block animate-slide-up-fade text-transparent bg-clip-text bg-gradient-to-r from-[#0f172a] via-[#0d9488] to-[#14b8a6]" style={{ animationDelay: '250ms' }}>
              with absolute clarity.
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
  const { ref, isVisible } = useIntersectionObserver({ threshold: 0.1 });

  return (
    <section className="relative z-10 py-32 px-6 max-w-7xl mx-auto" ref={ref}>
      <div className="mb-20 grid grid-cols-1 md:grid-cols-2 gap-8 items-end">
        <div>
          <h2 className="text-4xl md:text-5xl font-bold tracking-[-0.03em] text-[#0f172a] leading-[1.1]">
            Powerful analysis.<br />
            <span className="text-[#0d9488]">Simple design.</span>
          </h2>
        </div>
        <div>
          <p className="text-[#475569] text-lg font-medium leading-relaxed max-w-lg md:ml-auto">
            Real market intelligence shouldn't be complicated. We process millions of data points, so you see precisely what matters.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 auto-rows-min">

        {/* Feature 1 - Spans 8 cols */}
        <RevealCard className="md:col-span-8 group overflow-hidden" delay={0}>
          <div className="absolute inset-0 bg-gradient-to-br from-[#0d9488]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

          <div className="relative z-10 flex flex-col md:flex-row gap-10 items-center">
            <div className="flex-1">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#0d9488]/10 to-transparent border border-[#0d9488]/10 flex items-center justify-center text-[#0d9488] mb-6">
                <Search size={22} />
              </div>
              <h3 className="text-2xl font-bold text-[#0f172a] mb-3">Live Risk Categorization</h3>
              <p className="text-[#475569] font-medium leading-relaxed">Instantly know if it's safe to enter. Our system continuously analyzes 30+ technical metrics to provide clear risk bounds.</p>
            </div>

            {/* Unique Vertical Data Slot / Scanner Animation */}
            <div className="w-full md:w-[280px] h-[200px] relative rounded-2xl bg-white border border-black/5 overflow-hidden flex-shrink-0 group/slot flex justify-center items-center">
              {/* Center Highlight Scanner Box */}
              <div className="absolute inset-x-0 h-[64px] top-1/2 -translate-y-1/2 bg-[#fafafa]/80 border-y border-black/5 z-0" />
              <div className="absolute inset-x-0 h-[64px] top-1/2 -translate-y-1/2 z-20 pointer-events-none flex items-center justify-between px-6">
                <div className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse shadow-[0_0_12px_rgba(16,185,129,0.8)]" />
                <span className="text-[10px] font-bold text-[#10b981] uppercase tracking-[0.2em] font-mono">Risk: Safe</span>
              </div>

              {/* Rolling Icons Feed */}
              <div className="absolute flex flex-col animate-marquee-vertical group-hover/slot:[animation-play-state:paused] z-10 w-full pt-[68px]"> {/* Offset to align initial frame */}
                {[...Array(2)].map((_, i) => (
                  <div key={i} className="flex flex-col w-full">
                    {[
                      { icon: <BTCIcon />, symbol: "BTC" },
                      { icon: <ETHIcon />, symbol: "ETH" },
                      { icon: <SOLIcon />, symbol: "SOL" },
                      { icon: <XRPIcon />, symbol: "XRP" }
                    ].map((coin, j) => (
                      <div key={j} className="h-[64px] flex items-center gap-6 opacity-30 group-hover/slot:opacity-100 transition-all duration-500 w-full px-10 grayscale group-hover/slot:grayscale-0">
                        <div className="w-10 h-10 flex-shrink-0">{coin.icon}</div>
                        <span className="font-mono font-bold text-[#0f172a] tracking-tight">{coin.symbol}/USD</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>

              {/* Edge Fades for Seamless Loop Illusion */}
              <div className="absolute top-0 inset-x-0 h-16 bg-gradient-to-b from-white to-transparent z-20 pointer-events-none" />
              <div className="absolute bottom-0 inset-x-0 h-16 bg-gradient-to-t from-white to-transparent z-20 pointer-events-none" />
            </div>
          </div>
        </RevealCard>

        {/* Feature 2 - Spans 4 cols */}
        <RevealCard className="md:col-span-4 bg-[#0f172a] text-white border-none group" delay={150}>
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(13,148,136,0.2),transparent_50%)] opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
          <div className="h-full flex flex-col justify-end relative z-10">
            <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center text-white mb-6 backdrop-blur-md">
              <Zap size={22} className="group-hover:text-[#10b981] transition-colors duration-500" />
            </div>
            <h3 className="text-5xl font-mono tracking-tighter mb-3 font-bold">&lt;100<span className="text-[#0d9488] text-2xl ml-1">ms</span></h3>
            <p className="text-[#94a3b8] font-medium leading-relaxed">Lightning-fast, real-time market data processing.</p>
          </div>
        </RevealCard>

        {/* Feature 3 - Spans 4 cols */}
        <RevealCard className="md:col-span-4 group" delay={0}>
          <div className="h-full flex flex-col justify-between">
            <div className="w-12 h-12 rounded-xl bg-[#fafafa] border border-black/5 flex items-center justify-center text-[#0d9488] mb-6">
              <Eye size={22} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#0f172a] mb-2">Trend Detection</h3>
              <p className="text-[#475569] font-medium text-sm leading-relaxed">Automatically identifies market momentum—whether bull, bear, or completely sideways.</p>
            </div>
          </div>
        </RevealCard>

        {/* Feature 4 - Spans 8 cols */}
        <RevealCard className="md:col-span-8 group overflow-hidden" delay={150}>
          <div className="absolute right-0 top-0 w-1/2 h-full bg-[radial-gradient(circle_at_center,rgba(20,184,166,0.05),transparent_70%)] group-hover:opacity-100 opacity-0 transition-opacity duration-700" />

          <div className="relative z-10 flex flex-col md:flex-row gap-10 items-center h-full">
            <div className="flex-1">
              <div className="w-12 h-12 rounded-xl bg-[#fafafa] border border-black/5 flex items-center justify-center text-[#0d9488] mb-6">
                <BarChart size={22} />
              </div>
              <h3 className="text-2xl font-bold text-[#0f172a] mb-3">Smarter Indicators</h3>
              <p className="text-[#475569] font-medium leading-relaxed">
                RSI, MACD, and Bollinger Bands tracked natively and continuously, displayed only when there's an actionable signal.
              </p>
            </div>

            <div className="w-full md:w-auto mt-6 md:mt-0 relative group">
              <div className="p-6 rounded-2xl bg-white border border-black/[0.04] shadow-lg group-hover:-translate-y-2 transition-transform duration-500 ease-out-expo min-w-[200px]">
                <div className="flex justify-between items-center mb-6">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6"><BTCIcon /></div>
                    <span className="font-mono text-xs font-bold text-[#0a0a0a]">BTC/USD</span>
                  </div>
                  <span className="font-mono text-[10px] font-bold text-[#10b981] bg-[#10b981]/10 px-2 py-1 rounded-full">+4.2%</span>
                </div>
                <div className="h-12 w-full flex items-end justify-between gap-1 overflow-hidden">
                  {[30, 45, 60, 40, 70, 85, 55, 90].map((h, i) => (
                    <div
                      key={i}
                      className="w-full bg-[#0d9488] rounded-t-sm transform translate-y-[100%] group-hover:translate-y-0 transition-transform duration-700 ease-out-expo"
                      style={{ height: `${h}%`, transitionDelay: `${i * 50}ms`, opacity: (i + 1) / 8 }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </RevealCard>

      </div>
    </section>
  );
};

// 3. Immersive Typography Marquee Banner
const CryptoMarquee: React.FC = () => {
  const assets = [
    { icon: <BTCIcon />, label: "BITCOIN" },
    { icon: <ETHIcon />, label: "ETHEREUM" },
    { icon: <SOLIcon />, label: "SOLANA" },
    { icon: <XRPIcon />, label: "RIPPLE" }
  ];

  return (
    <section className="py-32 relative z-10 bg-[#FAFAFA] border-y border-black/[0.03] overflow-hidden flex">
      {/* Soft gradients for edge fading */}
      <div className="absolute left-0 top-0 bottom-0 w-32 md:w-64 bg-gradient-to-r from-[#FAFAFA] to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-32 md:w-64 bg-gradient-to-l from-[#FAFAFA] to-transparent z-10 pointer-events-none" />

      <div className="flex whitespace-nowrap animate-marquee w-max">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="flex items-center">
            {assets.map((asset, j) => (
              <div key={j} className="flex items-center gap-6 md:gap-12 mx-8 md:mx-16 group cursor-pointer transition-transform duration-700 hover:scale-[1.02]">
                <div className="w-16 h-16 md:w-20 md:h-20 opacity-30 grayscale group-hover:grayscale-0 group-hover:opacity-100 transition-all duration-500 drop-shadow-2xl">
                  {asset.icon}
                </div>
                <span
                  className="text-[4rem] md:text-[7.5rem] font-bold tracking-[-0.04em] text-transparent transition-all duration-700 group-hover:text-[#0f172a]"
                  style={{ WebkitTextStroke: '2px rgba(15, 23, 42, 0.1)' }}
                >
                  {asset.label}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

// 4. Data Flow Minimal Pipeline
const PipelineSection: React.FC = () => {
  const { ref, isVisible } = useIntersectionObserver({ threshold: 0.3 });

  return (
    <section ref={ref} className="py-32 relative z-10 px-6 max-w-5xl mx-auto flex flex-col items-center">
      <div className="text-center mb-24">
        <GlassBadge text="System Flow" />
        <h2 className="text-4xl font-bold tracking-[-0.03em] text-[#0f172a] mt-6 mb-4">
          Data doesn't sleep.
        </h2>
        <p className="text-[#475569] text-lg font-medium leading-relaxed max-w-2xl">
          From raw market feeds to clear dashboard visuals in milliseconds. Constant updates. Constant edge.
        </p>
      </div>

      <div className="w-full relative py-8">
        <div className="absolute top-1/2 left-[10%] w-[80%] h-[1px] bg-black/5 -translate-y-1/2 hidden md:block" />

        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 relative z-10">
          {[
            { icon: <Database />, title: "Ingest", desc: "Live ticks" },
            { icon: <Layers />, title: "Extract", desc: "Processing" },
            { icon: <Brain />, title: "Score", desc: "Analysis" },
            { icon: <BarChart3 />, title: "Render", desc: "Dashboards" }
          ].map((step, i) => (
            <div
              key={i}
              className={`flex flex-col items-center justify-center transition-all duration-700 ease-out-expo group
                                ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}
                            `}
              style={{ transitionDelay: `${i * 150}ms` }}
            >
              <div className="w-20 h-20 mb-5 rounded-2xl bg-white border border-black/5 shadow-sm flex items-center justify-center relative group-hover:shadow-[0_10px_30px_rgba(13,148,136,0.1)] group-hover:-translate-y-2 transition-all duration-500 ease-out-expo">
                <div className="absolute inset-0 rounded-2xl border border-[#0d9488]/20 scale-[1.15] opacity-0 group-hover:scale-110 group-hover:opacity-100 transition-all duration-500" />
                <div className="text-[#0f172a] group-hover:text-[#0d9488] transition-colors">{step.icon}</div>
              </div>
              <h4 className="font-bold text-[#0f172a]">{step.title}</h4>
              <span className="text-xs text-[#64748b] font-medium mt-1">{step.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

/* --- LAYOUT COMPONENT --- */

const LandingPage: React.FC = () => {
  const scrollY = useScrollPosition();

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
    .animate-blob { animation: blob 15s infinite alternate ease-in-out; }
    .animation-delay-2000 { animation-delay: 2s; }
    .animate-slide-up-fade { animation: slideUpFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; }
    .animate-marquee { animation: marquee 35s linear infinite; }
    .animate-marquee-reverse { animation: marquee-reverse 40s linear infinite; }
    .animate-marquee-vertical { animation: marquee-vertical 8s linear infinite; }
    .ease-out-expo { transition-timing-function: cubic-bezier(0.16, 1, 0.3, 1); }
  `;

  return (
    <div className="bg-[#FAFAFA] min-h-screen text-[#0f172a] font-sans selection:bg-[#0d9488]/20 selection:text-[#0d9488] overflow-hidden">
      <style dangerouslySetInnerHTML={{ __html: styles }} />

      <Atmosphere />

      <nav className={`fixed top-0 w-full z-50 transition-all duration-500 ease-out-expo ${scrollY > 20 ? 'bg-white/80 backdrop-blur-xl border-b border-black/[0.04] py-4' : 'bg-transparent py-6'}`}>
        <div className="max-w-[1280px] mx-auto px-6 flex justify-between items-center">

          <Logo />

          <div className="flex items-center gap-6 text-sm font-semibold">
            <Link to="/sentiment" className="text-[#475569] hover:text-[#0f172a] transition-colors hidden md:block">Technology</Link>
            <Link to="/dashboard" className="px-5 py-2.5 rounded-xl bg-[#0f172a] text-white hover:bg-[#0d9488] transition-colors shadow-sm">
              Launch System
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

      <footer className="relative z-10 bg-white border-t border-black/[0.04] pt-24 pb-12 px-6 overflow-hidden">
        {/* Dithering Shader Background */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.15] mix-blend-multiply z-0">
          <DitheringShader
            shape="wave"
            type="8x8"
            colorBack="#ffffff"
            colorFront="#0d9488"
            pxSize={3}
            speed={0.4}
          />
        </div>

        <div className="max-w-[1280px] mx-auto relative z-10">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8 border-b border-black/[0.04] pb-16">
            <div>
              <Logo size={20} />
              <p className="text-[#475569] font-medium max-w-sm mt-4">The cleanest standard for intelligent crypto risk analysis. Stop guessing, start knowing.</p>
            </div>
            <div className="flex gap-4">
              <Link to="/dashboard" className="relative group h-12 px-8 rounded-xl bg-white border border-[#0d9488]/20 flex items-center justify-center font-semibold text-[#0d9488] overflow-hidden transition-all hover:border-[#0d9488]">
                <div className="absolute inset-0 bg-[#0d9488]/5 group-hover:bg-[#0d9488]/10 transition-colors" />
                <span className="relative z-10">Access Dashboard</span>
              </Link>
            </div>
          </div>
          <div className="pt-8 flex flex-col md:flex-row justify-between items-center text-sm font-medium text-[#94a3b8]">
            <p>© {new Date().getFullYear()} CryptoRisk Lens. Online.</p>
            <div className="flex items-center gap-2 mt-4 md:mt-0">
              <div className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
              <span>All Systems Operational</span>
            </div>
          </div>
        </div>
      </footer>

    </div>
  );
};

export default LandingPage;
