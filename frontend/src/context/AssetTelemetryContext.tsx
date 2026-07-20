import { createContext, useContext, useState, type ReactNode } from 'react';
import { useAssetTelemetry, type LiveAsset } from '../hooks/useAssetTelemetry';

type AssetTelemetryContextValue = {
  assets: LiveAsset[];
  refresh: () => void;
  anyLoading: boolean;
};

const AssetTelemetryContext = createContext<AssetTelemetryContextValue | null>(null);

export function AssetTelemetryProvider({ children }: { children: ReactNode }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const assets = useAssetTelemetry(refreshKey);
  const anyLoading = assets.some((a) => a.loading);

  const refresh = () => setRefreshKey((k) => k + 1);

  return (
    <AssetTelemetryContext.Provider value={{ assets, refresh, anyLoading }}>
      {children}
    </AssetTelemetryContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAssetTelemetryContext() {
  const ctx = useContext(AssetTelemetryContext);
  if (!ctx) {
    throw new Error('useAssetTelemetryContext must be used within an AssetTelemetryProvider');
  }
  return ctx;
}