import io

content = '''import { useMemo } from 'react';
import { motion } from 'framer-motion';
import PageHeader from '../components/PageHeader';
import { formatINR } from '../utils/currency';
import { type LiveAsset } from '../hooks/useAssetTelemetry';
import { useAssetTelemetryContext } from '../context/AssetTelemetryContext';
import {
  Flame,
  Gauge,
  Thermometer,
  Wind,
  Factory,
  ShieldAlert,
  RefreshCw,
} from 'lucide-react';

const ICONS: Record<string, any> = {
  'unit-1': Flame,
  'unit-2': Factory,
  'unit-3': Gauge,
  'unit-4': Thermometer,
  'unit-5': Wind,
};

function riskState(score: number): 'safe' | 'warn' | 'critical' {
  if (score >= 70) return 'critical';
  if (score >= 40) return 'warn';
  return 'safe';
}

const stateColor = {
  safe: 'mint',
  warn: 'amber',
  critical: 'crimson',
  error: 'slate',
} as const;

export default function CoreVitals() {
  const { assets, refresh, anyLoading } = useAssetTelemetryContext();

  const totalExposure = useMemo(
    () => assets.reduce((s, a) => s + (a.estimated_cost_usd ?? 0), 0),
    [assets],
  );

  const anyError = assets.some((a) => a.error);

  return (
    <div className="flex h-full flex-col p-6">
      <PageHeader
        code="VIT\u00b701 / CORE TELEMETRY"
        title="Core Vitals Dashboard"
        subtitle="Correlation Engine + Cost-of-Risk Translator \u2014 live across five critical assets."
        right={
          <div className="flex items-center gap-3">
            <button
              onClick={refresh}
              disabled={anyLoading}
              className="hud-mono flex items-center gap-2 rounded border border-edge px-3 py-2 text-[10px] tracking-wider text-mint transition hover:bg-white/5 disabled:opacity-40"
            >
              <RefreshCw size={12} className={anyLoading ? 'animate-spin' : ''} />
              {anyLoading ? 'SYNCING\u2026' : 'REFRESH'}
            </button>
            <div className="glass rounded-md px-4 py-2">
              <div className="hud-label">TOTAL EXPOSURE</div>
              <div className="hud-mono text-[18px] font-semibold text-amber-cyber glow-amber">
                {formatINR(totalExposure)}/hr
              </div>
            </div>
          </div>
        }
      />

      {anyError && (
        <div className="mb-4 rounded border border-crimson-vitals/40 bg-crimson-vitals/10 px-4 py-2 text-[12px] text-crimson-vitals">
          Some assets failed to load from the backend. Check the API server and Gemini quota, then hit Refresh.
        </div>
      )}

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-3">
        <div className="grid grid-cols-1 gap-4 overflow-y-auto pr-1 sm:grid-cols-2 xl:grid-cols-3 lg:col-span-2">
          {assets.map((a, idx) => (
            <AssetTile key={a.id} asset={a} index={idx} />
          ))}
        </div>

        <div className="glass flex flex-col overflow-hidden rounded-lg">
          <div className="flex items-center justify-between border-b border-edge px-4 py-3">
            <div className="hud-label">LIVE REASONING \u00b7 GEMINI</div>
            <span className="hud-mono text-[10px] text-mint glow-mint">\u25cf LIVE</span>
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-3">
            {assets.map((a) => (
              <div key={a.id} className="mb-3 border-b border-edge pb-3 last:border-none">
                <div className="hud-mono text-[10px] tracking-wider text-slate-500">{a.id.toUpperCase()}</div>
                <div className="text-[11px] font-medium text-slate-200">
                  {a.error ? `Error: ${a.error}` : a.primary_concern || (a.loading ? 'Loading\u2026' : '\u2014')}
                </div>
                {a.reasoning && !a.error && (
                  <div className="mt-1 text-[10px] font-light text-slate-400">{a.reasoning}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function AssetTile({ asset, index }: { asset: LiveAsset; index: number }) {
  const Icon = ICONS[asset.id] ?? Gauge;
  const state = asset.error ? 'error' : riskState(asset.risk_score);
  const color = stateColor[state];
  const toneClass =
    color === 'mint'
      ? 'text-mint glow-mint'
      : color === 'amber'
        ? 'text-amber-cyber glow-amber'
        : color === 'slate'
          ? 'text-slate-500'
          : 'text-crimson-vitals glow-crimson';
  const ringClass =
    color === 'mint'
      ? 'rgba(0,255,170,0.4)'
      : color === 'amber'
        ? 'rgba(255,170,0,0.4)'
        : color === 'slate'
          ? 'rgba(148,163,184,0.35)'
          : 'rgba(255,30,86,0.5)';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ stiffness: 100, damping: 15, delay: index * 0.06 }}
      whileHover={{ y: -2 }}
      className="glass glass-hover relative flex flex-col gap-3 rounded-lg p-4"
      style={{ boxShadow: `inset 0 0 0 1px ${ringClass.replace('0.4', '0.08')}` }}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Icon size={16} className={toneClass} />
          <div>
            <div className="font-display text-[13px] font-medium text-white">{asset.name}</div>
            <div className="hud-mono text-[9px] tracking-wider text-slate-500">
              {asset.id.toUpperCase()} \u00b7 {asset.zone}
            </div>
          </div>
        </div>
        <span
          className={`hud-mono text-[9px] tracking-wider ${
            state === 'safe'
              ? 'text-mint'
              : state === 'warn'
                ? 'text-amber-cyber'
                : state === 'error'
                  ? 'text-slate-500'
                  : 'text-crimson-vitals'
          }`}
        >
          {asset.loading
            ? 'SYNCING'
            : state === 'error'
              ? 'NO DATA'
              : state === 'safe'
                ? 'NOMINAL'
                : state === 'warn'
                  ? 'ADVISORY'
                  : 'CRITICAL'}
        </span>
      </div>

      <div className="relative flex items-end justify-between">
        <div className="flex flex-col">
          <span className="hud-label">RISK FACTOR</span>
          <motion.span
            key={asset.risk_score}
            initial={{ opacity: 0.6, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ stiffness: 100, damping: 15 }}
            className={`hud-mono text-[44px] font-semibold leading-none ${toneClass}`}
            style={{ textShadow: state === 'critical' ? '0 0 18px rgba(255,30,86,0.5)' : undefined }}
          >
            {asset.loading ? '--' : String(asset.risk_score).padStart(2, '0')}
          </motion.span>
        </div>
        <RiskRing value={asset.risk_score} color={ringClass} />
      </div>

      {asset.error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 1.2, repeat: Infinity }}
          className="flex items-center gap-2 rounded border border-slate-500/40 bg-slate-500/10 px-2 py-1.5"
        >
          <ShieldAlert size={12} className="text-slate-400" />
          <span className="hud-mono text-[10px] tracking-wider text-slate-400">
            BACKEND ERROR
          </span>
        </motion.div>
      )}

      <div className="mt-1 grid grid-cols-2 gap-3 border-t border-edge pt-3">
        <Metric
          label="RISK\u00b7LEVEL"
          value={asset.risk_level.toUpperCase()}
          tone={state === 'critical' ? 'crimson' : state === 'warn' ? 'amber' : undefined}
        />
        <Metric
          label="\u20b9/hr EXPOSURE"
          value={asset.estimated_cost_usd != null ? formatINR(asset.estimated_cost_usd) : '\u2014'}
          tone={asset.estimated_cost_usd && asset.estimated_cost_usd > 100000 ? 'crimson' : undefined}
        />
      </div>
    </motion.div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: 'amber' | 'crimson' }) {
  const c = tone === 'amber' ? 'text-amber-cyber glow-amber' : tone === 'crimson' ? 'text-crimson-vitals glow-crimson' : 'text-slate-200';
  return (
    <div className="min-w-0">
      <div className="hud-label whitespace-nowrap">{label}</div>
      <div className={`hud-mono text-[12px] font-medium whitespace-nowrap ${c}`}>{value}</div>
    </div>
  );
}

function RiskRing({ value, color }: { value: number; color: string }) {
  const r = 22;
  const c = 2 * Math.PI * r;
  const off = c - (value / 100) * c;
  return (
    <svg width="56" height="56" viewBox="0 0 56 56">
      <circle cx="28" cy="28" r={r} stroke="rgba(255,255,255,0.06)" strokeWidth="2" fill="none" />
      <motion.circle
        cx="28"
        cy="28"
        r={r}
        stroke={color}
        strokeWidth="2"
        fill="none"
        strokeDasharray={c}
        strokeDashoffset={off}
        strokeLinecap="round"
        transform="rotate(-90 28 28)"
        style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        initial={{ strokeDashoffset: c }}
        animate={{ strokeDashoffset: off }}
        transition={{ stiffness: 100, damping: 15 }}
      />
    </svg>
  );
}
'''

with io.open('CoreVitals.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("File written successfully with correct UTF-8 encoding.")