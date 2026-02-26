# Project Structure Visual Guide

## 🎨 Frontend Architecture

```
frontend/
│
├── public/                          # Static files served directly
│   ├── index.html                   # HTML entry point
│   └── favicon.ico                  # Site icon
│
└── src/                             # All source code
    │
    ├── app/                         # 🚀 Application Core
    │   ├── App.tsx                  # Main app component with routing
    │   ├── index.tsx                # React entry point
    │   └── routes.tsx               # Route configuration (optional)
    │
    ├── features/                    # 🎯 Feature Modules (Business Logic)
    │   │
    │   ├── dashboard/               # Dashboard feature
    │   │   ├── components/          # Dashboard-specific components
    │   │   │   ├── StatCard.tsx
    │   │   │   ├── RiskGauge.tsx
    │   │   │   ├── RiskDistribution.tsx
    │   │   │   └── TechnicalIndicators.tsx
    │   │   ├── hooks/               # Dashboard-specific hooks
    │   │   │   ├── useDashboardData.ts
    │   │   │   └── useChartData.ts
    │   │   ├── utils/               # Dashboard-specific utilities
    │   │   │   └── chartHelpers.ts
    │   │   └── Dashboard.tsx        # Main dashboard page
    │   │
    │   ├── charts/                  # Charts feature
    │   │   ├── components/
    │   │   │   ├── PriceChart.tsx
    │   │   │   ├── CandlestickChart.tsx
    │   │   │   └── LineChart.tsx
    │   │   └── utils/
    │   │       ├── chartConfig.ts
    │   │       └── yAxisTicks.ts
    │   │
    │   ├── coin-search/             # Coin search feature
    │   │   ├── components/
    │   │   │   ├── CoinSearch.tsx
    │   │   │   └── CoinSuggestion.tsx
    │   │   └── hooks/
    │   │       └── useCoinSearch.ts
    │   │
    │   ├── sentiment/               # Sentiment analysis feature
    │   │   └── SentimentPage.tsx
    │   │
    │   ├── risk/                    # Risk insights feature
    │   │   └── RiskPage.tsx
    │   │
    │   ├── history/                 # Historical patterns feature
    │   │   └── HistoryPage.tsx
    │   │
    │   ├── about/                   # About/methodology feature
    │   │   └── AboutPage.tsx
    │   │
    │   └── landing/                 # Landing page feature
    │       ├── components/
    │       │   └── AnimatedBackground.tsx
    │       └── LandingPage.tsx
    │
    ├── shared/                      # 🔄 Shared Code (Reusable)
    │   │
    │   ├── components/              # Reusable UI components
    │   │   ├── Layout/
    │   │   │   ├── Layout.tsx       # Main layout wrapper
    │   │   │   ├── Sidebar.tsx      # Navigation sidebar
    │   │   │   └── Header.tsx       # Top header
    │   │   ├── ui/                  # Base UI components
    │   │   │   ├── Button.tsx
    │   │   │   ├── Card.tsx
    │   │   │   ├── Input.tsx
    │   │   │   └── Tooltip.tsx
    │   │   └── IndicatorTooltip.tsx
    │   │
    │   ├── hooks/                   # Reusable custom hooks
    │   │   ├── useDebounce.ts
    │   │   ├── useClickOutside.ts
    │   │   └── useLocalStorage.ts
    │   │
    │   ├── context/                 # Global state management
    │   │   └── CryptoContext.tsx    # Crypto data context
    │   │
    │   ├── services/                # API services
    │   │   ├── api.ts               # Main API service
    │   │   ├── coingecko.ts         # CoinGecko API
    │   │   └── analytics.ts         # Analytics service
    │   │
    │   ├── utils/                   # Utility functions
    │   │   ├── formatters.ts        # Number/date formatters
    │   │   ├── dataHelpers.ts       # Data manipulation
    │   │   └── validators.ts        # Input validation
    │   │
    │   ├── types/                   # TypeScript types
    │   │   ├── index.ts             # Main exports
    │   │   ├── api.types.ts         # API types
    │   │   ├── chart.types.ts       # Chart types
    │   │   └── coin.types.ts        # Coin types
    │   │
    │   └── constants/               # App constants
    │       ├── colors.ts            # Color palette
    │       ├── routes.ts            # Route paths
    │       └── config.ts            # App config
    │
    └── styles/                      # 🎨 Global styles
        ├── index.css                # Main stylesheet
        ├── design-system.css        # Design system
        └── variables.css            # CSS variables
```

