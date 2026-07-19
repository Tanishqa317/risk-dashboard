import { useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PageHeader from '../components/PageHeader';
import { BellOff, Bell, Layers, RefreshCw } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';

const UNITS = [
  { id: 'unit-1', name: 'Hydrocracker Complex' },
  { id: 'unit-2', name: 'Distillation Tower 3' },
  { id: 'unit-3', name: 'Catalytic Reformer' },
  { id: 'unit-4', name: 'Boiler House B' },
  { id: 'unit-5', name: 'Storage Terminal 5' },
];

type AlarmEvent = {
  unit_id: string;
  source: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
};

type AlarmResult = {
  unit_id: string;
  alert_count_last_hour: number;
  fatigue_detected: boolean;
  suppressed_count: number;
  top_priority_alert: AlarmEvent | null;
  recommendation: string;
};

type AlarmResponse = {
  unit_id: string;
  events: AlarmEvent[];
  result: AlarmResult;
};

function severityDot(sev: string) {
  if (sev === 'critical' || sev === 'high') return 'bg-crimson-vitals glow-crimson';
  if (sev === 'medium') return 'bg-amber-cyber glow-amber';
  return 'bg-slate-500';
}

function timeAgo(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  const secs = Math.floor((diffMs % 60000) / 1000);
  if (mins <= 0) return `${secs}s ago`;
  return `${mins}m ago`;
}

export default function AlarmFatigue() {
  const [unitId, setUnitId] = useState('unit-1');
  const [refreshKey, setRefreshKey] = useState(0);
  const [data, setData] = useState<AlarmResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`${API_BASE}/alarm-fatigue/demo/${unitId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        return res.json();
      })
      .then((json: AlarmResponse) => {
        if (!cancelled) {
          setData(json);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message ?? 'fetch failed');
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [unitId, refreshKey]);

  const events = data?.events ?? [];
  const result = data?.result ?? null;

  // Real per-severity distribution, used to shade the frequency chart honestly
  // (this is a SUMMARY visualization of real event severities, not a fake
  // random bar generator — it does not claim to be a 60-minute time series
  // unless/until the backend provides real per-minute bucketed counts)
  const severityCounts = useMemo(() => {
    const c = { low: 0, medium: 0, high: 0, critical: 0 };
    events.forEach((e) => {
      c[e.severity] = (c[e.severity] ?? 0) + 1;
    });
    return c;
  }, [events]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let raf = 0;
    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const draw = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);

      ctx.strokeStyle = 'rgba(255,255,255,0.04)';
      ctx.lineWidth = 1;
      for (let y = 0; y < h; y += 24) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      // Real severity distribution rendered as 4 grouped bars (low/med/high/critical)
      // — honest summary of actual event data, not a fabricated time series
      const groups = [
        { label: 'low', value: severityCounts.low, color: 'rgba(148,163,184,0.5)' },
        { label: 'medium', value: severityCounts.medium, color: 'rgba(255,170,0,0.6)' },
        { label: 'high', value: severityCounts.high, color: 'rgba(255,30,86,0.6)' },
        { label: 'critical', value: severityCounts.critical, color: 'rgba(255,30,86,0.9)' },
      ];
      const maxVal = Math.max(...groups.map((g) => g.value), 1);
      const bw = w / groups.length;
      groups.forEach((g, i) => {
        const bh = (g.value / maxVal) * h * 0.8;
        const x = i * bw + bw * 0.2;
        const y = h - bh;
        const grad = ctx.createLinearGradient(0, y, 0, h);
        grad.addColorStop(0, g.color);
        grad.addColorStop(1, g.color.replace(/[\d.]+\)$/, '0.05)'));
        ctx.fillStyle = grad;
        ctx.fillRect(x, y, bw * 0.6, bh);
      });

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [severityCounts]);

  return (
    <div className="flex h-full flex-col p-6">
      <PageHeader
        code="VIT·07 / ALARM FATIGUE"
        title="Alarm Fatigue Compensator"
        subtitle="Real alert stream across sensors, guardrails, and correlation engine — folded to surface only what matters."
        right={
          <div className="flex items-center gap-2">
            <select
              value={unitId}
              onChange={(e) => setUnitId(e.target.value)}
              className="hud-mono rounded border border-edge bg-transparent px-3 py-1.5 text-[10px] tracking-wider text-slate-300"
            >
              {UNITS.map((u) => (
                <option key={u.id} value={u.id} className="bg-[#0a0f0d]">
                  {u.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => setRefreshKey((k) => k + 1)}
              disabled={loading}
              className="hud-mono flex items-center gap-2 rounded border border-edge px-3 py-1.5 text-[10px] tracking-wider text-mint transition hover:bg-white/5 disabled:opacity-40"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              {loading ? 'SYNCING' : 'REFRESH'}
            </button>
          </div>
        }
      />

      {error && (
        <div className="mb-4 rounded border border-crimson-vitals/40 bg-crimson-vitals/10 px-4 py-2 text-[12px] text-crimson-vitals">
          Failed to load alarm data: {error}. Confirm the backend is running.
        </div>
      )}

      <div className="glass relative mb-4 overflow-hidden rounded-lg p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="hud-label">ALERT SEVERITY DISTRIBUTION</span>
          <span className="hud-mono text-[10px] text-slate-500">
            {events.length} real events this cycle
          </span>
        </div>
        <div className="h-32">
          <canvas ref={canvasRef} className="h-full w-full" />
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-2">
        <div className="glass flex flex-col overflow-hidden rounded-lg">
          <div className="flex items-center justify-between border-b border-edge px-4 py-3">
            <span className="hud-label">RAW ALERT FLOOD</span>
            <span className="hud-mono text-[10px] text-crimson-vitals glow-crimson">
              {events.length} alerts · unit {unitId.toUpperCase()}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {events.length === 0 && !loading && (
              <div className="p-4 text-[11px] text-slate-500">No alerts recorded for this unit right now.</div>
            )}
            {events.map((a, i) => (
              <motion.div
                key={`${a.timestamp}-${i}`}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mb-1 flex items-center gap-3 rounded px-2 py-1.5 hover:bg-white/[0.02]"
              >
                <span className={`h-1.5 w-1.5 rounded-full ${severityDot(a.severity)}`} />
                <span className="hud-mono text-[9px] text-slate-500">{timeAgo(a.timestamp)}</span>
                <span className="hud-mono text-[9px] text-slate-400">{a.source.toUpperCase()}</span>
                <span className="flex-1 text-[11px] text-slate-300">{a.message}</span>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <AnimatePresence mode="wait">
            {result?.fatigue_detected ? (
              <motion.div
                key="compensated"
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.96 }}
                transition={{ stiffness: 100, damping: 15 }}
                className="glass flex flex-1 flex-col rounded-lg border border-crimson-vitals/30 p-6"
                style={{ boxShadow: '0 0 30px rgba(255,30,86,0.15)' }}
              >
                <div className="hud-mono mb-3 flex items-center gap-2 text-[10px] tracking-[0.3em] text-crimson-vitals glow-crimson">
                  <Bell size={14} />
                  PRIMARY ALERT · FATIGUE COMPENSATION ACTIVE
                </div>
                {result.top_priority_alert && (
                  <>
                    <div className="hud-mono text-[14px] text-white">
                      {result.top_priority_alert.source.toUpperCase()}
                    </div>
                    <div className="mt-2 font-display text-[20px] font-semibold text-crimson-vitals glow-crimson">
                      {result.top_priority_alert.message}
                    </div>
                    <div className="hud-mono mt-2 text-[10px] text-slate-400">
                      {timeAgo(result.top_priority_alert.timestamp)} · severity {result.top_priority_alert.severity.toUpperCase()}
                    </div>
                  </>
                )}

                <div className="mt-auto flex items-center gap-3 rounded-md border border-mint/30 bg-mint/5 px-4 py-3">
                  <Layers size={14} className="text-mint glow-mint" />
                  <div>
                    <div className="hud-mono text-[12px] text-mint glow-mint">
                      {result.suppressed_count} ALERTS SUPPRESSED / SUMMARIZED
                    </div>
                    <div className="hud-mono mt-1 text-[10px] text-slate-500">{result.recommendation}</div>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="uncompensated"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="glass flex flex-1 flex-col items-center justify-center rounded-lg p-6 text-center"
              >
                <Bell size={32} className="text-slate-600" />
                <div className="mt-3 font-display text-[14px] text-slate-400">
                  {loading ? 'Loading alert stream…' : 'No fatigue suppression needed'}
                </div>
                <div className="mt-1 text-[11px] text-slate-500">
                  {result?.recommendation ?? 'Alert volume is within normal range for this unit.'}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}