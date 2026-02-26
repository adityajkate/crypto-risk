// Number formatting utilities for financial data

export const formatLargeNumber = (value: number): string => {
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  if (absValue >= 1e12) {
    return `${sign}${(absValue / 1e12).toFixed(2)}T`;
  } else if (absValue >= 1e9) {
    return `${sign}${(absValue / 1e9).toFixed(2)}B`;
  } else if (absValue >= 1e6) {
    return `${sign}${(absValue / 1e6).toFixed(2)}M`;
  } else if (absValue >= 1e3) {
    return `${sign}${(absValue / 1e3).toFixed(2)}K`;
  }
  return `${sign}${absValue.toFixed(2)}`;
};

export const formatPercentage = (value: number, decimals: number = 2): string => {
  return `${value.toFixed(decimals)}%`;
};

export const formatPrice = (value: number): string => {
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const formatDecimal = (value: number, decimals: number = 2): string => {
  return value.toFixed(decimals);
};

// Standardized decimal places by metric type
export const formatIndicator = (value: number, type: 'percentage' | 'ratio' | 'index' | 'price' | 'volume'): string => {
  switch (type) {
    case 'percentage':
      return formatPercentage(value, 2);
    case 'ratio':
      return formatDecimal(value, 4);
    case 'index':
      return formatDecimal(value, 2);
    case 'price':
      return formatPrice(value);
    case 'volume':
      return formatLargeNumber(value);
    default:
      return formatDecimal(value, 2);
  }
};
