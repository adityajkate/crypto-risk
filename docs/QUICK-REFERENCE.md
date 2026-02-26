# Quick Reference Card - Project Structure

## 🚀 Quick Commands

```bash
# Run migration
bash scripts/migrate-structure.sh

# Test frontend
cd frontend && npm run build && npm run dev

# Test backend
python scripts/run_api.py

# Run tests
python -m pytest tests/
```

## 📁 Where to Find Things

| What You Need | Where to Look |
|---------------|---------------|
| Dashboard components | `frontend/src/features/dashboard/components/` |
| Charts | `frontend/src/features/charts/components/` |
| Coin search | `frontend/src/features/coin-search/components/` |
| Reusable components | `frontend/src/shared/components/` |
| Custom hooks | `frontend/src/shared/hooks/` |
| API services | `frontend/src/shared/services/` |
| Utilities | `frontend/src/shared/utils/` |
| Types | `frontend/src/shared/types/` |
| Global styles | `frontend/src/styles/` |
| API routes | `api/routes/` |
| Business logic | `api/services/` |
| Documentation | `docs/` |

## 🔧 Import Path Cheat Sheet

```tsx
// Shared components
import { Layout } from '@/shared/components';

// Shared hooks
import { useDebounce } from '@/shared/hooks';

// Shared services
import { apiService } from '@/shared/services/api';

// Shared utils
import { formatPrice } from '@/shared/utils';

// Shared types
import { CoinData } from '@/shared/types';

// Feature components (from same feature)
import RiskGauge from './components/RiskGauge';

// Feature components (from other feature)
import PriceChart from '@/features/charts/components/PriceChart';
```

## 📝 File Naming

| Type | Convention | Example |
|------|------------|---------|
| Component | PascalCase | `RiskGauge.tsx` |
| Hook | camelCase + use | `useDashboardData.ts` |
| Util | camelCase | `formatters.ts` |
| Type | camelCase + .types | `api.types.ts` |
| Folder | kebab-case | `coin-search/` |

## 🎯 Common Tasks

### Add New Feature
```bash
# 1. Create feature folder
mkdir -p frontend/src/features/my-feature/components

# 2. Create main component
touch frontend/src/features/my-feature/MyFeature.tsx

# 3. Add route in App.tsx
# Import and add to routes
```

### Add Shared Component
```bash
# 1. Create component
touch frontend/src/shared/components/MyComponent.tsx

# 2. Export from index
# Add to shared/components/index.ts
```

### Add API Endpoint
```bash
# 1. Create route
touch api/routes/my_route.py

# 2. Create service
touch api/services/my_service.py

# 3. Register in main.py
```

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| Import not found | Check tsconfig.json paths |
| Build fails | Clear cache: `rm -rf node_modules/.vite` |
| TS errors | Restart TS server in VS Code |
| Module not found | Check file was moved correctly |

## 📚 Documentation Quick Links

- **Full Structure**: `docs/IMPROVED-STRUCTURE.md`
- **Migration Guide**: `docs/MIGRATION-GUIDE.md`
- **Import Updates**: `docs/IMPORT-UPDATES.md`
- **Visual Guide**: `docs/STRUCTURE-VISUAL-GUIDE.md`
- **Summary**: `docs/STRUCTURE-IMPROVEMENT-SUMMARY.md`

## ✅ Pre-Migration Checklist

- [ ] Backup project (git commit)
- [ ] Read migration guide
- [ ] Have 2-4 hours available
- [ ] Notify team members

## ✅ Post-Migration Checklist

- [ ] All files moved
- [ ] Config files updated
- [ ] Import paths fixed
- [ ] Build succeeds
- [ ] Tests pass
- [ ] App runs correctly
- [ ] No console errors

## 🎨 Structure at a Glance

```
crypto-risk/
├── docs/              # 📚 Documentation
├── frontend/src/
│   ├── app/          # 🚀 App config
│   ├── features/     # 🎯 Features
│   └── shared/       # 🔄 Shared code
├── api/              # 🔧 Backend
├── shared/           # 🔄 Python modules
├── training/         # 🎓 ML training
└── tests/            # 🧪 Tests
```

## 💡 Pro Tips

1. **Use @ alias** for cleaner imports
2. **Keep features independent** - avoid cross-feature dependencies
3. **Put reusable code in shared/** - not in features
4. **Create index files** for cleaner exports
5. **Follow naming conventions** consistently
6. **Document as you go** - update docs when adding features

## 🆘 Need Help?

1. Check `docs/MIGRATION-GUIDE.md`
2. Review `docs/IMPORT-UPDATES.md`
3. Look at `docs/STRUCTURE-VISUAL-GUIDE.md`
4. Check git diff to see changes
5. Rollback if needed: `git checkout backup-before-migration`

---

**Print this card and keep it handy during migration!** 📋
