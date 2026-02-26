export const getSeed = (str: string) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash);
};

export const generateSeries = (seed: number, length: number, base: number, variance: number) => {
  return Array.from({ length }, (_, i) => {
    // Deterministic pseudo-random using sin
    const randomFactor = Math.abs(Math.sin(seed + i * 132.1));
    return base + (randomFactor * variance) - (variance / 2);
  });
};

/**
 * Seeded random number generator for consistent chart data
 * Replaces Math.random() to enable proper memoization
 */
export const seededRandom = (seed: number, index: number): number => {
  const x = Math.sin(seed + index * 9999.9) * 10000;
  return x - Math.floor(x);
};