import { useState } from 'react';
import { Menu } from 'lucide-react';
import { Header } from '@/components/Header';
import { Sidebar } from '@/components/Sidebar';
import { OverviewPage } from '@/pages/OverviewPage';
import { PatrolPage } from '@/pages/PatrolPage';
import { AlertsPage } from '@/pages/AlertsPage';
import { HistoryPage } from '@/pages/HistoryPage';
import { ThemeProvider } from '@/context/ThemeContext';
import { DashboardProvider } from '@/context/DashboardContext';

export type PageId = 'overview' | 'patrol' | 'alerts' | 'history';

function AppContent() {
  const [currentPage, setCurrentPage] = useState<PageId>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen max-h-screen h-screen overflow-hidden bg-base text-ink flex flex-col justify-between select-none">
      {/* Global Top Header */}
      <Header onAlertClick={() => setCurrentPage('alerts')} />

      {/* Mobile Navigation Header */}
      <div className="lg:hidden flex items-center justify-between px-4 py-2 border-b border-line bg-base-surface shrink-0">
        <button
          onClick={() => setSidebarOpen(true)}
          className="flex items-center gap-2 text-xs font-semibold text-ink-muted hover:text-green cursor-pointer"
        >
          <Menu className="w-4 h-4 text-green" />
          MENU
        </button>
        <span className="text-xs font-bold text-green uppercase tracking-wider">
          {currentPage}
        </span>
      </div>

      {/* Main Layout Container */}
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar
          currentPage={currentPage}
          onNavigate={setCurrentPage}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto scrollbar-thin p-3 lg:p-4 flex flex-col justify-between">
          <div>
            {currentPage === 'overview' && (
              <OverviewPage onNavigateAlerts={() => setCurrentPage('alerts')} />
            )}
            {currentPage === 'patrol' && <PatrolPage />}
            {currentPage === 'alerts' && <AlertsPage />}
            {currentPage === 'history' && <HistoryPage />}
          </div>

          {/* Minimal Footer */}
          <footer className="flex items-center justify-between pt-4 pb-1 text-xs text-ink-muted shrink-0 border-t border-line/40 mt-4">
            <span className="font-medium">SAFEROOM · Autonomous Environmental Patrol</span>
            <span className="mono text-3xs opacity-80">CONNECTED · REALTIME TELEMETRY</span>
          </footer>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <DashboardProvider>
        <AppContent />
      </DashboardProvider>
    </ThemeProvider>
  );
}

export default App;
