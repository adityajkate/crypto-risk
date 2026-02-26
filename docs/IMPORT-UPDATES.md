# Import Path Updates Guide

After running the migration script, you'll need to update import paths throughout your codebase. This guide shows the old vs new import paths.

## Frontend Import Updates

### App-level Files

**App.tsx**
```tsx
// OLD
import Layout from './components/Layout';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';

// NEW
import Layout from '@/shared/components/Layout/Layout';
import LandingPage from '@/features/landing/LandingPage';
import Dashboard from '@/features/dashboard/Dashboard';
```

### Dashboard Component

**Dashboard.tsx**
```tsx
// OLD
import RiskGauge from '../components/RiskGauge';
import CoinSearch from '../components/CoinSearch';
import PriceChart from '../components/PriceChart';
import IndicatorTooltip from '../components/IndicatorTooltip';
import { useCrypto } from '../context/CryptoContext';
import { apiService, TechnicalIndicators } from '../services/api';
import { formatLargeNumber, formatPercentage, formatPrice, formatDecimal } from '../utils/formatters';

// NEW
import RiskGauge from './components/RiskGauge';
import CoinSearch from '@/features/coin-search/components/CoinSearch';
import PriceChart from '@/features/charts/components/PriceChart';
import IndicatorTooltip from '@/shared/components/IndicatorTooltip';
import { useCrypto } from '@/shared/context/CryptoContext';
import { apiService, TechnicalIndicators } from '@/shared/services/api';
import { formatLargeNumber, formatPercentage, formatPrice, formatDecimal } from '@/shared/utils/formatters';
```

### Layout Component

**Layout.tsx**
```tsx
// OLD
import { Link, useLocation } from 'react-router-dom';

// NEW (no change, external dependency)
import { Link, useLocation } from 'react-router-dom';
```

### CoinSearch Component

**CoinSearch.tsx**
```tsx
// OLD
import { Search, X } from 'lucide-react';

// NEW (no change, external dependency)
import { Search, X } from 'lucide-react';
```

### PriceChart Component

**PriceChart.tsx**
```tsx
// OLD
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Area, AreaChart } from 'recharts';

// NEW (no change, external dependency)
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Area, AreaChart } from 'recharts';
```

### CryptoContext

**CryptoContext.tsx**
```tsx
// OLD
import { apiService, CoinAnalysis, PriceData } from '../services/api';

// NEW
import { apiService, CoinAnalysis, PriceData } from '@/shared/services/api';
```

### API Service

**api.ts**
```tsx
// OLD (if any internal imports exist)
import { PricePoint, SentimentData } from '../types';

// NEW
import { PricePoint, SentimentData } from '@/shared/types';
```

## TypeScript Path Aliases

Update `tsconfig.json` to support the `@/` alias:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@/app/*": ["src/app/*"],
      "@/features/*": ["src/features/*"],
      "@/shared/*": ["src/shared/*"],
      "@/styles/*": ["src/styles/*"]
    }
  }
}
```

## Vite Configuration

Update `vite.config.ts` to support path aliases:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/app': path.resolve(__dirname, './src/app'),
      '@/features': path.resolve(__dirname, './src/features'),
      '@/shared': path.resolve(__dirname, './src/shared'),
      '@/styles': path.resolve(__dirname, './src/styles'),
    },
  },
});
```

## Backend Import Updates

### API Main

**api/main.py**
```python
# OLD
from predictor import RiskPredictor
from coingecko_realtime import get_coin_price
from config import settings

# NEW
from api.services.predictor import RiskPredictor
from api.services.coingecko_realtime import get_coin_price
from api.utils.config import settings
```

### Predictor Service

**api/services/predictor.py**
```python
# OLD
from shared.feature_engine import FeatureEngine
from shared.models import RiskPrediction

# NEW
from shared.features.feature_engine import FeatureEngine
from shared.models.models import RiskPrediction
```

### Training Scripts

**training/models/train_risk_classifier.py**
```python
# OLD
from shared.feature_engine import FeatureEngine
from shared.coingecko_client import CoinGeckoClient
from training.preprocess import preprocess_data
from training.label_generator import generate_labels

# NEW
from shared.features.feature_engine import FeatureEngine
from shared.clients.coingecko_client import CoinGeckoClient
from training.data.preprocess import preprocess_data
from training.utils.label_generator import generate_labels
```

## Quick Find & Replace

Use these regex patterns for bulk updates:

### Frontend
```bash
# Update component imports
find frontend/src -type f -name "*.tsx" -exec sed -i "s|from '../components/|from '@/shared/components/|g" {} +
find frontend/src -type f -name "*.tsx" -exec sed -i "s|from './components/|from './components/|g" {} +

# Update context imports
find frontend/src -type f -name "*.tsx" -exec sed -i "s|from '../context/|from '@/shared/context/|g" {} +

# Update service imports
find frontend/src -type f -name "*.tsx" -exec sed -i "s|from '../services/|from '@/shared/services/|g" {} +

# Update utils imports
find frontend/src -type f -name "*.tsx" -exec sed -i "s|from '../utils/|from '@/shared/utils/|g" {} +

# Update types imports
find frontend/src -type f -name "*.tsx" -exec sed -i "s|from '../types'|from '@/shared/types'|g" {} +
```

### Backend
```bash
# Update shared imports
find api -type f -name "*.py" -exec sed -i "s|from shared.|from shared.clients.|g" {} +
find api -type f -name "*.py" -exec sed -i "s|from shared.|from shared.features.|g" {} +
find api -type f -name "*.py" -exec sed -i "s|from shared.|from shared.models.|g" {} +
```

## Manual Review Required

After running automated updates, manually review:

1. **Circular dependencies** - Check if any imports create circular references
2. **Relative vs absolute** - Ensure consistency in import style
3. **Type imports** - Verify TypeScript type imports work correctly
4. **Dynamic imports** - Check lazy-loaded components
5. **Test imports** - Update test file imports

## Testing After Migration

```bash
# Frontend
cd frontend
npm run build  # Check for build errors
npm run dev    # Test in development

# Backend
cd ..
python -m pytest tests/  # Run all tests
python scripts/run_api.py  # Test API startup
```

## Common Issues & Solutions

### Issue: Module not found
**Solution**: Check if the file was moved correctly and update the import path

### Issue: Circular dependency
**Solution**: Extract shared types/interfaces to a separate file

### Issue: TypeScript errors
**Solution**: Update `tsconfig.json` paths and restart TypeScript server

### Issue: Vite build fails
**Solution**: Clear cache with `rm -rf node_modules/.vite` and rebuild

## Rollback Plan

If migration causes issues:

```bash
# Restore from git
git checkout .
git clean -fd

# Or restore from backup
cp -r backup/* .
```

## Verification Checklist

- [ ] All frontend files compile without errors
- [ ] All backend files import correctly
- [ ] Tests pass
- [ ] Development server runs
- [ ] Production build succeeds
- [ ] No console errors in browser
- [ ] API endpoints respond correctly
- [ ] All features work as expected

## Next Steps

1. Run the migration script
2. Update imports using this guide
3. Test thoroughly
4. Commit changes with descriptive message
5. Update team documentation
