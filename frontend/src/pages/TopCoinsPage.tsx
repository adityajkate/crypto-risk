import React, { useState, useEffect, useMemo } from 'react';
import { apiClient, PriceData } from '../services/apiClient';
import { formatLargeNumber, formatPrice, formatPercentage } from '../utils/formatters';
import { useCrypto } from '../context/CryptoContext';
import { useNavigate } from 'react-router-dom';

const TopCoinsPage: React.FC = () => {
  const [coins, setCoins] = useState<PriceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { setCurrency, setCoinId } = useCrypto();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchTopCoins = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await apiClient.getTopCoins(20);
        if (result.coins) {
          setCoins(result.coins);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to fetch top coins');
      } finally {
        setLoading(false);
      }
    };

    fetchTopCoins();
    const interval = setInterval(fetchTopCoins, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleCoinClick = (coin: PriceData) => {
    setCurrency(coin.name);
    setCoinId(coin.id);
    navigate('/dashboard');
  };

  // Calculate statistics
  const stats = useMemo(() => {
    if (coins.length === 0) return null;

    const topGainer = coins.reduce((max, coin) =>
      (coin.price_change_percentage_24h > max.price_change_percentage_24h) ? coin : max
    , coins[0]);

    const topLoser = coins.reduce((min, coin) =>
      (coin.price_change_percentage_24h < min.price_change_percentage_24h) ? coin : min
    , coins[0]);

    const totalMarketCap = coins.reduce((sum, coin) => sum + coin.market_cap, 0);
    const btcDominance = coins.find(c => c.symbol === 'BTC')?.market_cap || 0;
    const ethDominance = coins.find(c => c.symbol === 'ETH')?.market_cap || 0;

    const avgChange = coins.reduce((sum, coin) => sum + coin.price_change_percentage_24h, 0) / coins.length;

    return {
      topGainer,
      topLoser,
      totalMarketCap,
      btcDominance: (btcDominance / totalMarketCap) * 100,
      ethDominance: (ethDominance / totalMarketCap) * 100,
      avgChange
    };
  }, [coins]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading market data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-red-600 font-semibold mb-2">Failed to load data</p>
          <p className="text-slate-600 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Top 20 Cryptocurrencies</h1>
        <p className="text-slate-600 mt-2">Real-time market data and performance metrics</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Market Average */}
        <div className="bg-white rounded-xl p-6 border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-slate-600">Market Average</span>
            <svg className={`w-5 h-5 ${stats.avgChange >= 0 ? 'text-emerald-500' : 'text-red-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <div className={`text-3xl font-bold ${stats.avgChange >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
            {stats.avgChange >= 0 ? '+' : ''}{stats.avgChange.toFixed(2)}%
          </div>
          <p className="text-sm text-slate-500 mt-2">24h Change</p>
        </div>

        {/* BTC Dominance */}
        <div className="bg-white rounded-xl p-6 border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-slate-600">BTC Dominance</span>
            <svg className="w-5 h-5 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
            </svg>
          </div>
          <div className="text-3xl font-bold text-slate-900">
            {stats.btcDominance.toFixed(1)}%
          </div>
          <p className="text-sm text-slate-500 mt-2">Market Share</p>
        </div>

        {/* ETH Dominance */}
        <div className="bg-white rounded-xl p-6 border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-slate-600">ETH Dominance</span>
            <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="text-3xl font-bold text-slate-900">
            {stats.ethDominance.toFixed(1)}%
          </div>
          <p className="text-sm text-slate-500 mt-2">Market Share</p>
        </div>

        {/* Total Market Cap */}
        <div className="bg-white rounded-xl p-6 border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-slate-600">Total Market Cap</span>
            <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="text-3xl font-bold text-slate-900">
            {formatLargeNumber(stats.totalMarketCap)}
          </div>
          <p className="text-sm text-slate-500 mt-2">Top 20 Combined</p>
        </div>
      </div>

      {/* Top Performers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top Gainer */}
        <div className="bg-gradient-to-br from-emerald-50 to-white rounded-xl p-6 border border-emerald-200">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            <h3 className="text-lg font-semibold text-slate-900">Top Gainer (24h)</h3>
          </div>
          {stats.topGainer.id && (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {stats.topGainer.image && (
                  <img src={stats.topGainer.image} alt={stats.topGainer.name} className="w-10 h-10 rounded-full" />
                )}
                <div>
                  <div className="font-semibold text-slate-900">{stats.topGainer.name}</div>
                  <div className="text-sm text-slate-500">{stats.topGainer.symbol}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-emerald-600">
                  +{formatPercentage(stats.topGainer.price_change_percentage_24h)}
                </div>
                <div className="text-sm text-slate-600">
                  {formatPrice(stats.topGainer.current_price)}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Top Loser */}
        <div className="bg-gradient-to-br from-red-50 to-white rounded-xl p-6 border border-red-200">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
            </svg>
            <h3 className="text-lg font-semibold text-slate-900">Top Loser (24h)</h3>
          </div>
          {stats.topLoser.id && (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {stats.topLoser.image && (
                  <img src={stats.topLoser.image} alt={stats.topLoser.name} className="w-10 h-10 rounded-full" />
                )}
                <div>
                  <div className="font-semibold text-slate-900">{stats.topLoser.name}</div>
                  <div className="text-sm text-slate-500">{stats.topLoser.symbol}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-red-600">
                  {formatPercentage(stats.topLoser.price_change_percentage_24h)}
                </div>
                <div className="text-sm text-slate-600">
                  {formatPrice(stats.topLoser.current_price)}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Coins Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">#</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Name</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider">Price</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider">24h %</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider hidden md:table-cell">Market Cap</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider hidden lg:table-cell">Volume (24h)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {coins.map((coin) => {
                const isPositive = coin.price_change_percentage_24h > 0;

                return (
                  <tr
                    key={coin.id}
                    onClick={() => handleCoinClick(coin)}
                    className="hover:bg-slate-50 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {coin.market_cap_rank <= 3 && (
                          <svg className={`w-4 h-4 ${
                            coin.market_cap_rank === 1 ? 'text-yellow-500' :
                            coin.market_cap_rank === 2 ? 'text-slate-400' :
                            'text-amber-600'
                          }`} fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                        )}
                        <span className="font-semibold text-slate-900">{coin.market_cap_rank}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {coin.image && (
                          <img
                            src={coin.image}
                            alt={coin.name}
                            className="w-8 h-8 rounded-full"
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                        )}
                        <div>
                          <div className="font-semibold text-slate-900">{coin.name}</div>
                          <div className="text-sm text-slate-500">{coin.symbol}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="font-semibold text-slate-900">
                        {formatPrice(coin.current_price)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="inline-flex items-center gap-1">
                        <svg className={`w-4 h-4 ${isPositive ? 'text-emerald-600' : 'text-red-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          {isPositive ? (
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                          ) : (
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                          )}
                        </svg>
                        <span className={`font-semibold ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                          {isPositive ? '+' : ''}{formatPercentage(coin.price_change_percentage_24h)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right hidden md:table-cell">
                      <span className="text-slate-900">
                        {formatLargeNumber(coin.market_cap)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right hidden lg:table-cell">
                      <span className="text-slate-600">
                        {formatLargeNumber(coin.total_volume)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default TopCoinsPage;
