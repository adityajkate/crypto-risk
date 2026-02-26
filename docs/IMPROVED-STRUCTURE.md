# Improved Project Structure

## Current Issues
1. Documentation files scattered in root
2. Frontend components not organized by feature
3. No clear separation between UI components and business logic
4. Utils and services mixed together
5. No hooks directory for custom React hooks
6. Types scattered across files

## Proposed Structure

```
crypto-risk/
├── docs/                           # 📚 All documentation
│   ├── README.md                   # Main project documentation
│   ├── IMPROVEMENTS.md             # UI/UX improvements log
│   ├── PREMIUM-FIDELITY.md         # Premium design refinements
│   ├── FINAL-CORRECTIONS.md        # Final corrections log
│   ├── VISUAL-COMPARISON.md        # Before/after comparisons
│   ├── COIN-SEARCH-FIX.md          # Coin search fix documentation
│   ├── CHECKLIST.md                # Implementation checklist
│   └── API.md                      # API documentation
│
├── frontend/                       # 🎨 Frontend application
│   ├── public/                     # Static assets
│   │   ├── index.html
│   │   └── favicon.ico
│   │
│   ├── src/                        # Source code
│   │   ├── app/                    # App-level configuration
│   │   │   ├── App.tsx
│   │   │   ├── index.tsx
│   │   │   └── routes.tsx
│   │   │
│   │   ├── features/               # Feature-based modules
│   │   │   ├── dashboard/
│   │   │   │   ├── components/
│   │   │   │   │   ├── StatCard.tsx
│   │   │   │   │   ├── RiskGauge.tsx
│   │   │   │   │   ├── RiskDistribution.tsx
│   │   │   │   │   └── TechnicalIndicators.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   ├── useDashboardData.ts
│   │   │   │   │   └── useChartData.ts
│   │   │   │   ├── utils/
│   │   │   │   │   └── chartHelpers.ts
│   │   │   │   └── Dashboard.tsx
│   │   │   │
│   │   │   ├── coin-search/
│   │   │   │   ├── components/
│   │   │   │   │   ├── CoinSearch.tsx
│   │   │   │   │   └── CoinSuggestion.tsx
│   │   │   │   └── hooks/
│   │   │   │       └── useCoinSearch.ts
│   │   │   │
│   │   │   ├── charts/
│   │   │   │   ├── components/
│   │   │   │   │   ├── PriceChart.tsx
│   │   │   │   │   ├── CandlestickChart.tsx
│   │   │   │   │   └── LineChart.tsx
│   │   │   │   └── utils/
│   │   │   │       ├── chartConfig.ts
│   │   │   │       └── yAxisTicks.ts
│   │   │   │
│   │   │   ├── sentiment/
│   │   │   │   └── SentimentPage.tsx
│   │   │   │
│   │   │   ├── risk/
│   │   │   │   └── RiskPage.tsx
│   │   │   │
│   │   │   ├── history/
│   │   │   │   └── HistoryPage.tsx
│   │   │   │
│   │   │   ├── about/
│   │   │   │   └── AboutPage.tsx
│   │   │   │
│   │   │   └── landing/
│   │   │       ├── components/
│   │   │       │   └── AnimatedBackground.tsx
│   │   │       └── LandingPage.tsx
│   │   │
│   │   ├── shared/                 # Shared across features
│   │   │   ├── components/         # Reusable UI components
│   │   │   │   ├── Layout/
│   │   │   │   │   ├── Layout.tsx
│   │   │   │   │   ├── Sidebar.tsx
│   │   │   │   │   └── Header.tsx
│   │   │   │   ├── ui/             # Base UI components
│   │   │   │   │   ├── Button.tsx
│   │   │   │   │   ├── Card.tsx
│   │   │   │   │   ├── Input.tsx
│   │   │   │   │   └── Tooltip.tsx
│   │   │   │   └── IndicatorTooltip.tsx
│   │   │   │
│   │   │   ├── hooks/              # Shared custom hooks
│   │   │   │   ├── useDebounce.ts
│   │   │   │   ├── useClickOutside.ts
│   │   │   │   └── useLocalStorage.ts
│   │   │   │
│   │   │   ├── context/            # Global state management
│   │   │   │   └── CryptoContext.tsx
│   │   │   │
│   │   │   ├── services/           # API services
│   │   │   │   ├── api.ts
│   │   │   │   ├── coingecko.ts
│   │   │   │   └── analytics.ts
│   │   │   │
│   │   │   ├── utils/              # Utility functions
│   │   │   │   ├── formatters.ts
│   │   │   │   ├── dataHelpers.ts
│   │   │   │   └── validators.ts
│   │   │   │
│   │   │   ├── types/              # TypeScript types
│   │   │   │   ├── index.ts
│   │   │   │   ├── api.types.ts
│   │   │   │   ├── chart.types.ts
│   │   │   │   └── coin.types.ts
│   │   │   │
│   │   │   └── constants/          # App constants
│   │   │       ├── colors.ts
│   │   │       ├── routes.ts
│   │   │       └── config.ts
│   │   │
│   │   └── styles/                 # Global styles
│   │       ├── index.css
│   │       ├── design-system.css
│   │       └── variables.css
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── README.md
│
├── api/                            # 🔧 Backend API
│   ├── routes/                     # API routes
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── coins.py
│   │   └── indicators.py
│   │
│   ├── services/                   # Business logic
│   │   ├── __init__.py
│   │   ├── predictor.py
│   │   └── coingecko_realtime.py
│   │
│   ├── utils/                      # Utility functions
│   │   ├── __init__.py
│   │   └── config.py
│   │
│   ├── __init__.py
│   ├── main.py
│   └── README.md
│
├── shared/                         # 🔄 Shared Python modules
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── coingecko_client.py
│   │   └── cryptopanic_client.py
│   │
│   ├── features/
│   │   ├── __init__.py
│   │   └── feature_engine.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   │
│   └── __init__.py
│
├── training/                       # 🎓 ML training scripts
│   ├── data/
│   │   ├── __init__.py
│   │   ├── collect_training_data.py
│   │   └── preprocess.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── train_risk_classifier.py
│   │   ├── train_regime_model.py
│   │   ├── train_regression.py
│   │   └── train_clustering.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── label_generator.py
│   │   └── run_pca.py
│   │
│   ├── __init__.py
│   ├── run_all.py
│   └── README.md
│
├── tests/                          # 🧪 Test files
│   ├── unit/
│   │   ├── test_coingecko_client.py
│   │   ├── test_feature_engine.py
│   │   └── test_label_generator.py
│   │
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_training_pipeline.py
│   │
│   └── __init__.py
│
├── artifacts/                      # 📦 Generated artifacts
│   ├── models/                     # Trained models
│   ├── data/                       # Processed data
│   └── metrics/
│       └── training_metrics.json
│
├── scripts/                        # 🔨 Utility scripts
│   ├── setup.sh
│   ├── run_api.py
│   └── deploy.sh
│
├── .github/                        # GitHub configuration
│   └── workflows/
│       └── ci.yml
│
├── .claude/                        # Claude Code settings
│   └── settings.local.json
│
├── requirements-api.txt
├── requirements-train.txt
├── .gitignore
├── .env.example
└── README.md
```

## Key Improvements

### 1. Feature-Based Organization
- Each feature has its own folder with components, hooks, and utils
- Easy to find and modify feature-specific code
- Better code splitting and lazy loading

### 2. Clear Separation of Concerns
- `shared/` for reusable code across features
- `features/` for feature-specific code
- `app/` for app-level configuration

### 3. Organized Documentation
- All docs in `docs/` folder
- Easy to find and maintain
- Separate from source code

### 4. Better Type Management
- All types in `shared/types/`
- Organized by domain (api, chart, coin)
- Single source of truth

### 5. Improved Backend Structure
- Routes separated from business logic
- Services contain core functionality
- Utils for configuration and helpers

### 6. Scalable Testing
- Unit tests separated from integration tests
- Easy to add new test files
- Clear test organization

## Migration Benefits

✅ **Easier Navigation** - Find files quickly by feature
✅ **Better Scalability** - Add new features without cluttering
✅ **Improved Maintainability** - Clear ownership and responsibility
✅ **Enhanced Collaboration** - Team members can work on separate features
✅ **Better Code Reuse** - Shared components and utilities clearly identified
✅ **Cleaner Imports** - Shorter, more logical import paths
✅ **Professional Structure** - Follows industry best practices
