import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import { apiClient, CoinAnalysis, PriceData } from '../services/apiClient';

interface CryptoContextType {
  currency: string;
  coinId: string;
  setCurrency: (c: string) => void;
  setCoinId: (id: string) => void;
  analysis: CoinAnalysis | null;
  priceData: PriceData | null;
  loading: boolean;
  error: string | null;
  refreshData: () => Promise<void>;
}

const CryptoContext = createContext<CryptoContextType | undefined>(undefined);

// Map common currency names to CoinGecko IDs
const currencyToCoinId = (currency: string): string => {
  const mapping: Record<string, string> = {
    'bitcoin': 'bitcoin',
    'btc': 'bitcoin',
    'ethereum': 'ethereum',
    'eth': 'ethereum',
    'ripple': 'ripple',
    'xrp': 'ripple',
    'cardano': 'cardano',
    'ada': 'cardano',
    'solana': 'solana',
    'sol': 'solana',
    'polkadot': 'polkadot',
    'dot': 'polkadot',
    'dogecoin': 'dogecoin',
    'doge': 'dogecoin',
  };

  const normalized = currency.toLowerCase().trim();
  return mapping[normalized] || normalized;
};

export const CryptoProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currency, setCurrencyState] = useState('Bitcoin');
  const [coinId, setCoinId] = useState('bitcoin');
  const [analysis, setAnalysis] = useState<CoinAnalysis | null>(null);
  const [priceData, setPriceData] = useState<PriceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchData = async (id: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const [analysisData, priceInfo] = await Promise.all([
        apiClient.getCoinAnalysis(id, 30, signal),
        apiClient.getCoinPrice(id, signal)
      ]);
      console.log('CryptoContext - Fetched data:', { analysisData, priceInfo });
      setAnalysis(analysisData);
      setPriceData(priceInfo);
    } catch (err: any) {
      // Only show error if it's not an aborted request
      if (err?.isAborted !== true && err?.name !== 'AbortError') {
        setError(err?.userMessage || err?.message || 'Failed to fetch data');
        console.error('Error fetching crypto data:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const setCurrency = (c: string) => {
    setCurrencyState(c);
    const id = currencyToCoinId(c);
    setCoinId(id);
  };

  const refreshData = async () => {
    const controller = new AbortController();
    await fetchData(coinId, controller.signal);
  };

  useEffect(() => {
    // Cancel any pending requests when coinId changes
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    fetchData(coinId, controller.signal);

    // Polling interval: 30 seconds (reduced from 5s to avoid API quota issues)
    const POLLING_INTERVAL = parseInt(import.meta.env.VITE_POLLING_INTERVAL || '30000');
    let intervalId: NodeJS.Timeout;

    const startPolling = () => {
      intervalId = setInterval(() => {
        // Only poll if page is visible
        if (document.visibilityState === 'visible') {
          const priceController = new AbortController();
          apiClient.getCoinPrice(coinId, priceController.signal)
            .then(priceInfo => setPriceData(priceInfo))
            .catch(err => {
              if (err?.isAborted !== true && err?.name !== 'AbortError') {
                console.error('Error fetching live price:', err);
              }
            });
        }
      }, POLLING_INTERVAL);
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // Refresh immediately when tab becomes visible
        const visibilityController = new AbortController();
        apiClient.getCoinPrice(coinId, visibilityController.signal)
          .then(priceInfo => setPriceData(priceInfo))
          .catch(err => {
            if (err?.isAborted !== true && err?.name !== 'AbortError') {
              console.error('Error fetching live price:', err);
            }
          });
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    startPolling();

    return () => {
      // Don't abort the controller here - let the fetch complete
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [coinId]);

  return (
    <CryptoContext.Provider value={{
      currency,
      coinId,
      setCurrency,
      setCoinId,
      analysis,
      priceData,
      loading,
      error,
      refreshData
    }}>
      {children}
    </CryptoContext.Provider>
  );
};

export const useCrypto = () => {
  const context = useContext(CryptoContext);
  if (!context) {
    throw new Error('useCrypto must be used within a CryptoProvider');
  }
  return context;
};