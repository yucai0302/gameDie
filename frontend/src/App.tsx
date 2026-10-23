import { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useStore } from "@/store/useStore";
import { ToastProvider } from "@/components/common/Toast";
import TopNav from "@/components/Layout/TopNav";
import Dashboard from "@/pages/Dashboard";
import Timeline from "@/pages/Timeline";
import Review from "@/pages/Review";
import GearConfig from "@/pages/GearConfig";
import Settings from "@/pages/Settings";
import Media from "@/pages/Media";

export default function App() {
  useWebSocket();
  const loadConfig = useStore((s) => s.loadConfig);
  const loadGamesStatus = useStore((s) => s.loadGamesStatus);

  useEffect(() => {
    loadConfig();
    loadGamesStatus();
    const id = setInterval(loadGamesStatus, 5000);
    return () => clearInterval(id);
  }, [loadConfig, loadGamesStatus]);

  return (
    <ToastProvider>
      <Router>
        <div className="flex h-screen flex-col">
          <TopNav />
          <main className="flex-1 overflow-hidden">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/timeline" element={<Timeline />} />
              <Route path="/review/:matchId" element={<Review />} />
              <Route path="/gear" element={<GearConfig />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/media" element={<Media />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ToastProvider>
  );
}
