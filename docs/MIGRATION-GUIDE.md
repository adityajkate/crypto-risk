# Project Structure Improvement - Complete Guide

## Overview

This guide provides a complete walkthrough for migrating your crypto-risk project to an improved, scalable folder structure following industry best practices.

## Why Improve the Structure?

### Current Problems
- ❌ Documentation scattered in root directory
- ❌ Components not organized by feature
- ❌ No clear separation between UI and business logic
- ❌ Difficult to find related files
- ❌ Hard to scale as project grows
- ❌ Import paths are confusing

### Benefits of New Structure
- ✅ Feature-based organization (easy to find related code)
- ✅ Clear separation of concerns
- ✅ Better code reusability
- ✅ Easier onboarding for new developers
- ✅ Scalable architecture
- ✅ Professional industry-standard structure
- ✅ Cleaner import paths with aliases

## Migration Process

### Step 1: Backup Your Project

```bash
# Create a backup
cp -r crypto-risk crypto-risk-backup

# Or use git
git add .
git commit -m "Backup before structure migration"
git branch backup-before-migration
```

### Step 2: Review the New Structure

Read `docs/IMPROVED-STRUCTURE.md` to understand the new organization.

**Key Changes:**
- `frontend/src/features/` - Feature-based modules
- `frontend/src/shared/` - Shared components, hooks, utils
- `docs/` - All documentation in one place
- `api/routes/`, `api/services/` - Backend organization
- `shared/clients/`, `shared/features/` - Python modules

### Step 3: Run Migration Script

```bash
# Make script executable
chmod +x scripts/migrate-structure.sh

# Run migration
bash scripts/migrate-structure.sh
```

**What the script does:**
1. Creates new directory structure
2. Moves files to appropriate locations
3. Organizes documentation
4. Cleans up empty directories

### Step 4: Update Configuration Files

#### Update `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@/app/*": ["src/app/*"],
      "@/features/*": ["src/features/*"],
      "@/shared/*": ["src/shared/*"],
      "@/styles/*": ["src/styles/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

#### Update `frontend/vite.config.ts`

```typescript
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
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

#### Update `frontend/src/app/index.tsx`

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import '@/styles/index.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

#### Update `frontend/public/index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Crypto-Risk Lens</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/app/index.tsx"></script>
  </body>
</html>
```

### Step 5: Update Import Paths

Follow the detailed guide in `docs/IMPORT-UPDATES.md` to update all import statements.

**Quick automated updates:**

```bash
cd frontend/src

# Update to use @ alias for shared imports
find . -type f -name "*.tsx" -o -name "*.ts" | while read file; do
  sed -i "s|from '../shared/|from '@/shared/|g" "$file"
  sed -i "s|from '../../shared/|from '@/shared/|g" "$file"
  sed -i "s|from '../../../shared/|from '@/shared/|g" "$file"
done
```

### Step 6: Create Index Files for Cleaner Imports

#### `frontend/src/shared/components/index.ts`

```typescript
export { default as Layout } from './Layout/Layout';
export { default as IndicatorTooltip } from './IndicatorTooltip';
```

#### `frontend/src/shared/utils/index.ts`

```typescript
export * from './formatters';
export * from './dataHelpers';
```

#### `frontend/src/shared/types/index.ts`

```typescript
export * from './api.types';
export * from './chart.types';
export * from './coin.types';
```

### Step 7: Test Everything

```bash
# Frontend
cd frontend
npm install  # Reinstall dependencies
npm run build  # Check for build errors
npm run dev  # Test in development

# Backend
cd ..
pip install -r requirements-api.txt
python scripts/run_api.py

# Run tests
python -m pytest tests/
```

### Step 8: Update Documentation

Update your main `README.md` to reflect the new structure:

```markdown
## Project Structure

```
crypto-risk/
├── docs/              # Documentation
├── frontend/src/      # Frontend source code
│   ├── app/          # App configuration
│   ├── features/     # Feature modules
│   └── shared/       # Shared code
├── api/              # Backend API
├── shared/           # Shared Python modules
├── training/         # ML training
└── tests/            # Tests
```

See `docs/IMPROVED-STRUCTURE.md` for detailed structure.
```

## Common Migration Issues

### Issue 1: Import Errors After Migration

**Symptom:** `Cannot find module '@/shared/...'`

**Solution:**
1. Check `tsconfig.json` has correct paths
2. Restart TypeScript server in VS Code: `Ctrl+Shift+P` → "TypeScript: Restart TS Server"
3. Clear Vite cache: `rm -rf node_modules/.vite`

### Issue 2: Build Fails

**Symptom:** `vite build` fails with module errors

**Solution:**
1. Check `vite.config.ts` has correct aliases
2. Ensure all files were moved correctly
3. Verify import paths are updated

### Issue 3: Tests Fail

**Symptom:** Tests can't find modules

**Solution:**
1. Update test imports to use new paths
2. Check if test files were moved to `tests/unit/`
3. Update pytest configuration if needed

### Issue 4: API Can't Import Modules

**Symptom:** Python import errors

**Solution:**
1. Check Python path includes project root
2. Update imports to use new module structure
3. Verify `__init__.py` files exist in all directories

## Rollback Instructions

If you need to rollback:

```bash
# Using git
git checkout backup-before-migration
git branch -D main
git checkout -b main

# Using backup
rm -rf crypto-risk
mv crypto-risk-backup crypto-risk
```

## Post-Migration Checklist

- [ ] All files moved to correct locations
- [ ] `tsconfig.json` updated with path aliases
- [ ] `vite.config.ts` updated with aliases
- [ ] All import paths updated
- [ ] Index files created for cleaner imports
- [ ] Frontend builds successfully
- [ ] Frontend runs in development
- [ ] Backend API starts correctly
- [ ] All tests pass
- [ ] No console errors
- [ ] All features work correctly
- [ ] Documentation updated
- [ ] Team notified of changes

## Benefits You'll See

### Before
```tsx
// Confusing relative paths
import RiskGauge from '../../../components/RiskGauge';
import { formatPrice } from '../../../utils/formatters';
import { useCrypto } from '../../../context/CryptoContext';
```

### After
```tsx
// Clean, absolute paths
import RiskGauge from '@/features/dashboard/components/RiskGauge';
import { formatPrice } from '@/shared/utils';
import { useCrypto } from '@/shared/context/CryptoContext';
```

### Before
```
components/
  RiskGauge.tsx
  PriceChart.tsx
  CoinSearch.tsx
  Layout.tsx
  IndicatorTooltip.tsx
```

### After
```
features/
  dashboard/
    components/
      RiskGauge.tsx
  charts/
    components/
      PriceChart.tsx
  coin-search/
    components/
      CoinSearch.tsx
shared/
  components/
    Layout/
      Layout.tsx
    IndicatorTooltip.tsx
```

## Next Steps

1. ✅ Complete the migration
2. ✅ Test thoroughly
3. ✅ Commit changes
4. ✅ Update team documentation
5. ✅ Share migration guide with team
6. ✅ Monitor for any issues
7. ✅ Celebrate improved codebase! 🎉

## Support

If you encounter issues:
1. Check `docs/IMPORT-UPDATES.md` for import path help
2. Review `docs/IMPROVED-STRUCTURE.md` for structure details
3. Check git history for what changed
4. Rollback if needed and try again

## Conclusion

This improved structure will make your project:
- **Easier to navigate** - Find files by feature
- **More maintainable** - Clear organization
- **More scalable** - Add features without clutter
- **More professional** - Industry-standard structure
- **Team-friendly** - Easier for others to understand

Good luck with your migration! 🚀
