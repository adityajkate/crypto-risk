import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Area, AreaChart } from 'recharts';
import { TrendingUp, BarChart3, Activity } from 'lucide-react';
import { apiClient } from '../services/apiClient';

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
  currentPrice: number;
}

type ChartType = 'line' | 'candlestick' | 'live';

// Custom Candlestick Tooltip
const CandlestickTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length > 0) {
    const data = payload[0].payload;

    if (!data || !data.timestamp) return null;

    const date = new Date(data.timestamp);
    const dateStr = date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }) + ' ' + date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });

    const formatPrice = (price: number) => {
      if (!price) return 'N/A';
      return price >= 1 ? `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : `$${price.toFixed(6)}`;
    };

    return (
      <div style={{
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        boxShadow: '0 10px 40px rgba(0,0,0,0.12)',
        padding: '12px 16px',
        minWidth: '200px'
      }}>
        <p style={{
          color: '#0f172a',
          fontWeight: 600,
          marginBottom: '8px',
          fontSize: '13px',
          borderBottom: '1px solid #e2e8f0',
          paddingBottom: '6px'
        }}>{dateStr}</p>
        <div style={{ fontSize: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '20px', padding: '4px 0' }}>
            <span style={{ color: '#64748b' }}>Open:</span>
            <span style={{ color: '#0f172a', fontWeight: 600, fontFamily: 'monospace' }}>{formatPrice(data.open)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '20px', padding: '4px 0' }}>
            <span style={{ color: '#64748b' }}>High:</span>
            <span style={{ color: '#10b981', fontWeight: 600, fontFamily: 'monospace' }}>{formatPrice(data.high)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '20px', padding: '4px 0' }}>
            <span style={{ color: '#64748b' }}>Low:</span>
            <span style={{ color: '#ef4444', fontWeight: 600, fontFamily: 'monospace' }}>{formatPrice(data.low)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '20px', padding: '4px 0' }}>
            <span style={{ color: '#64748b' }}>Close:</span>
            <span style={{ color: '#0f172a', fontWeight: 600, fontFamily: 'monospace' }}>{formatPrice(data.close)}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

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

const PriceChart: React.FC<PriceChartProps> = ({ coinId, currentPrice }) => {
  const [chartType, setChartType] = useState<ChartType>('line');
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [liveData, setLiveData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch real OHLC data from backend
  useEffect(() => {
    const controller = new AbortController();

    const fetchOHLCData = async () => {
      setLoading(true);
      try {
        if (!currentPrice || currentPrice === 0) {
          setLoading(false);
          return;
        }

        // Fixed 7-day timeframe with 4-hour candles
        const days = 7;
        const result = await apiClient.getOHLC(coinId, days, controller.signal);

        if (result && Array.isArray(result.ohlc) && result.ohlc.length > 0) {
          // Show all 7-day data (42 candles with 4-hour intervals)
          const filteredData = result.ohlc;

          // Format time labels: Show date only (Feb 26) for cleaner x-axis
          const formatted = filteredData.map((item: any) => {
            const date = new Date(item.timestamp);
            const timeLabel = date.toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric'
            });

            return {
              time: timeLabel,
              timestamp: item.timestamp,
              open: item.open,
              high: item.high,
              low: item.low,
              close: item.close,
              price: item.close
            };
          });

          setChartData(formatted);
        }
      } catch (error: any) {
        // Don't show error if request was cancelled
        if (error?.isAborted !== true && error?.name !== 'AbortError') {
          console.error('Failed to fetch OHLC data:', error?.userMessage || error?.message || error);
        }
      } finally {
        setLoading(false);
      }
    };

    if (chartType === 'candlestick' || chartType === 'line') {
      fetchOHLCData();
    }

    return () => {
      controller.abort();
    };
  }, [coinId, chartType, currentPrice]);

  // Live chart - poll real price from backend
  useEffect(() => {
    if (chartType !== 'live') {
      setLiveData([]);
      return;
    }

    // Initialize with current price
    const now = new Date();
    const initialData: ChartData[] = Array.from({ length: 20 }, (_, i) => {
      const time = new Date(now.getTime() - (19 - i) * 3000); // 3 seconds apart
      return {
        time: time.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        }),
        price: currentPrice
      };
    });
    setLiveData(initialData);

    // Fetch immediately on mount
    const fetchPrice = async () => {
      try {
        const result = await apiClient.getCoinPrice(coinId);

        if (result && result.current_price) {
          const newPrice = result.current_price;
          const now = new Date();

          setLiveData(prev => {
            const newData = [...prev.slice(1)];
            newData.push({
              time: now.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
              }),
              price: newPrice
            });
            return newData;
          });
        }
      } catch (error) {
        console.error('Failed to fetch live price:', error);
      }
    };

    // Fetch immediately
    fetchPrice();

    // Then poll every 3 seconds for smoother updates
    const interval = setInterval(fetchPrice, 3000);

    return () => {
      clearInterval(interval);
      setLiveData([]);
    };
  }, [chartType, currentPrice, coinId]);

  const renderCandlestick = (data: ChartData[]) => {
    if (!data || data.length === 0) {
      return (
        <div className="flex items-center justify-center h-full text-slate-500">
          No data available for this timeframe
        </div>
      );
    }

    return (
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 20, right: 40, left: 10, bottom: 20 }}>
          <defs>
            <linearGradient id="gridGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f1f5f9" stopOpacity={0.8}/>
              <stop offset="100%" stopColor="#f1f5f9" stopOpacity={0.2}/>
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="url(#gridGradient)"
            vertical={false}
            strokeWidth={1}
          />
          <XAxis
            dataKey="time"
            stroke="#94a3b8"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#cbd5e1', strokeWidth: 1.5 }}
            height={50}
            interval="preserveStartEnd"
            tick={{ fill: '#64748b', fontWeight: 500 }}
          />
          <YAxis
            stroke="#94a3b8"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#cbd5e1', strokeWidth: 1.5 }}
            domain={['auto', 'auto']}
            tickFormatter={(v) => {
              if (v >= 1000000) return `$${(v/1000000).toFixed(2)}M`;
              if (v >= 1000) return `$${(v/1000).toFixed(1)}K`;
              if (v >= 1) return `$${v.toFixed(2)}`;
              return `$${v.toFixed(4)}`;
            }}
            width={85}
            tick={{ fill: '#64748b', fontWeight: 500 }}
          />
          <Tooltip content={<CandlestickTooltip />} />
          <Bar
            dataKey="high"
            fill="transparent"
            shape={(props: any) => {
              const { x, y, width, payload, height } = props;
              if (!payload.open || !payload.close || !payload.high || !payload.low) return null;

              const isGreen = payload.close >= payload.open;
              const color = isGreen ? '#10b981' : '#ef4444';

              // Get chart dimensions
              const yScale = height / (Math.max(...data.map(d => d.high || 0)) - Math.min(...data.map(d => d.low || 0)));

              const wickX = x + width / 2;
              const candleWidth = Math.max(Math.min(width * 0.7, 14), 4);

              // Calculate positions
              const highY = y;
              const lowY = y + (payload.high - payload.low) * yScale;
              const openY = y + (payload.high - payload.open) * yScale;
              const closeY = y + (payload.high - payload.close) * yScale;
              const bodyTop = Math.min(openY, closeY);
              const bodyHeight = Math.max(Math.abs(closeY - openY), 2);

              return (
                <g>
                  {/* Wick with shadow */}
                  <line
                    x1={wickX}
                    y1={highY}
                    x2={wickX}
                    y2={lowY}
                    stroke={color}
                    strokeWidth={2}
                    opacity={0.9}
                  />
                  {/* Body with gradient */}
                  <defs>
                    <linearGradient id={`candle-${x}-${isGreen ? 'green' : 'red'}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={color} stopOpacity={1}/>
                      <stop offset="100%" stopColor={color} stopOpacity={0.8}/>
                    </linearGradient>
                  </defs>
                  <rect
                    x={x + (width - candleWidth) / 2}
                    y={bodyTop}
                    width={candleWidth}
                    height={bodyHeight}
                    fill={`url(#candle-${x}-${isGreen ? 'green' : 'red'})`}
                    stroke={color}
                    strokeWidth={1.5}
                    rx={2}
                  />
                </g>
              );
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    );
  };

  const renderLineChart = (data: ChartData[]) => {
    if (!data || data.length === 0) {
      return (
        <div className="flex items-center justify-center h-full text-slate-500">
          No data available for this timeframe
        </div>
      );
    }

    return (
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 20, right: 40, left: 10, bottom: 20 }}>
          <defs>
            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0d9488" stopOpacity={0.3}/>
              <stop offset="50%" stopColor="#14b8a6" stopOpacity={0.15}/>
              <stop offset="95%" stopColor="#5eead4" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="gridGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f1f5f9" stopOpacity={0.8}/>
              <stop offset="100%" stopColor="#f1f5f9" stopOpacity={0.2}/>
            </linearGradient>
            <filter id="shadow">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0d9488" floodOpacity="0.3"/>
            </filter>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="url(#gridGradient)"
            vertical={false}
            strokeWidth={1}
          />
          <XAxis
            dataKey="time"
            stroke="#94a3b8"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#cbd5e1', strokeWidth: 1.5 }}
            height={50}
            interval="preserveStartEnd"
            tick={{ fill: '#64748b', fontWeight: 500 }}
          />
          <YAxis
            stroke="#94a3b8"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#cbd5e1', strokeWidth: 1.5 }}
            domain={['auto', 'auto']}
            tickFormatter={(v) => {
              if (v >= 1000000) return `$${(v/1000000).toFixed(2)}M`;
              if (v >= 1000) return `$${(v/1000).toFixed(1)}K`;
              if (v >= 1) return `$${v.toFixed(2)}`;
              return `$${v.toFixed(4)}`;
            }}
            width={85}
            tick={{ fill: '#64748b', fontWeight: 500 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.98)',
              borderColor: '#14b8a6',
              borderRadius: '12px',
              boxShadow: '0 10px 40px rgba(13, 148, 136, 0.15)',
              padding: '12px 16px',
              border: '1px solid #99f6e4'
            }}
            itemStyle={{ color: '#0f172a', fontSize: '12px', fontWeight: 500 }}
            labelStyle={{ color: '#0f172a', fontWeight: 600, marginBottom: '8px', fontSize: '13px' }}
            formatter={(value: number) => {
              const formatted = value >= 1 ? `$${value.toFixed(2)}` : `$${value.toFixed(6)}`;
              return [formatted, 'Price'];
            }}
          />
          <Area
            type="monotone"
            dataKey="price"
            stroke="#0d9488"
            strokeWidth={2.5}
            fillOpacity={1}
            fill="url(#colorPrice)"
            dot={false}
            filter="url(#shadow)"
            animationDuration={800}
          />
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  const renderLiveChart = () => (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={liveData} margin={{ top: 20, right: 40, left: 10, bottom: 20 }}>
        <defs>
          <linearGradient id="colorLive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0d9488" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#0d9488" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis
          dataKey="time"
          stroke="#94a3b8"
          fontSize={11}
          tickLine={false}
          axisLine={{ stroke: '#cbd5e1', strokeWidth: 1.5 }}
          interval="preserveEnd"
          tick={{ fill: '#64748b', fontWeight: 500 }}
        />
        <YAxis
          stroke="#94a3b8"
          fontSize={11}
          tickLine={false}
          axisLine={{ stroke: '#cbd5e1', strokeWidth: 1.5 }}
          domain={['dataMin - 0.5', 'dataMax + 0.5']}
          tickFormatter={(v) => {
            if (v >= 1000000) return `$${(v/1000000).toFixed(2)}M`;
            if (v >= 1000) return `$${(v/1000).toFixed(1)}K`;
            if (v >= 1) return `$${v.toFixed(2)}`;
            return `$${v.toFixed(4)}`;
          }}
          width={85}
          tick={{ fill: '#64748b', fontWeight: 500 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(255, 255, 255, 0.98)',
            borderColor: '#14b8a6',
            borderRadius: '12px',
            boxShadow: '0 10px 40px rgba(13, 148, 136, 0.15)',
            padding: '12px 16px',
            border: '1px solid #99f6e4'
          }}
          itemStyle={{ color: '#0f172a', fontSize: '12px', fontWeight: 500 }}
          labelStyle={{ color: '#0f172a', fontWeight: 600, marginBottom: '8px', fontSize: '13px' }}
          formatter={(value: number) => {
            const formatted = value >= 1 ? `$${value.toFixed(2)}` : `$${value.toFixed(6)}`;
            return [formatted, 'Price'];
          }}
        />
        <Area
          type="monotone"
          dataKey="price"
          stroke="#0d9488"
          strokeWidth={2.5}
          fillOpacity={1}
          fill="url(#colorLive)"
          isAnimationActive={false}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );

  return (
    <div className="space-y-3">
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
