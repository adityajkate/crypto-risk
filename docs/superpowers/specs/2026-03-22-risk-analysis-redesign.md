# Risk Analysis Page Redesign - March 22, 2026

## Problem Statement

The current Risk Analysis page shows ML-powered risk data (XGBoost classifier, volatility forecasts, technical indicators) but doesn't help users understand what action to take. Users see "Medium Risk 39%" but don't know if they should buy, sell, wait, or ignore it. The page is data-rich but conclusion-poor.

## Goal

Transform the Risk Analysis page from a data dashboard into an actionable decision-support tool. Users should immediately understand:
1. What the risk assessment means for their investment decisions
2. Why the system reached that conclusion
3. What the technical indicators mean in plain English

## Design Overview

Add a prominent "Investment Recommendation" card at the top of the page that provides clear, actionable guidance based on the ML risk assessment. Enhance existing sections with plain English interpretations of technical metrics.

## Architecture

### Component Structure

```
RiskPage
├── Header (existing)
├── InvestmentRecommendationCard (NEW)
│   ├── Risk-colored background
│   ├── Icon (AlertTriangle/AlertCircle/CheckCircle)
│   ├── Main action text
│   ├── 2-3 reasoning bullets
│   ├── Risk badge
│   └── Disclaimer
├── Risk Assessment Card (enhanced)
├── Volatility Forecast (enhanced)
├── Risk Factors Grid (enhanced)
├── Alert Section (enhanced)
└── Info Notice (existing)
```

### Data Flow

```
Backend API (/api/v1/coin/{coin_id}/analysis)
    ↓
risk_analysis object
    ↓
Frontend RiskPage component
    ↓
├── Extract risk_assessment (risk_label, probabilities, confidence, features)
├── Extract volatility_forecast (predicted, current_7d, current_30d)
├── Extract market_regime (regime_name, description)
    ↓
Generate recommendation logic (NEW)
    ↓
Render InvestmentRecommendationCard + enhanced sections
```

## Detailed Design

### 1. Investment Recommendation Card (NEW)

**Purpose:** Provide immediate, actionable investment guidance based on ML risk assessment.

**Placement:** Top of page, immediately after header, before Risk Assessment card.

**Visual Design:**
- Large card with risk-colored background:
  - High Risk: `bg-red-50 border-red-200`
  - Medium Risk: `bg-yellow-50 border-yellow-200`
  - Low Risk: `bg-emerald-50 border-emerald-200`
- Left side: Icon matching risk level
  - High: `<AlertTriangle className="text-red-600" size={32} />`
  - Medium: `<AlertCircle className="text-yellow-600" size={32} />`
  - Low: `<CheckCircle className="text-emerald-600" size={32} />`
- Center: Main recommendation text (text-xl font-bold)
- Below: 2-3 bullet points (text-sm)
- Right side: Risk badge (reused from Risk Assessment card)
- Bottom: Disclaimer text (text-xs text-slate-500)

**Recommendation Logic:**

#### High Risk (risk_label === 'high')
- **Action:** "Exercise Caution" or "Consider Waiting"
- **Bullets:**
  1. "XGBoost model shows {high_probability}% high risk probability"
  2. Volatility context:
     - If current_volatility_30d > 0.05: "30-day volatility at {X}%, above normal levels"
     - Else: "Elevated risk despite moderate volatility"
  3. Market regime context:
     - If regime === 'high_vol_crisis': "High volatility crisis regime detected"
     - Else: "Market conditions show elevated risk signals"

#### Medium Risk (risk_label === 'medium')
- **Action:** "Proceed with Caution" or "Monitor Closely"
- **Bullets:**
  1. Probability context:
     - If medium_prob - low_prob < 10%: "Mixed signals - {medium}% medium risk, {low}% low risk"
     - Else: "{medium}% medium risk probability detected"
  2. Key risk factor (highest score from risk factors):
     - If RSI > 70: "RSI indicates overbought conditions"
     - If volatility_30d > 0.04: "Volatility elevated above comfort zone"
     - Else: "Technical indicators show moderate risk"
  3. Market regime: "{regime_name} - {regime_description}"

#### Low Risk (risk_label === 'low')
- **Action:** "Favorable Conditions" or "Lower Risk Entry"
- **Bullets:**
  1. "XGBoost shows {low_probability}% low risk probability"
  2. Stability indicators:
     - If current_volatility_30d < 0.03: "Volatility below average, stable conditions"
     - Else: "Risk indicators show healthy levels"
  3. Regime context:
     - If regime === 'low_vol_stable': "Low volatility stable regime"
     - Else: "Market conditions relatively favorable"

**Disclaimer:** "Not financial advice. Always do your own research."

**Implementation:**
```typescript
const getInvestmentRecommendation = (riskAssessment, volatilityData, marketRegime) => {
  const { risk_label, probabilities, features } = riskAssessment;
  const { current_volatility_30d } = volatilityData;
  const { regime_name, description } = marketRegime;

  // Generate action, bullets, icon, colors based on logic above
  return { action, bullets, icon, bgColor, textColor, borderColor };
};
```

### 2. Enhanced Risk Assessment Card

**Changes:**
- Add plain English summary below risk label:
  ```typescript
  const riskSummary = {
    high: "This cryptocurrency is experiencing elevated risk levels",
    medium: "This cryptocurrency shows mixed risk signals",
    low: "This cryptocurrency is in a relatively stable state"
  };
  ```

- Add confidence interpretation:
  ```typescript
  const confidenceText =
    confidence < 40 ? "Low confidence - model is uncertain" :
    confidence < 60 ? "Moderate confidence" :
    "High confidence - strong signal";
  ```

