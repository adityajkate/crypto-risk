import React, { useState, useEffect, useRef } from 'react';
import { Search, X } from 'lucide-react';
import { apiClient } from '../services/apiClient';

interface CoinSuggestion {
  id: string;
  name: string;
  symbol: string;
  thumb?: string;
  large?: string;
}

interface CoinSearchProps {
  onSelectCoin: (coinId: string, coinName: string) => void;
}

const POPULAR_COINS = [
  { id: 'bitcoin', name: 'Bitcoin', symbol: 'BTC' },
  { id: 'ethereum', name: 'Ethereum', symbol: 'ETH' },
  { id: 'ripple', name: 'XRP', symbol: 'XRP' },
  { id: 'cardano', name: 'Cardano', symbol: 'ADA' },
  { id: 'solana', name: 'Solana', symbol: 'SOL' },
  { id: 'polkadot', name: 'Polkadot', symbol: 'DOT' },
  { id: 'dogecoin', name: 'Dogecoin', symbol: 'DOGE' },
  { id: 'avalanche-2', name: 'Avalanche', symbol: 'AVAX' },
];

const CoinSearch: React.FC<CoinSearchProps> = ({ onSelectCoin }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [suggestions, setSuggestions] = useState<CoinSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [imageErrors, setImageErrors] = useState<Set<string>>(new Set());
  const searchRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    if (searchTerm.length < 1) {
      setSuggestions(POPULAR_COINS);
      return;
    }

    const searchCoins = async () => {
      setLoading(true);
      abortControllerRef.current = new AbortController();

      try {
        const result = await apiClient.searchCoins(searchTerm, abortControllerRef.current.signal);

        if (result.coins) {
          setSuggestions(result.coins);
        }
      } catch (error: any) {
        if (error?.isAborted !== true && error?.name !== 'AbortError') {
          console.error('Search error:', error);
          setSuggestions(POPULAR_COINS);
        }
      } finally {
        setLoading(false);
      }
    };

    const debounce = setTimeout(searchCoins, 300);
    return () => {
      clearTimeout(debounce);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [searchTerm]);

  const handleSelect = (coin: CoinSuggestion) => {
    onSelectCoin(coin.id, coin.name);
    setSearchTerm('');
    setShowSuggestions(false);
  };

  const handleFocus = () => {
    setShowSuggestions(true);
    if (suggestions.length === 0) {
      setSuggestions(POPULAR_COINS);
    }
  };

  return (
    <div ref={searchRef} className="relative w-full sm:w-80">
      <div className="relative">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          size={18}
        />
        <input
          type="text"
          placeholder="Search cryptocurrency..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onFocus={handleFocus}
          aria-label="Search for cryptocurrency"
          role="combobox"
          aria-expanded={showSuggestions}
          aria-controls="coin-suggestions"
          aria-autocomplete="list"
          className="w-full pl-10 pr-10 py-2.5 bg-white border border-slate-300 rounded-lg focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 text-sm text-slate-900 transition-all placeholder:text-slate-400"
        />
        {searchTerm && (
          <button
            onClick={() => {
              setSearchTerm('');
              setSuggestions(POPULAR_COINS);
            }}
            aria-label="Clear search"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {showSuggestions && (
        <div id="coin-suggestions" className="absolute top-full left-0 right-0 mt-2 bg-white border border-slate-200 rounded-lg shadow-lg max-h-96 overflow-y-auto z-50" role="listbox">
          {loading ? (
            <div className="p-4 text-center text-slate-500 text-sm">
              Searching...
            </div>
          ) : suggestions.length > 0 ? (
            <>
              {searchTerm.length < 1 && (
                <div className="px-3 py-2 text-xs font-medium text-slate-500 border-b border-slate-100">
                  Popular Cryptocurrencies
                </div>
              )}
              {suggestions.map((coin) => (
                <button
                  key={coin.id}
                  onClick={() => handleSelect(coin)}
                  role="option"
                  aria-selected={false}
                  className="w-full px-3 py-2.5 flex items-center gap-3 hover:bg-slate-50 transition-colors text-left border-b border-slate-100 last:border-b-0"
                >
                  {coin.thumb && !imageErrors.has(coin.id) ? (
                    <img
                      src={coin.thumb}
                      alt={coin.name}
                      className="w-6 h-6 rounded-full"
                      onError={() => {
                        setImageErrors(prev => new Set(prev).add(coin.id));
                      }}
                    />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-xs font-medium text-slate-600">
                      {coin.symbol.charAt(0)}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-900 truncate">{coin.name}</div>
                    <div className="text-xs text-slate-500">{coin.symbol}</div>
                  </div>
                </button>
              ))}
            </>
          ) : (
            <div className="p-4 text-center text-slate-500 text-sm">
              No results found
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CoinSearch;
