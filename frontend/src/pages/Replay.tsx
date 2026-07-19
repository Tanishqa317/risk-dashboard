import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import PageHeader from '../components/PageHeader';
import { History, GitBranch, Play, Pause, FastForward, RefreshCw } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';
const UNIT_ID = 'unit-1'; // TODO: wire to global unit selector if/when one exists

type TimelineEvent = {
  t: number;
  label: string;
  tone: 'mint' | 'amber' | 'crimson';
  zone?: string;
};

type ReplayData = {
  unit_id: string;
  window_hours: number;
  timeline: TimelineEvent[];
  historical_series: number[];
  counterfactual_series: number[];
};

export default function Replay() {
  const [scrub, setScrub] = useState(0.23);
  const [playing, setPlaying] = useState(true);
  const [hoveredEvent, setHoveredEvent] = useState<string | null>(null);
  const [data, setData] = useState<ReplayData | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const histCanvas = useRef<HTMLCanvasElement>(null);
  const cfCanvas = useRef<HTMLCanvasElement>(null);

  const fetchReplay = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(`${API_BASE}/replay?unit_id=${UNIT_ID}`);
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const json: ReplayData = await res.json();
      setData(json);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Failed to reach backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReplay(); // one-time load — no auto-polling
  }, [fetchReplay]);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setScrub((s) => (s >= 1 ? 0 : s + 0.004));
    }, 60);
    return () => clearInterval(id);
  }, [playing]);

  useEffect(() => {
    if (!data) return;

    const draw = (
      canvas: HTMLCanvasElement | null,
      series: number[],
      color: string,
      glow: string,
    ) => {
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);

      // Grid
      ctx.strokeStyle = 'rgba(255,255,255,0.04)';
      ctx.lineWidth = 1;
      for (let y = 0; y < h; y += 28) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
      for (let x = 0; x < w; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }

      const min = Math.min(...series);
      const max = Math.max(...series);
      const range = max - min || 1;
      const mid = h * 0.55;
      const scaleY = (v: number) => mid - ((v - min) / range - 0.5) * (h * 0.7);

      ctx.strokeStyle = color;
      ctx.lineWidth = 1.4;
      ctx.shadowColor = glow;
      ctx.shadowBlur = 8;
      ctx.beginPath();
      series.forEach((v, i) => {
        const x = (i / (series.length - 1)) * w;
        const y = scaleY(v);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Scrub head
      const sx = scrub * w;
      const idx = Math.min(series.length - 1, Math.floor(scrub * series.length));
      ctx.strokeStyle = 'rgba(255,255,255,0.3)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(sx, 0);
      ctx.lineTo(sx, h);
      ctx.stroke();
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(sx, scaleY(series[idx]), 3, 0, Math.PI * 2);
      ctx.fill();
    };

    draw(histCanvas.current, data.historical_series, '#00ffaa', 'rgba(0,255,170,0.5)');
    draw(cfCanvas.current, data.counterfactual_series, '#ff1e56', 'rgba(255,30,86,0.5)');

    const ro = new ResizeObserver(() => {
      draw(histCanvas.current, data.historical_series, '#00ffaa', 'rgba(0,255,170,0.5)');
      draw(cfCanvas.current, data.counterfactual_series, '#ff1e56', 'rgba(255,30,86,0.5)');
    });
    if (histCanvas.current) ro.observe(histCanvas.current);
    if (cfCanvas.current) ro.observe(cfCanvas.current);
    return () => ro.disconnect();
  }, [scrub, data]);

  const events = data?.timeline ?? [];
  const currentEvents = useMemo(() => events.filter((e) => e.t <= scrub), [events, scrub]);
  // index (within `events`) of the most recently passed event — used to ring it distinctly
  const activeIdx = useMemo(() => {
    let idx = -1;
    events.forEach((e, i) => {
      if (e.t <= scrub) idx = i;
    });
    return idx;
  }, [events, scrub]);
  const windowHours = data?.window_hours ?? 24;
  const timeLabel = `T+${String(Math.floor(scrub * windowHours)).padStart(2, '0')}:${String(
    Math.floor((scrub * windowHours * 60) % 60),
  ).padStart(2, '0')}:${String(Math.floor((scrub * windowHours * 3600) % 60)).padStart(2, '0')}`;

  return (
    <div className="flex h-full flex-col overflow-y-auto p-6">
      <PageHeader
        code="VIT·04 / COUNTERFACTUAL REPLAY"
        title="Counterfactual Replay Engine"
        subtitle="Digital Twin stress-test — historical reality vs. adversarial permit-gaming counterfactual."
        right={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchReplay}
              disabled={loading}
              className="glass glass-hover flex items-center gap-2 rounded-md px-3 py-2 text-[11px] text-slate-200 disabled:opacity-50"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              {loading ? 'LOADING' : 'REFRESH'}
            </button>
            <button
              onClick={() => setPlaying((p) => !p)}
              className="glass glass-hover flex items-center gap-2 rounded-md px-3 py-2 text-[11px] text-slate-200"
            >
              {playing ? <Pause size={12} /> : <Play size={12} />}
              {playing ? 'PAUSE' : 'PLAY'}
            </button>
            <button
              onClick={() => setScrub((s) => Math.min(1, s + 0.05))}
              className="glass glass-hover rounded-md px-3 py-2 text-slate-200"
            >
              <FastForward size={12} />
            </button>
          </div>
        }
      />

      {fetchError && (
        <div className="mb-3 glass rounded-md border border-amber-cyber/30 px-4 py-2 hud-mono text-[10px] text-amber-cyber">
          BACKEND UNREACHABLE · {fetchError}
        </div>
      )}

      <div className="grid flex-1 min-h-[300px] grid-cols-1 gap-4 overflow-hidden lg:grid-cols-2">
        <Viewport
          title="HISTORICAL REALITY PATH"
          subtitle="Recorded telemetry · 24h crisis window"
          icon={History}
          tone="mint"
          canvasRef={histCanvas}
          timeLabel={timeLabel}
        />
        <Viewport
          title="COUNTERFACTUAL PROJECTION"
          subtitle="Without Adversarial Permit-Gaming Detector"
          icon={GitBranch}
          tone="crimson"
          canvasRef={cfCanvas}
          timeLabel={timeLabel}
        />
      </div>

      <div className="glass mt-4 shrink-0 rounded-lg p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="hud-label">TIMELINE · {windowHours}H CRISIS WINDOW</span>
          <span className="hud-mono text-[11px] text-mint glow-mint">{timeLabel}</span>
        </div>
        <div className="relative">
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={scrub}
            onChange={(e) => {
              setPlaying(false);
              setScrub(parseFloat(e.target.value));
            }}
            className="hud-range w-full"
          />
          <div className="relative mt-3 h-16">
            {events.map((e, i) => {
              const dotColor =
                e.tone === 'mint' ? '#00ffaa' : e.tone === 'amber' ? '#ffaa00' : '#ff1e56';
              const isHovered = hoveredEvent === e.label;
              const isPassed = e.t <= scrub;
              const isActive = i === activeIdx;
              return (
                <div
                  key={e.label}
                  className="absolute flex -translate-x-1/2 flex-col items-center"
                  style={{ left: `${e.t * 100}%`, opacity: isPassed ? 1 : 0.35 }}
                  onMouseEnter={() => setHoveredEvent(e.label)}
                  onMouseLeave={() => setHoveredEvent(null)}
                >
                  <span
                    className="cursor-pointer rounded-full transition-all"
                    style={{
                      width: isActive ? 10 : 8,
                      height: isActive ? 10 : 8,
                      background: dotColor,
                      boxShadow: isActive
                        ? `0 0 0 3px ${dotColor}33, 0 0 10px ${dotColor}`
                        : `0 0 6px ${dotColor}99`,
                    }}
                  />
                  <span
                    className="hud-mono mt-2 hidden origin-top-left whitespace-nowrap text-[8px] text-slate-500 lg:block"
                    style={{ transform: 'rotate(35deg)' }}
                  >
                    {e.label}
                  </span>
                  {isHovered && (
                    <div
                      className="glass hud-mono absolute top-6 z-20 whitespace-nowrap rounded-md border border-edge px-2 py-1 text-[10px] shadow-lg"
                      style={{ color: dotColor }}
                    >
                      {e.label}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
        <div className="mt-4 max-h-20 overflow-y-auto">
          {currentEvents.slice(-4).map((e, i) => (
            <motion.div
              key={`${e.label}-${i}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3 py-0.5"
            >
              <span
                className="hud-mono text-[9px] tracking-wider"
                style={{
                  color: e.tone === 'mint' ? '#00ffaa' : e.tone === 'amber' ? '#ffaa00' : '#ff1e56',
                }}
              >
                T+{String(Math.floor(e.t * windowHours)).padStart(2, '0')}:{String(
                  Math.floor((e.t * windowHours * 60) % 60),
                ).padStart(2, '0')}
              </span>
              <span className="text-[11px] text-slate-300">{e.label}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Viewport({
  title,
  subtitle,
  icon: Icon,
  tone,
  canvasRef,
  timeLabel,
}: {
  title: string;
  subtitle: string;
  icon: React.ElementType;
  tone: 'mint' | 'crimson';
  canvasRef: React.RefObject<HTMLCanvasElement>;
  timeLabel: string;
}) {
  const c = tone === 'mint' ? 'text-mint glow-mint' : 'text-crimson-vitals glow-crimson';
  return (
    <div className="glass relative flex flex-col overflow-hidden rounded-lg">
      <div className="flex items-center justify-between border-b border-edge px-4 py-3">
        <div className="flex items-center gap-2">
          <Icon size={14} className={c} />
          <div>
            <div className={`hud-mono text-[11px] tracking-wider ${c}`}>{title}</div>
            <div className="hud-mono text-[9px] text-slate-500">{subtitle}</div>
          </div>
        </div>
        <span className="hud-mono text-[10px] text-slate-400">{timeLabel}</span>
      </div>
      <div className="relative flex-1">
        <canvas ref={canvasRef} className="h-full w-full" />
      </div>
    </div>
  );
}