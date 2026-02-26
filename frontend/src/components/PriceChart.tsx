import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Area, AreaChart } from 'recharts';
import { TrendingUp, BarChart3, Activity } from 'lucide-react';

interface ChartData {
  time: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  price?: number;
  volume?: number;
}

interface PriceChartProps {
  coinId: string;
  timeframe: '1H' | '24H' | '7D' | '1M';
  currentPrice: number;
}

type ChartType = 'line' | 'candlestick' | 'live';

// Generate human-readable Y-axis ticks
const generateYAxisTicks = (data: ChartData[]): number[] => {
  if (!data || data.length === 0) return [];

  const prices = data.map(d => d.price || d.close || 0).filter(p => p > 0);
  if (prices.length === 0) return [];

  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min;

  // Determine step size based on range
  let step: number;
  if (range > 10000) {
    step = 1000;
  } else if (range > 5000) {
    step = 500;
  } else if (range > 1000) {
    step = 200;
  } else if (range > 500) {
    step = 100;
  } else if (range > 100) {
    step = 50;
  } else {
    step = 10;
  }

  // Round min down and max up to nearest step
  const minTick = Math.floor(min / step) * step;
  const maxTick = Math.ceil(max / step) * step;

  // Generate ticks
  const ticks: number[] = [];
  for (let tick = minTick; tick <= maxTick; tick += step) {
    ticks.push(tick);
  }

  return ticks;
};

