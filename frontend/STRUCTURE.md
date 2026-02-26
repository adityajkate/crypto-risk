# Frontend Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── AnimatedBackground.tsx
│   │   ├── CoinSearch.tsx
│   │   ├── ErrorBoundary.tsx
│   │   ├── IndicatorTooltip.tsx
│   │   ├── Layout.tsx
│   │   ├── PriceChart.tsx
│   │   └── RiskGauge.tsx
│   ├── pages/              # Route pages
│   │   ├── AboutPage.tsx
│   │   ├── Dashboard.tsx
│   │   ├── HistoryPage.tsx
│   │   ├── LandingPage.tsx
│   │   ├── RiskPage.tsx
│   │   └── SentimentPage.tsx
│   ├── context/            # React context providers
│   │   └── CryptoContext.tsx
│   ├── services/           # API clients and services
│   │   ├── api.ts          # Type definitions
│   │   └── apiClient.ts    # Enhanced API client
│   ├── utils/              # Helper functions
│   │   ├── dataHelpers.ts
│   │   └── formatters.ts
│   ├── types/              # TypeScript type definitions
│   │   └── types.ts
│   ├── styles/             # CSS files
│   │   └── design-system.css
│   ├── assets/             # Static assets (images, fonts, etc.)
│   ├── App.tsx             # Root component
│   └── index.tsx           # Entry point
├── public/                 # Public static files
├── .env.example            # Environment variables template
├── .env.development        # Development environment
├── .env.production         # Production environment
├── index.html              # HTML template
├── package.json            # Dependencies
├── tsconfig.json           # TypeScript config
├── vite.config.ts          # Vite config
└── README.md               # Documentation
```

## Key Features

- **Organized Structure**: Clear separation of concerns with dedicated folders
- **Type Safety**: Full TypeScript support with proper type definitions
- **API Client**: Enhanced client with retry logic, timeout, and error handling
- **Context API**: Global state management with CryptoContext
- **Error Boundaries**: Three-level error handling (root, route, component)
- **Accessibility**: WCAG 2.1 AA compliant with proper ARIA labels
- **Performance**: Optimized polling (60s), request deduplication, memoization

## Import Aliases

Use `@/` to import from src:
```typescript
import { apiClient } from '@/services/apiClient';
import { useCrypto } from '@/context/CryptoContext';
```
