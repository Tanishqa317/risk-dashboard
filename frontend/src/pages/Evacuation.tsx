import { useEffect, useRef, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import PageHeader from '../components/PageHeader';
import { Map, AlertTriangle, Users, Route as RouteIcon, RefreshCw } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';
const UNIT_ID = 'unit-1';

type WorkerNode = { id: string; label: string; x: number; y: number };
type DangerZone = { x: number; y: number; r: number; zone_id: string; gas_ppm: number };
type ExitNode = { id: string; x: number; y: number; label: string };
type ActivePath = { worker_id: string; status: string };

type EvacData = {
  unit_id: string;
  compromised: boolean;
  workers: WorkerNode[];
  danger_zones: DangerZone[];
  exit: ExitNode;
  active_paths: ActivePath[];
  evac_eta: string;
  eta_note: string;
};

export default function Evacuation() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [compromised, setCompromised] = useState(false);
  const [tick, setTick] = useState(0);
  const [data, setData] = useState<EvacData | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchEvac = useCallback(async (nextCompromised: boolean) => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(
        `${API_BASE}/evac-routing?unit_id=${UNIT_ID}&compromised=${nextCompromised}`,
      );
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const json: EvacData = await res.json();
      setData(json);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Failed to reach backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvac(false); // initial nominal load — no auto-polling
  }, [fetchEvac]);

  const workers = data?.workers ?? [];
  const dangerZones = data?.danger_zones ?? [];
  const exit = data?.exit ?? { id: 'EXIT', x: 0.92, y: 0.88, label: 'EXIT GATE' };

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 50);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let raf = 0;
    let t = 0;
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

      // Schematic background
      ctx.strokeStyle = 'rgba(255,255,255,0.06)';
      ctx.lineWidth = 1;
      const buildings = [
        [0.1, 0.1, 0.2, 0.25],
        [0.35, 0.1, 0.25, 0.2],
        [0.65, 0.1, 0.25, 0.3],
        [0.1, 0.55, 0.25, 0.3],
        [0.4, 0.55, 0.2, 0.3],
        [0.7, 0.55, 0.2, 0.3],
      ];
      buildings.forEach((b) => {
        ctx.strokeRect(b[0] * w, b[1] * h, b[2] * w, b[3] * h);
      });
      ctx.strokeStyle = 'rgba(255,255,255,0.04)';
      ctx.setLineDash([4, 6]);
      for (let i = 1; i < 4; i++) {
        ctx.beginPath();
        ctx.moveTo(0, (h * i) / 4);
        ctx.lineTo(w, (h * i) / 4);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // Danger zones — from real gas_ppm-derived data
      dangerZones.forEach((z, i) => {
        const cx = z.x * w;
        const cy = z.y * h;
        const r = z.r + Math.sin(t * 0.4 + i) * 6;
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        grad.addColorStop(0, 'rgba(255,30,86,0.25)');
        grad.addColorStop(0.6, 'rgba(255,170,0,0.1)');
        grad.addColorStop(1, 'rgba(255,30,86,0)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = `rgba(255,30,86,${0.3 + Math.sin(t * 0.4 + i) * 0.2})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(cx, cy, r * 0.7, 0, Math.PI * 2);
        ctx.stroke();
      });

      // Evacuation routing paths — curve from each worker to active exit
      const ex = exit.x * w;
      const ey = exit.y * h;
      workers.forEach((worker, i) => {
        const wx = worker.x * w;
        const wy = worker.y * h;
        const midX = compromised ? (wx + ex) / 2 + (i % 2 === 0 ? -50 : 50) : (wx + ex) / 2;
        const midY = compromised ? (wy + ey) / 2 - 30 : (wy + ey) / 2;

        ctx.strokeStyle = '#00ffaa';
        ctx.lineWidth = 1.4;
        ctx.shadowColor = 'rgba(0,255,170,0.6)';
        ctx.shadowBlur = 8;
        ctx.setLineDash([6, 6]);
        ctx.lineDashOffset = -t * 4;
        ctx.beginPath();
        ctx.moveTo(wx, wy);
        ctx.quadraticCurveTo(midX, midY, ex, ey);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.shadowBlur = 0;
      });

      // Exit gate marker
      ctx.fillStyle = '#00ffaa';
      ctx.shadowColor = 'rgba(0,255,170,0.8)';
      ctx.shadowBlur = 14;
      ctx.beginPath();
      ctx.arc(ex, ey, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = '#00ffaa';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(ex, ey, 12 + Math.sin(t * 0.5) * 2, 0, Math.PI * 2);
      ctx.stroke();

      t += 0.05;
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [compromised, tick, workers, exit, dangerZones]);

  const toggleCompromised = () => {
    const next = !compromised;
    setCompromised(next);
    fetchEvac(next);
  };

  return (
    <div className="flex h-full flex-col p-6">
      <PageHeader
        code="VIT-06 / EVACUATION"
        title="Evacuation Map & Rerouting"
        subtitle="Top-down site schematic with live worker nodes and dynamically optimized escape vectors."
        right={
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchEvac(compromised)}
              disabled={loading}
              className="glass glass-hover flex items-center gap-2 rounded-md px-3 py-2 text-[11px] text-slate-200 disabled:opacity-50"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              {loading ? 'LOADING' : 'REFRESH'}
            </button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={toggleCompromised}
              disabled={loading}
              className="flex items-center gap-2 rounded-md border border-crimson-vitals/40 bg-crimson-vitals/10 px-4 py-2 text-[11px] font-medium tracking-wider text-crimson-vitals glow-crimson transition-all hover:bg-crimson-vitals/20 disabled:opacity-50"
            >
              <AlertTriangle size={12} />
              {compromised ? 'RESET TO NOMINAL' : 'SIMULATE STRUCTURAL COMPROMISE'}
            </motion.button>
          </div>
        }
      />

      {fetchError && (
        <div className="mb-3 glass rounded-md border border-amber-cyber/30 px-4 py-2 hud-mono text-[10px] text-amber-cyber">
          BACKEND UNREACHABLE - {fetchError}
        </div>
      )}

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-4">
        <div className="glass relative overflow-hidden rounded-lg lg:col-span-3">
          <div className="absolute left-4 top-4 z-10 flex items-center gap-2">
            <Map size={14} className="text-mint glow-mint" />
            <span className="hud-label">SITE SCHEMATIC - EVAC ROUTING</span>
          </div>
          <div className="absolute right-4 top-4 z-10 hud-mono text-[10px] text-slate-500">
            {compromised ? '● COMPROMISED - REROUTING' : '● NOMINAL'}
          </div>
          <canvas ref={canvasRef} className="h-full w-full" />

          <svg className="pointer-events-none absolute inset-0 h-full w-full" preserveAspectRatio="none" viewBox="0 0 100 100">
            {workers.map((w, i) => (
              <motion.circle
                key={w.id}
                cx={w.x * 100}
                cy={w.y * 100}
                r={1.2}
                fill="#00ffaa"
                style={{ filter: 'drop-shadow(0 0 4px rgba(0,255,170,0.9))' }}
                initial={false}
                animate={{
                  cx: w.x * 100,
                  cy: w.y * 100,
                  scale: [1, 1.15, 1],
                }}
                transition={{
                  cx: { stiffness: 100, damping: 15 },
                  cy: { stiffness: 100, damping: 15 },
                  scale: { duration: 1.4, repeat: Infinity, ease: 'easeInOut', delay: i * 0.1 },
                }}
              />
            ))}
            {workers.map((w) => (
              <motion.text
                key={`${w.id}-label`}
                x={w.x * 100}
                y={w.y * 100 - 2.5}
                textAnchor="middle"
                fill="rgba(255,255,255,0.6)"
                style={{ fontSize: '2px', fontFamily: 'JetBrains Mono, monospace' }}
                initial={false}
                animate={{ x: w.x * 100, y: w.y * 100 - 2.5 }}
                transition={{ stiffness: 100, damping: 15 }}
              >
                {w.label}
              </motion.text>
            ))}
          </svg>
        </div>

        <div className="flex flex-col gap-4 overflow-y-auto">
          <div className="glass glass-hover rounded-lg p-5">
            <div className="flex items-center gap-2">
              <Users size={14} className="text-mint glow-mint" />
              <span className="hud-label">WORKERS IN TRANSIT</span>
            </div>
            <div className="hud-mono mt-2 text-[36px] font-semibold text-white glow-mint">
              {workers.length}
            </div>
            <div className="hud-mono text-[10px] text-slate-500">{workers.length} nodes - live tracking</div>
          </div>

          <div className="glass rounded-lg p-5">
            <div className="flex items-center gap-2">
              <RouteIcon size={14} className="text-mint glow-mint" />
              <span className="hud-label">ACTIVE PATHS</span>
            </div>
            <div className="mt-3 space-y-2">
              {(data?.active_paths ?? []).map((p) => (
                <div key={p.worker_id} className="flex items-center justify-between">
                  <span className="hud-mono text-[10px] text-slate-400">{p.worker_id}</span>
                  <span className="hud-mono text-[10px] text-mint glow-mint">{p.status}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass rounded-lg p-5">
            <div className="hud-label mb-3">EVAC ETA</div>
            <motion.div
              key={compromised ? 'comp' : 'nom'}
              initial={{ opacity: 0.6, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ stiffness: 100, damping: 15 }}
              className="hud-mono text-[28px] font-semibold text-mint glow-mint"
            >
              {data?.evac_eta ?? '--:--'}
            </motion.div>
            <div className="hud-mono mt-1 text-[10px] text-slate-500">{data?.eta_note ?? ''}</div>
          </div>
        </div>
      </div>
    </div>
  );
}