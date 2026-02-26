# Crypto Risk Lens - Frontend

Real-time cryptocurrency risk analysis dashboard with ML-powered predictions.

## Quick Start

### Prerequisites
- Node.js 18+
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Using Startup Scripts

From the project root:

**Windows:**
```bash
scripts\start.bat
```

**Linux/Mac:**
```bash
./scripts/start.sh
```

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```env
VITE_API_URL=http://localhost:8000
VITE_POLLING_INTERVAL=60000
VITE_REQUEST_TIMEOUT=30000
VITE_MAX_RETRIES=3
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## Features

- **Real-time Price Updates** - 60-second polling with Page Visibility API
- **Risk Analysis** - ML-powered risk assessment (low/medium/high)
- **Technical Indicators** - 30+ TA-Lib indicators
- **Sentiment Analysis** - News and social media sentiment
- **Accessibility** - WCAG 2.1 AA compliant
- **Error Handling** - Graceful error boundaries with retry logic

## Architecture

### Performance Optimizations
- Request deduplication
- Automatic retry with exponential backoff
- Request cancellation on component unmount
- Polling pauses when tab is hidden
- Seeded random for consistent memoization

### Accessibility
- Full keyboard navigation
- Screen reader support
- ARIA labels on all interactive elements
- Focus management

### Error Handling
- Three-level error boundaries (root, route, component)
- User-friendly error messages
- Automatic retry mechanisms

## Tech Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **React Router** - Routing
- **Recharts** - Data visualization
- **Lucide React** - Icons

## Project Structure

```
frontend/
├── components/       # Reusable UI components
├── pages/           # Route pages
├── context/         # React context providers
├── services/        # API client and services
├── utils/           # Helper functions
├── types.ts         # TypeScript types
└── App.tsx          # Root component
```

## API Integration

The frontend communicates with the FastAPI backend:

- `/api/v1/coin/{id}/analysis` - Full risk analysis
- `/api/v1/coin/{id}/price` - Current price data
- `/api/v1/coin/{id}/indicators` - Technical indicators
- `/api/v1/sentiment/{currency}` - Sentiment analysis
- `/api/v1/trending` - Trending coins

## Development

### Code Quality
- TypeScript strict mode enabled
- Proper error handling throughout
- Consistent code style
- Accessibility best practices

### Performance
- 95% reduction in API calls (3s → 60s polling)
- No memory leaks with AbortController
- Proper memoization with seeded random
- Optimized re-renders

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
