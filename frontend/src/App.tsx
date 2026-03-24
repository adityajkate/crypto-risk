import React from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import SentimentPage from './pages/SentimentPage';
import TopCoinsPage from './pages/TopCoinsPage';
import { CryptoProvider } from './context/CryptoContext';
import ErrorBoundary from './components/ErrorBoundary';

const App: React.FC = () => {
  return (
    <ErrorBoundary level="root">
      <CryptoProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/dashboard" element={
                <ErrorBoundary level="route">
                  <Dashboard />
                </ErrorBoundary>
              } />
              <Route path="/sentiment" element={
                <ErrorBoundary level="route">
                  <SentimentPage />
                </ErrorBoundary>
              } />
              <Route path="/top-coins" element={
                <ErrorBoundary level="route">
                  <TopCoinsPage />
                </ErrorBoundary>
              } />
            </Routes>
          </Layout>
        </Router>
      </CryptoProvider>
    </ErrorBoundary>
  );
};

export default App;