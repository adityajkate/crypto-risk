import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  level?: 'root' | 'route' | 'component';
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to console in development
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI based on level
      const { level = 'component' } = this.props;

      if (level === 'root') {
        return (
          <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
            <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
              <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h1 className="text-2xl font-bold text-slate-900 mb-2">
                Something went wrong
              </h1>
              <p className="text-slate-600 mb-6">
                The application encountered an unexpected error. Please refresh the page to try again.
              </p>
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-2.5 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors font-medium"
              >
                Refresh Page
              </button>
            </div>
          </div>
        );
      }

      if (level === 'route') {
        return (
          <div className="flex items-center justify-center min-h-[400px] p-4">
            <div className="max-w-md w-full bg-white rounded-lg shadow-md p-6 text-center">
              <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-3" />
              <h2 className="text-xl font-semibold text-slate-900 mb-2">
                Page Error
              </h2>
              <p className="text-slate-600 mb-4">
                This page encountered an error. Try going back or refreshing.
              </p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={() => window.history.back()}
                  className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors font-medium"
                >
                  Go Back
                </button>
                <button
                  onClick={this.handleReset}
                  className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors font-medium"
                >
                  Try Again
                </button>
              </div>
            </div>
          </div>
        );
      }

      // Component level
      return (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 my-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-900 mb-1">
                Component Error
              </h3>
              <p className="text-sm text-red-700 mb-3">
                This component failed to load. You can try again or continue using other features.
              </p>
              <button
                onClick={this.handleReset}
                className="text-sm px-3 py-1.5 bg-red-600 text-white rounded hover:bg-red-700 transition-colors font-medium"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