## 🔧 Backend Architecture

```
api/
│
├── routes/                          # 🛣️ API Routes (HTTP endpoints)
│   ├── __init__.py
│   ├── analysis.py                  # /api/analysis/* routes
│   ├── coins.py                     # /api/coins/* routes
│   └── indicators.py                # /api/indicators/* routes
│
├── services/                        # ⚙️ Business Logic
│   ├── __init__.py
│   ├── predictor.py                 # Risk prediction service
│   └── coingecko_realtime.py        # Real-time price service
│
├── utils/                           # 🛠️ Utilities
│   ├── __init__.py
│   └── config.py                    # Configuration
│
├── __init__.py
├── main.py                          # FastAPI app entry point
└── README.md
```

## 🔄 Shared Python Modules

```
shared/
│
├── clients/                         # 🌐 External API clients
│   ├── __init__.py
│   ├── coingecko_client.py          # CoinGecko API client
│   └── cryptopanic_client.py        # CryptoPanic API client
│
├── features/                        # 🧮 Feature Engineering
│   ├── __init__.py
│   └── feature_engine.py            # Feature extraction
│
├── models/                          # 📊 Data Models
│   ├── __init__.py
│   └── models.py                    # Pydantic models
│
└── __init__.py
```

## 🎓 Training Pipeline

```
training/
│
├── data/                            # 📥 Data Processing
│   ├── __init__.py
│   ├── collect_training_data.py     # Data collection
│   └── preprocess.py                # Data preprocessing
│
├── models/                          # 🤖 Model Training
│   ├── __init__.py
│   ├── train_risk_classifier.py     # Risk classification
│   ├── train_regime_model.py        # Market regime detection
│   ├── train_regression.py          # Regression models
│   └── train_clustering.py          # Clustering models
│
├── utils/                           # 🔧 Training Utilities
│   ├── __init__.py
│   ├── label_generator.py           # Label generation
│   └── run_pca.py                   # PCA analysis
│
├── __init__.py
├── run_all.py                       # Run full pipeline
└── README.md
```

## 🧪 Testing Structure

```
tests/
│
├── unit/                            # Unit tests
│   ├── test_coingecko_client.py
│   ├── test_feature_engine.py
│   ├── test_label_generator.py
│   └── test_formatters.py
│
├── integration/                     # Integration tests
│   ├── test_api.py
│   ├── test_training_pipeline.py
│   └── test_end_to_end.py
│
└── __init__.py
```

## 📚 Documentation Structure

```
docs/
│
├── README.md                        # Main documentation
├── IMPROVED-STRUCTURE.md            # Structure explanation
├── MIGRATION-GUIDE.md               # Migration instructions
├── IMPORT-UPDATES.md                # Import path guide
├── STRUCTURE-IMPROVEMENT-SUMMARY.md # Quick summary
├── IMPROVEMENTS.md                  # UI/UX improvements
├── PREMIUM-FIDELITY.md              # Design refinements
├── FINAL-CORRECTIONS.md             # Final corrections
├── VISUAL-COMPARISON.md             # Before/after visuals
├── COIN-SEARCH-FIX.md               # Coin search fix
├── CHECKLIST.md                     # Implementation checklist
└── API.md                           # API documentation
```

## 🎯 Import Path Examples

