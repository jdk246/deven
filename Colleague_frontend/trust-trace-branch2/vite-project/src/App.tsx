import { Routes, Route, useParams } from 'react-router-dom';
import { mockKOLs, mockCalls, mockAssets, mockAuditResult, willyWooHistory } from './data/mockData';
import { Sidebar } from './components/Sidebar';
import { ChatBot } from './components/ChatBot';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { KOLProfilePage } from './pages/KOLProfilePage';
import { AssetInsightsPage } from './pages/AssetInsightsPage';
import { TokenAuditPage } from './pages/TokenAuditPage';
import { AllKOLsPage } from './pages/AllKOLsPage';
import { AllMarketsPage } from './pages/AllMarketsPage';
import { LiveFeedPage } from './pages/LiveFeedPage';

function KOLProfileRoute() {
  const { kolId } = useParams<{ kolId: string }>();
  const kol = kolId ? mockKOLs[kolId] : undefined;

  if (!kol) {
    return (
      <div className="min-h-screen text-white relative z-10 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">KOL Not Found</h1>
          <p className="text-white/60">The KOL you're looking for doesn't exist.</p>
        </div>
      </div>
    );
  }

  const callHistory = kolId === 'willy-woo' ? willyWooHistory : mockCalls.filter(c => c.kolId === kolId);

  return <KOLProfilePage kol={kol} callHistory={callHistory} />;
}

function AssetInsightsRoute() {
  const { symbol } = useParams<{ symbol: string }>();
  const asset = symbol ? mockAssets[symbol] : undefined;

  if (!asset) {
    return (
      <div className="min-h-screen text-white relative z-10 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Asset Not Found</h1>
          <p className="text-white/60">The asset you're looking for doesn't exist.</p>
        </div>
      </div>
    );
  }

  return <AssetInsightsPage asset={asset} />;
}

function TokenAuditRoute() {
  const handleTokenScan = (contract: string) => {
    if (contract.toLowerCase().includes('1234') || contract.toLowerCase().includes('moonx')) {
      return mockAuditResult;
    }
    return null;
  };

  return <TokenAuditPage onScan={handleTokenScan} />;
}

function AppContent() {
  return (
    <Routes>
      {/* Landing page - no sidebar */}
      <Route path="/" element={<LandingPage kols={mockKOLs} />} />

      {/* App routes - with sidebar */}
      <Route path="/*" element={
        <div className="size-full flex">
          <Sidebar />
          <ChatBot />
          <div className="flex-1 lg:ml-64 relative z-10">
            <Routes>
              <Route path="/dashboard" element={<DashboardPage calls={mockCalls} kols={mockKOLs} assets={mockAssets} />} />
          <Route path="/live" element={<LiveFeedPage calls={mockCalls} kols={mockKOLs} />} />
          <Route path="/markets" element={<AllMarketsPage assets={mockAssets} />} />
          <Route path="/kols" element={<AllKOLsPage kols={mockKOLs} />} />
          <Route path="/audit" element={<TokenAuditRoute />} />
          <Route path="/kol/:kolId" element={<KOLProfileRoute />} />
              <Route path="/market/:symbol" element={<AssetInsightsRoute />} />
              <Route path="/settings" element={
                <div className="min-h-screen text-white relative z-10 flex items-center justify-center">
                  <div className="text-center">
                    <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
                      Settings
                    </h1>
                    <p className="text-white/60">Coming soon...</p>
                  </div>
                </div>
              } />
              <Route path="*" element={
                <div className="min-h-screen text-white relative z-10 flex items-center justify-center">
                  <div className="text-center">
                    <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
                      404
                    </h1>
                    <p className="text-white/60">Page not found</p>
                  </div>
                </div>
              } />
            </Routes>
          </div>
        </div>
      } />
    </Routes>
  );
}

export default function App() {
  return (
    <AppContent />
  );
}
