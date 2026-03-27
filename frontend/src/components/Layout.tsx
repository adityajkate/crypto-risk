import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Activity,
  Menu,
  X,
  Zap,
  TrendingUp
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const location = useLocation();

  // Hide sidebar on Landing Page
  if (location.pathname === '/') {
    return <>{children}</>;
  }

  const navItems = [
    { path: '/dashboard', label: 'Overview', icon: <LayoutDashboard size={20} /> },
    { path: '/top-coins', label: 'Top Coins', icon: <TrendingUp size={20} /> },
    { path: '/sentiment', label: 'Sentiment', icon: <Activity size={20} /> },
  ];

  return (
    <div className="min-h-screen relative flex bg-[#F8F9FA] text-slate-900">
      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-white z-50 flex items-center justify-between px-4 border-b border-slate-200 shadow-sm">
        <Link to="/" className="flex items-center gap-3">
           <Zap className="text-[#0d9488]" size={24} strokeWidth={2.5} fill="currentColor" />
           <span className="text-xl font-bold tracking-tight text-[#0f172a]">CryptoRisk Lens</span>
        </Link>
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="p-2 text-slate-700 hover:text-slate-900"
          aria-label={isSidebarOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={isSidebarOpen}
        >
          {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Sidebar Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed top-0 bottom-0 left-0 z-40 w-64 bg-white transition-transform duration-300 ease-in-out card-shadow
        lg:translate-x-0 lg:static lg:block
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="h-full flex flex-col">
          <div className="h-20 flex items-center px-6 border-b border-slate-200">
             <Link to="/" className="flex items-center gap-3 group cursor-pointer">
                <div className="relative">
                  <Zap
                    className="text-[#0d9488] transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:rotate-[15deg] group-hover:scale-110"
                    size={24}
                    strokeWidth={2.5}
                    fill="currentColor"
                  />
                  <div className="absolute inset-0 bg-[#0d9488] blur-xl opacity-0 group-hover:opacity-40 transition-opacity duration-700" />
                </div>
                <span className="text-xl font-bold tracking-tight text-[#0f172a]">
                  CryptoRisk Lens
                </span>
             </Link>
          </div>

          <nav className="flex-1 py-6 px-3 space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsSidebarOpen(false)}
                  className={`
                    flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-all duration-200
                    ${isActive
                      ? 'bg-teal-50 text-teal-700'
                      : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                    }
                  `}
                >
                  {item.icon}
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="p-4 border-t border-slate-200">
            <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-700 border border-slate-200 cursor-pointer hover:bg-slate-100 transition-colors">
              <p className="mb-2 font-medium">Market Status</p>
              <div className="flex items-center gap-2 text-emerald-600 font-medium">
                <svg className="w-2 h-2 animate-pulse" viewBox="0 0 8 8" fill="currentColor">
                  <circle cx="4" cy="4" r="4" />
                </svg>
                Live Feed
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 w-full lg:w-auto relative z-0 pt-16 lg:pt-0 overflow-x-hidden">
        <div className="p-4 lg:p-8 max-w-[1600px] mx-auto min-h-screen">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
