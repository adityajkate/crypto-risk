import React from 'react';

export interface PricePoint {
  time: string;
  price: number;
  volatility: number;
}

export interface SentimentData {
  source: string;
  sentiment: 'Positive' | 'Negative' | 'Neutral';
  score: number;
  headline: string;
  timestamp: string;
}

export interface RiskMetric {
  name: string;
  value: number; // 0-100
  status: 'Low' | 'Medium' | 'High' | 'Critical';
  change: number;
}

export interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}