import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import PageHeader from '../components/PageHeader';
import {
  ClipboardCheck,
  BookOpen,
  AlertCircle,
  CheckCircle2,
  FileWarning,
  RefreshCw,
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';
const UNIT_ID = 'unit-1'; // TODO: wire to global unit selector if/when one exists

type Status = 'Compliant' | 'Minor Deviation' | 'Major Deviation';
type Anomaly = {
  id: string;
  regulation: string;
  anomaly: string;
  severity: 'minor' | 'major';
  recommendation: string;
  citation: string;
  status: Status;
};

// Backend has no severity field — derive it from keyword signals in the
// corrective action text. This is a heuristic, not authoritative; flag to
// the backend team that Gemini should ideally return severity explicitly.
const MAJOR_KEYWORDS = ['halt', 'immediately', 'immediate', 'stand-down', 'stop operations', 'critical', 'shut down'];

function deriveSeverity(actionText: string): 'minor' | 'major' {
  const lower = actionText.toLowerCase();
  return MAJOR_KEYWORDS.some((kw) => lower.includes(kw)) ? 'major' : 'minor';
}

function mapStatus(raw: string): Status {
  if (raw === 'major_deviation') return 'Major Deviation';
  if (raw === 'minor_deviation') return 'Minor Deviation';
  if (raw === 'compliant') return 'Compliant';
  return 'Minor Deviation'; // fallback for 'unknown'
}

// New backend shape: one array of self-contained anomaly objects instead of
// three parallel arrays. This removes the index-zipping that used to
// backfill "No citation provided" / "No description provided" placeholders.
type RawAnomaly = {
  deviation: string;
  corrective_action: string;
  regulatory_reference: string;
};

type ComplianceResponse = {
  unit_id: string;
  compliance_status: string;
  anomalies: RawAnomaly[];
  error?: string;
};

function formatBackendError(raw: string | null): string {
  if (!raw) return 'Unknown error';
  if (raw.includes('RESOURCE_EXHAUSTED')) {
    return 'Gemini daily quota exceeded (429). Try again after quota resets.';
  }
  if (raw.includes('PERMISSION_DENIED')) {
    return 'Gemini API key rejected (403). Check API key/project configuration.';
  }
  // Fallback: truncate anything else so a raw stack trace never fills the UI
  return raw.length > 120 ? `${raw.slice(0, 120)}…` : raw;
}

export default function Compliance() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [selected, setSelected] = useState<Anomaly | null>(null);
  const [filter, setFilter] = useState<'all' | 'minor' | 'major'>('all');
  const [loading, setLoading] = useState(false);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [complianceStatus, setComplianceStatus] = useState<string>('unknown');

  const fetchAudit = useCallback(async () => {
    setLoading(true);
    setBackendError(null);
    try {
      const res = await fetch(`${API_BASE}/compliance-audit/${UNIT_ID}`);
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data: ComplianceResponse = await res.json();

      setComplianceStatus(data.compliance_status);

      if (data.error) {
        setBackendError(data.error);
      }

      // Each item is now a self-contained object — no more zipping parallel
      // arrays by index, and no more placeholder backfill. Any item missing
      // a field was already filtered out server-side; this is a client-side
      // belt-and-braces check in case of an older cached/fallback payload.
      const mapped: Anomaly[] = (data.anomalies ?? [])
        .filter(
          (a) =>
            a &&
            a.deviation?.trim() &&
            a.corrective_action?.trim() &&
            a.regulatory_reference?.trim(),
        )
        .map((a, i) => {
          const severity = deriveSeverity(a.corrective_action);
          return {
            id: `AN-${String(i + 1).padStart(3, '0')}`,
            regulation: a.regulatory_reference,
            anomaly: a.deviation,
            severity,
            recommendation: a.corrective_action,
            citation: a.regulatory_reference,
            status: severity === 'major' ? 'Major Deviation' : 'Minor Deviation',
          };
        });

      setAnomalies(mapped);
      setSelected(mapped[0] ?? null);
    } catch (err) {
      setBackendError(err instanceof Error ? err.message : 'Failed to reach backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAudit(); // one-time load — no auto-polling, protects Gemini quota
  }, [fetchAudit]);

  const filtered = anomalies.filter((a) => filter === 'all' || a.severity === filter);
  const majorCount = anomalies.filter((a) => a.severity === 'major').length;
  const minorCount = anomalies.filter((a) => a.severity === 'minor').length;
  const overall: Status = mapStatus(complianceStatus);

  const isGeminiUnavailable = backendError && anomalies.length === 0;

  return (
    <div className="flex h-full flex-col p-6">
      <PageHeader
        code="VIT·09 / COMPLIANCE AUDIT"
        title="Compliance Audit Agent"
        subtitle="RAG-corpus agent — live regulatory anomaly detection with corrective actions and direct citations."
        right={
          <button
            onClick={fetchAudit}
            disabled={loading}
            className="glass glass-hover flex items-center gap-2 rounded-md px-3 py-2 text-[11px] text-slate-200 disabled:opacity-50"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            {loading ? 'AUDITING...' : 'RE-RUN AUDIT'}
          </button>
        }
      />

      {isGeminiUnavailable && (
        <div className="mb-4 glass rounded-md border border-amber-cyber/30 px-4 py-3 hud-mono text-[11px] text-amber-cyber">
          COMPLIANCE ENGINE UNAVAILABLE · {formatBackendError(backendError)}
          <div className="mt-1 text-slate-400">
            This audit relies on Gemini and no cached result was found. Try again once quota resets.
          </div>
        </div>
      )}

      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div
          className={`glass rounded-lg p-4 ${
            overall === 'Major Deviation'
              ? 'border-crimson-vitals/30'
              : overall === 'Minor Deviation'
                ? 'border-amber-cyber/30'
                : 'border-mint/30'
          }`}
        >
          <div className="hud-label">OVERALL STATUS</div>
          <div className="mt-2 flex items-center gap-2">
            {overall === 'Major Deviation' ? (
              <FileWarning size={20} className="text-crimson-vitals glow-crimson" />
            ) : overall === 'Minor Deviation' ? (
              <AlertCircle size={20} className="text-amber-cyber glow-amber" />
            ) : (
              <CheckCircle2 size={20} className="text-mint glow-mint" />
            )}
            <span
              className={`font-display text-[18px] font-semibold ${
                overall === 'Major Deviation'
                  ? 'text-crimson-vitals glow-crimson'
                  : overall === 'Minor Deviation'
                    ? 'text-amber-cyber glow-amber'
                    : 'text-mint glow-mint'
              }`}
            >
              {anomalies.length === 0 && isGeminiUnavailable ? 'Unavailable' : overall}
            </span>
          </div>
        </div>
        <div className="glass rounded-lg p-4">
          <div className="hud-label">MAJOR DEVIATIONS</div>
          <div className="hud-mono mt-2 text-[28px] font-semibold text-crimson-vitals glow-crimson">
            {majorCount}
          </div>
        </div>
        <div className="glass rounded-lg p-4">
          <div className="hud-label">MINOR DEVIATIONS</div>
          <div className="hud-mono mt-2 text-[28px] font-semibold text-amber-cyber glow-amber">
            {minorCount}
          </div>
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-5">
        <div className="glass flex flex-col overflow-hidden rounded-lg lg:col-span-3">
          <div className="flex items-center justify-between border-b border-edge px-4 py-3">
            <div className="flex items-center gap-2">
              <ClipboardCheck size={14} className="text-mint glow-mint" />
              <span className="hud-label">REGULATORY ANOMALY MATRIX</span>
            </div>
            <div className="flex items-center gap-1">
              {(['all', 'minor', 'major'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`hud-mono rounded border px-2 py-1 text-[9px] tracking-wider transition-all ${
                    filter === f
                      ? 'border-mint/40 bg-mint/10 text-mint'
                      : 'border-edge text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {f.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-y-auto">
            {filtered.length === 0 && (
              <div className="p-6 hud-mono text-[11px] text-slate-500">
                {loading
                  ? 'Running audit...'
                  : isGeminiUnavailable
                    ? 'No anomalies to show — compliance engine unavailable.'
                    : 'No anomalies found for this filter.'}
              </div>
            )}
            {filtered.map((a, i) => (
              <motion.button
                key={a.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ stiffness: 100, damping: 15, delay: i * 0.04 }}
                onClick={() => setSelected(a)}
                className={`grid w-full grid-cols-12 items-center gap-2 border-b border-edge px-4 py-3 text-left transition-colors ${
                  selected?.id === a.id ? 'bg-mint/5' : 'hover:bg-white/[0.02]'
                }`}
              >
                <div className="col-span-2 hud-mono text-[10px] text-slate-400">{a.id}</div>
                <div className="col-span-4 hud-mono text-[10px] text-amber-cyber">{a.regulation}</div>
                <div className="col-span-5 text-[11px] text-slate-300">{a.anomaly}</div>
                <div className="col-span-1 flex justify-end">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      a.severity === 'major' ? 'bg-crimson-vitals glow-crimson' : 'bg-amber-cyber glow-amber'
                    }`}
                  />
                </div>
              </motion.button>
            ))}
          </div>
        </div>

        <div className="glass glass-hover flex flex-col overflow-y-auto rounded-lg p-5 lg:col-span-2">
          <div className="mb-3 flex items-center gap-2">
            <BookOpen size={14} className="text-mint glow-mint" />
            <span className="hud-label">CORPUS·CITATION · DETAIL</span>
          </div>

          {selected ? (
            <>
              <div className="hud-mono text-[11px] text-amber-cyber">{selected.regulation}</div>
              <div className="mt-1 font-display text-[16px] font-medium text-white">
                {selected.anomaly}
              </div>
              <div className="mt-3">
                <span
                  className={`hud-mono rounded border px-2 py-1 text-[9px] tracking-wider ${
                    selected.severity === 'major'
                      ? 'border-crimson-vitals/40 bg-crimson-vitals/10 text-crimson-vitals glow-crimson'
                      : 'border-amber-cyber/40 bg-amber-cyber/10 text-amber-cyber glow-amber'
                  }`}
                >
                  {selected.severity.toUpperCase()} · {selected.status.toUpperCase()}
                </span>
              </div>

              <div className="mt-5">
                <div className="hud-label mb-2">RECOMMENDED CORRECTIVE ACTION</div>
                <p className="text-[12px] font-light leading-relaxed text-slate-200">
                  {selected.recommendation}
                </p>
              </div>

              <div className="mt-5 rounded-md border border-edge bg-black/30 p-3">
                <div className="hud-label mb-2">DIRECT CITATION</div>
                <p className="hud-mono text-[11px] leading-relaxed text-slate-400">
                  {selected.citation}
                </p>
              </div>
            </>
          ) : (
            <div className="hud-mono text-[11px] text-slate-500">
              No anomaly selected — run the audit to populate results.
            </div>
          )}

          <div className="mt-auto pt-5">
            <div className="hud-mono text-[10px] text-slate-500">
              {loading ? 'Auditing...' : `Unit ${UNIT_ID} · live compliance-audit endpoint`}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}