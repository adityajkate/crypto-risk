import React from 'react';
import { Bitcoin, CircleDollarSign, Hexagon, Gem, Coins } from 'lucide-react';

const AnimatedBackground: React.FC = () => {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      <div className="absolute inset-0 bg-white" />
      
      {/* Floating Elements */}
      <div className="absolute top-[15%] left-[10%] text-black/5 animate-float-1">
        <Bitcoin size={120} />
      </div>
      <div className="absolute top-[60%] right-[15%] text-black/5 animate-float-2">
        <Hexagon size={180} />
      </div>
      <div className="absolute bottom-[10%] left-[20%] text-black/5 animate-float-3">
        <CircleDollarSign size={90} />
      </div>
      <div className="absolute top-[30%] right-[30%] text-black/5 animate-float-1 delay-1000">
        <Gem size={140} />
      </div>
      <div className="absolute top-[80%] left-[5%] text-black/5 animate-float-2 delay-700">
        <Coins size={100} />
      </div>
      
      {/* Soft depth layer */}
      <div className="absolute top-1/4 left-1/4 size-96 bg-black/5 rounded-full blur-[96px] animate-glow" />
      <div className="absolute bottom-1/4 right-1/4 size-96 bg-black/5 rounded-full blur-[96px] animate-glow delay-1000" />
    </div>
  );
};

export default AnimatedBackground;