- Keep existing: probabilities grid, market regime box

### 3. Enhanced Risk Factors Grid

**Add plain English interpretation below each factor:**

```typescript
const getRiskFactorInterpretation = (factorName, value, score) => {
  switch(factorName) {
    case 'Volatility Risk':
      return score > 70 ? "High price swings expected" :
             score > 40 ? "Moderate price swings expected" :
             "Relatively stable price movement";

    case 'Drawdown Risk':
      return `Down ${Math.abs(value)}% from peak`;

    case 'RSI Indicator':
      const rsi = parseFloat(value);
      return rsi > 70 ? "Overbought - potential pullback" :
             rsi < 30 ? "Oversold - potential bounce" :
             "Neutral territory";

    case 'Momentum Risk':
      return value > 0 ? "Positive short-term momentum" :
             value < 0 ? "Negative short-term momentum" :
             "Flat momentum";
  }
};
```

**Visual:**
- Add interpretation text below progress bar in `text-xs text-slate-600`
- Keep existing: colored progress bars, hover effects

### 4. Enhanced Volatility Forecast

**Add interpretation row below the three cards:**

```typescript
const getVolatilityTrend = (predicted, current7d) => {
  const change = ((predicted - current7d) / current7d) * 100;

  if (change > 10) {
    return {
      text: "⚠️ Volatility expected to increase",
      color: "text-red-600",
      icon: <TrendingUp className="text-red-600" size={16} />
    };
  } else if (change < -10) {
    return {
      text: "✓ Volatility expected to decrease",
      color: "text-emerald-600",
      icon: <TrendingDown className="text-emerald-600" size={16} />
    };
  } else {
    return {
      text: "→ Volatility expected to remain stable",
      color: "text-slate-600",
      icon: <Activity className="text-slate-600" size={16} />
    };
  }
};
```

**Visual:**
- Add trend indicator below the three cards
- Small icon + text in appropriate color

### 5. Enhanced Market Regime

**Add "What this means" interpretation:**

```typescript
const getRegimeInterpretation = (regimeName) => {
  const interpretations = {
    low_vol_stable: "Calm market conditions. Lower risk of sudden price swings.",
    moderate_transition: "Market in flux. Conditions may shift quickly - stay alert.",
    high_vol_crisis: "Turbulent conditions. Expect large price movements and uncertainty."
  };
  return interpretations[regimeName] || "Market conditions being analyzed.";
};
```

**Visual:**
- Add interpretation text below description in `text-sm text-slate-700`
- Keep existing: Activity icon, gray box styling

### 6. Enhanced Alert Section

**Make alert more specific and actionable:**

```typescript
const getHighRiskAlert = (riskAssessment, riskFactors) => {
  const highProb = (riskAssessment.probabilities.high * 100).toFixed(0);

  // Find highest risk factor
  const highestFactor = riskFactors.reduce((max, factor) =>
    factor.score > max.score ? factor : max
  );

  return {
    title: `High Risk Detected for ${currency.toUpperCase()}`,
    bullets: [
      `XGBoost classifier indicates ${highProb}% high risk probability`,
      `Key concern: ${highestFactor.name} at elevated levels`,
      `Recommendation: Exercise caution or wait for improved conditions`
    ]
  };
};
```

**Visual:**
- Keep existing: red background, AlertCircle icon
- Replace generic text with specific bullets

## Implementation Notes

### Frontend Changes
- **File:** `frontend/src/pages/RiskPage.tsx`
- **New component:** `InvestmentRecommendationCard` (can be inline or separate component)
- **New utility functions:**
  - `getInvestmentRecommendation()`
  - `getRiskFactorInterpretation()`
  - `getVolatilityTrend()`
  - `getRegimeInterpretation()`
  - `getHighRiskAlert()`

### Backend Changes
- **None required** - all data already available in `/api/v1/coin/{coin_id}/analysis` response
- Recommendation logic is frontend-only (deterministic based on ML outputs)

### Styling
- Use existing Tailwind classes
- Match current light theme (bg-white, border-slate-200)
- Risk-colored backgrounds: red-50, yellow-50, emerald-50
- Keep existing card shadows and borders

## Testing Checklist

- [ ] High risk coin shows "Exercise Caution" with appropriate bullets
- [ ] Medium risk coin shows "Proceed with Caution" with mixed signals
- [ ] Low risk coin shows "Favorable Conditions" with stability indicators
- [ ] Confidence interpretation shows correct text (<40%, 40-60%, >60%)
- [ ] Risk factors show plain English interpretations
- [ ] Volatility trend shows correct direction (increasing/decreasing/stable)
- [ ] Market regime shows "What this means" interpretation
- [ ] High risk alert shows specific concerns and recommendations
- [ ] Disclaimer visible on recommendation card
- [ ] Mobile responsive (recommendation card stacks properly)

## Success Criteria

1. **Clarity:** Users immediately understand what action to take
2. **Context:** Technical metrics have plain English explanations
3. **Consistency:** Recommendation logic is deterministic and predictable
4. **Design:** Matches existing light theme and design language
5. **Performance:** No additional API calls, pure frontend enhancement

## Future Enhancements (Out of Scope)

- Historical risk tracking (requires backend changes)
- Comparison to other coins (requires batch analysis)
- User risk tolerance settings (requires user accounts)
- Email/push alerts for risk changes (requires notification system)

---

**Status:** Design approved, ready for implementation planning
**Date:** March 22, 2026
