import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import Header from './Header';
import Sidebar from './Sidebar';
import { AssetTelemetryProvider } from '../context/AssetTelemetryContext';

export default function Layout() {
  const location = useLocation();
  return (
    <AssetTelemetryProvider>
      <div className="relative z-10 flex h-screen w-screen overflow-hidden bg-obsidian">
        <Sidebar />
        <div className="relative z-10 flex flex-1 flex-col overflow-hidden">
          <Header />
          <main className="relative z-10 flex-1 overflow-hidden">
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ stiffness: 100, damping: 15 }}
                className="absolute inset-0 overflow-y-auto"
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
      </div>
    </AssetTelemetryProvider>
  );
}