### Feature Component Importing Shared Code
```tsx
// In: features/dashboard/Dashboard.tsx

// ✅ Import from shared
import { Layout } from '@/shared/components';
import { useCrypto } from '@/shared/context/CryptoContext';
import { formatPrice, formatPercentage } from '@/shared/utils';
import { CoinData } from '@/shared/types';

// ✅ Import from same feature
import RiskGauge from './components/RiskGauge';
import { useDashboardData } from './hooks/useDashboardData';

// ✅ Import from other features
import PriceChart from '@/features/charts/components/PriceChart';
import CoinSearch from '@/features/coin-search/components/CoinSearch';
```

### Shared Component Importing Shared Code
```tsx
// In: shared/components/Layout/Layout.tsx

// ✅ Import from other shared modules
import { useLocalStorage } from '@/shared/hooks';
import { ROUTES } from '@/shared/constants';
import { NavItem } from '@/shared/types';
```

### App-level Importing Features
```tsx
// In: app/App.tsx

// ✅ Import shared layout
import { Layout } from '@/shared/components';

// ✅ Import feature pages
import Dashboard from '@/features/dashboard/Dashboard';
import LandingPage from '@/features/landing/LandingPage';
import SentimentPage from '@/features/sentiment/SentimentPage';
```

## 📊 Dependency Flow

```
┌─────────────────────────────────────────────────┐
│                    app/                         │
│              (App configuration)                │
└────────────────────┬────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────┐
│                 features/                       │
│           (Business logic modules)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │dashboard │  │  charts  │  │coin-search│     │
│  └──────────┘  └──────────┘  └──────────┘     │
└────────────────────┬────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────┐
│                  shared/                        │
│         (Reusable code & utilities)             │
│  ┌───────────┐  ┌─────────┐  ┌──────────┐     │
│  │components │  │  hooks  │  │ services │     │
│  └───────────┘  └─────────┘  └──────────┘     │
│  ┌───────────┐  ┌─────────┐  ┌──────────┐     │
│  │   utils   │  │  types  │  │constants │     │
│  └───────────┘  └─────────┘  └──────────┘     │
└─────────────────────────────────────────────────┘

Rules:
✅ app/ can import from features/ and shared/
✅ features/ can import from shared/ and other features/
✅ shared/ can only import from other shared/ modules
❌ shared/ should NOT import from features/
❌ Avoid circular dependencies
```

## 🎨 Color Coding Legend

- 🚀 **App Core** - Application entry and configuration
- 🎯 **Features** - Business logic and feature modules
- 🔄 **Shared** - Reusable code across features
- 🎨 **Styles** - Global styling
- 🔧 **Backend** - API and services
- 🎓 **Training** - ML pipeline
- 🧪 **Testing** - Test suites
- 📚 **Docs** - Documentation

## 📏 Naming Conventions

### Files
- **Components**: PascalCase (e.g., `RiskGauge.tsx`)
- **Hooks**: camelCase with `use` prefix (e.g., `useDashboardData.ts`)
- **Utils**: camelCase (e.g., `formatters.ts`)
- **Types**: camelCase with `.types` suffix (e.g., `api.types.ts`)
- **Constants**: camelCase (e.g., `colors.ts`)

### Folders
- **Features**: kebab-case (e.g., `coin-search/`)
- **Components**: PascalCase for component folders (e.g., `Layout/`)
- **Others**: lowercase (e.g., `hooks/`, `utils/`)

## 🔍 Finding Files Quickly

### By Feature
```
Need dashboard code? → features/dashboard/
Need chart code? → features/charts/
Need search code? → features/coin-search/
```

### By Type
```
Need a reusable component? → shared/components/
Need a custom hook? → shared/hooks/
Need a utility function? → shared/utils/
Need type definitions? → shared/types/
```

### By Purpose
```
Need to add a route? → app/App.tsx
Need to call an API? → shared/services/
Need to format data? → shared/utils/formatters.ts
Need global state? → shared/context/
```

This visual guide should help you navigate the improved structure efficiently! 🚀