const PriceChart: React.FC<PriceChartProps> = ({ coinId, timeframe, currentPrice }) => {
  const [chartType, setChartType] = useState<ChartType>('line');
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [liveData, setLiveData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(false);

  // Generate chart data based on current price
  useEffect(() => {
    const generateChartData = () => {
      setLoading(true);
      try {
        let dataPoints = 24;
        let timeLabels: string[] = [];

        switch (timeframe) {
          case '1H':
            dataPoints = 12;
            timeLabels = Array.from({ length: dataPoints }, (_, i) => `${i * 5}m`);
            break;
          case '24H':
            dataPoints = 24;
            timeLabels = Array.from({ length: dataPoints }, (_, i) => {
              const hour = i.toString().padStart(2, '0');
              return `${hour}:00`;
            });
            break;
          case '7D':
            dataPoints = 7;
            timeLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
            break;
          case '1M':
            dataPoints = 30;
            timeLabels = Array.from({ length: dataPoints }, (_, i) => `Day ${i + 1}`);
            break;
        }

        const now = Date.now();
        const formatted = Array.from({ length: dataPoints }, (_, i) => {
          const basePrice = currentPrice * (0.98 + Math.random() * 0.04);
          const volatility = currentPrice * 0.01;

          return {
            time: timeLabels[i],
            timestamp: now - (dataPoints - i - 1) * 60000,
            open: basePrice,
            high: basePrice + Math.random() * volatility,
            low: basePrice - Math.random() * volatility,
            close: basePrice + (Math.random() - 0.5) * volatility,
            price: basePrice
          };
        });

        setChartData(formatted);
      } catch (error) {
        console.error('Failed to generate chart data:', error);
      } finally {
        setLoading(false);
      }
    };

    if (chartType === 'candlestick' || chartType === 'line') {
      generateChartData();
    }
  }, [coinId, timeframe, chartType, currentPrice]);

  // Live chart simulation
  useEffect(() => {
    if (chartType !== 'live') return;

    const initialData: ChartData[] = Array.from({ length: 30 }, (_, i) => ({
      time: `${i}s`,
      price: currentPrice + (Math.random() - 0.5) * currentPrice * 0.001
    }));
    setLiveData(initialData);

    const interval = setInterval(() => {
      setLiveData(prev => {
        const newData = [...prev.slice(1)];
        const lastPrice = prev[prev.length - 1].price || currentPrice;
        const change = (Math.random() - 0.5) * currentPrice * 0.0005;

        newData.push({
          time: new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
          }),
          price: lastPrice + change
        });

        return newData;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [chartType, currentPrice]);

  const renderCandlestick = (data: ChartData[]) => (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" strokeOpacity={0.3} vertical={false} />
        <XAxis
          dataKey="time"
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={{ stroke: '#e2e8f0' }}
          interval="preserveStartEnd"
          minTickGap={50}
          domain={['dataMin', 'dataMax']}
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={{ stroke: '#e2e8f0' }}
          domain={['dataMin - 100', 'dataMax + 100']}
          tickFormatter={(v) => {
            if (v >= 1000000) return `$${(v/1000000).toFixed(1)}M`;
            if (v >= 1000) return `$${(v/1000).toFixed(1)}K`;
            return `$${v.toFixed(0)}`;
          }}
          width={60}
          ticks={generateYAxisTicks(data)}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#ffffff',
            borderColor: '#e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.03)'
          }}
          formatter={(value: number, name: string) => {
            if (name === 'open') return [`$${value.toFixed(2)}`, 'Open'];
            if (name === 'high') return [`$${value.toFixed(2)}`, 'High'];
            if (name === 'low') return [`$${value.toFixed(2)}`, 'Low'];
            if (name === 'close') return [`$${value.toFixed(2)}`, 'Close'];
            return [`$${value.toFixed(2)}`, name];
          }}
          labelFormatter={(label) => `Time: ${label}`}
        />
        <Bar
          dataKey="high"
          fill="transparent"
          shape={(props: any) => {
            const { x, y, width, payload } = props;
            if (!payload.open || !payload.close || !payload.high || !payload.low) return null;

            const isGreen = payload.close >= payload.open;
            const color = isGreen ? '#10b981' : '#ef4444';
            const bodyHeight = Math.abs(payload.close - payload.open);
            const bodyY = Math.min(payload.close, payload.open);

            // Scale factors
            const priceRange = Math.max(...data.map(d => d.high || 0)) - Math.min(...data.map(d => d.low || 0));
            const chartHeight = 350;
            const scale = chartHeight / priceRange;

            const wickX = x + width / 2;
            const candleWidth = Math.max(width * 0.6, 2);

            return (
              <g>
                {/* Wick */}
                <line
                  x1={wickX}
                  y1={y}
                  x2={wickX}
                  y2={y + (payload.high - payload.low) * scale}
                  stroke={color}
                  strokeWidth={1}
                />
                {/* Body */}
                <rect
                  x={x + (width - candleWidth) / 2}
                  y={y + (payload.high - Math.max(payload.open, payload.close)) * scale}
                  width={candleWidth}
                  height={Math.max(bodyHeight * scale, 1)}
                  fill={color}
                  stroke={color}
                />
              </g>
            );
          }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );

  const renderLineChart = (data: ChartData[]) => (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0f766e" stopOpacity={0.15}/>
            <stop offset="95%" stopColor="#0f766e" stopOpacity={0}/>
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" strokeOpacity={0.3} vertical={false} />
        <XAxis
          dataKey="time"
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={{ stroke: '#e2e8f0' }}
          interval="preserveStartEnd"
          minTickGap={50}
          domain={['dataMin', 'dataMax']}
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={{ stroke: '#e2e8f0' }}
          domain={['dataMin - 100', 'dataMax + 100']}
          tickFormatter={(v) => {
            if (v >= 1000000) return `$${(v/1000000).toFixed(1)}M`;
            if (v >= 1000) return `$${(v/1000).toFixed(1)}K`;
            return `$${v.toFixed(0)}`;
          }}
          width={60}
          ticks={generateYAxisTicks(data)}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#ffffff',
            borderColor: '#e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.03)'
          }}
          itemStyle={{ color: '#0f172a' }}
          labelStyle={{ color: '#64748b', fontWeight: 600 }}
          formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
        />
        <Area
          type="monotone"
          dataKey="price"
          stroke="#0f766e"
          strokeWidth={1.25}
          fillOpacity={1}
          fill="url(#colorPrice)"
          filter="url(#glow)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );

  const renderLiveChart = () => (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={liveData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="colorLive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
            <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis
          dataKey="time"
          stroke="#64748b"
          fontSize={11}
          tickLine={false}
          axisLine={{ stroke: '#e2e8f0' }}
          interval="preserveEnd"
          minTickGap={80}
        />
        <YAxis
          stroke="#64748b"
          fontSize={11}
          tickLine={false}
          axisLine={{ stroke: '#e2e8f0' }}
          domain={['dataMin - 10', 'dataMax + 10']}
          tickFormatter={(v) => {
            if (v >= 1000000) return `$${(v/1000000).toFixed(1)}M`;
            if (v >= 1000) return `$${(v/1000).toFixed(1)}K`;
            return `$${v.toFixed(0)}`;
          }}
          width={60}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#ffffff',
            borderColor: '#e2e8f0',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
          }}
          itemStyle={{ color: '#0f172a' }}
          labelStyle={{ color: '#64748b', fontWeight: 600 }}
          formatter={(value: number) => [`$${value.toFixed(2)}`, 'Live Price']}
        />
        <Area
          type="monotone"
          dataKey="price"
          stroke="#10b981"
          strokeWidth={2}
          fillOpacity={1}
          fill="url(#colorLive)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          onClick={() => setChartType('line')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            chartType === 'line'
              ? 'bg-teal-600 text-white shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <TrendingUp size={14} />
          Line
        </button>
        <button
          onClick={() => setChartType('candlestick')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            chartType === 'candlestick'
              ? 'bg-teal-600 text-white shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <BarChart3 size={14} />
          Candlestick
        </button>
        <button
          onClick={() => setChartType('live')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            chartType === 'live'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <Activity size={14} />
          Live
        </button>
      </div>

      <div className="h-[350px] w-full">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
          </div>
        ) : chartType === 'candlestick' ? (
          renderCandlestick(chartData)
        ) : chartType === 'live' ? (
          renderLiveChart()
        ) : (
          renderLineChart(chartData)
        )}
      </div>
    </div>
  );
};

export default PriceChart;
