import React from 'react';
import './styles.css';

type RiskZoneGlowProps = {
  risk_score: number;
  zone_label: string;
  subtitle?: string;
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

const getGlowPalette = (score: number) => {
  if (score < 35) {
    return {
      inner: '#a7f3d0',
      outer: '#4ade80',
      accent: '#22c55e',
    };
  }

  if (score < 70) {
    return {
      inner: '#fde68a',
      outer: '#f59e0b',
      accent: '#f97316',
    };
  }

  return {
    inner: '#fecaca',
    outer: '#f43f5e',
    accent: '#dc2626',
  };
};

const getRiskLabel = (score: number) => {
  if (score < 35) return 'Low risk';
  if (score < 70) return 'Moderate risk';
  return 'High risk';
};

export default function RiskZoneGlow({ risk_score, zone_label, subtitle }: RiskZoneGlowProps) {
  const score = clamp(Math.round(risk_score), 0, 100);
  const ratio = score / 100;
  const palette = getGlowPalette(score);
  const duration = Math.max(0.9, 3 - 2.1 * ratio).toFixed(2);

  return (
    <div
      className="risk-zone-glow"
      style={{
        '--glow-inner': palette.inner,
        '--glow-outer': palette.outer,
        '--glow-accent': palette.accent,
        '--pulse-duration': `${duration}s`,
      } as React.CSSProperties}
    >
      <div className="risk-zone-glow__content">
        <div className="risk-zone-glow__header">
          <span className="risk-zone-glow__label">{zone_label}</span>
          <span className="risk-zone-glow__score">{score}</span>
        </div>
        <p className="risk-zone-glow__description">{subtitle || getRiskLabel(score)}</p>
      </div>
    </div>
  );
}
