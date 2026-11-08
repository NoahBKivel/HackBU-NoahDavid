// The calculations and display bands follow Noah/mod/hooks/register.tsx.
// They are presentation logic; the classifier owns the flagged field.
export const WINDOWS = [
  { id: 'last10', label: 'Last 10', ms: Infinity },
  { id: 'hour', label: '1h', ms: 3600000 },
  { id: 'day', label: '1d', ms: 86400000 },
  { id: 'week', label: '1w', ms: 604800000 },
  { id: 'all', label: 'All', ms: Infinity },
];

export function rollingRisk(risks, index, window = 5) {
  const values = risks.slice(Math.max(0, index - window + 1), index + 1);
  return values.length ? values.reduce((sum, risk) => sum + risk, 0) / values.length : 0;
}

export function driftValues(scored) {
  const risks = scored.map(point => point.risk);
  return scored.map((point, index) =>
    typeof point.drift === 'number' ? point.drift : rollingRisk(risks, index));
}

export function assessment(points) {
  const scored = points.filter(point => typeof point.risk === 'number');
  const latest = scored.at(-1);
  const risks = scored.map(point => point.risk);
  const drift = driftValues(scored);
  const currentDrift = drift.at(-1) ?? null;
  const previousDrift = drift.at(-2) ?? null;
  const rate = latest?.driftRate ??
    (currentDrift !== null && previousDrift !== null ? currentDrift - previousDrift : null);
  return {
    latest,
    drift: currentDrift,
    rate,
    arrow: rate === null ? '' : rate > 0.005 ? '↑' : rate < -0.005 ? '↓' : '→',
    trendColor: rate === null ? 'subtle' : rate > 0.005 ? 'error' : rate < -0.005 ? 'success' : 'subtle',
    peak: risks.length ? Math.max(...risks) : null,
    average: risks.length ? risks.reduce((sum, risk) => sum + risk, 0) / risks.length : null,
    flags: points.filter(point => point.flagged).length,
    corrections: points.filter(point => point.correction !== null).length,
  };
}

export function sessionHealth(session) {
  const reported = [...session.points].sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0)).findLast(point =>
    !point.isPending && typeof point.requires_user_intervention === 'boolean');
  if (!reported) return 'unknown';
  return reported.requires_user_intervention ? 'attention' : 'healthy';
}

export function fleetAssessment(sessions) {
  const fleet = { active: sessions.length, healthy: 0, attention: 0, unknown: 0 };
  for (const session of sessions) fleet[sessionHealth(session)]++;
  return fleet;
}

export function inWindow(points, window, now) {
  if (window === 'last10') return points.filter(point => point.risk !== null || point.isPending).slice(-10);
  const ms = WINDOWS.find(option => option.id === window)?.ms ?? Infinity;
  return ms === Infinity ? points : points.filter(point => point.ts >= now - ms);
}

export function downsample(points) {
  if (points.length <= 120) return points;
  const first = points[0]?.ts ?? 0;
  const span = Math.max(1, (points.at(-1)?.ts ?? 0) - first);
  const buckets = new Map();
  const score = point => (point.flagged ? 2 : 0) + (point.correction ? 1 : 0) + (point.risk ?? 0);
  for (const point of points) {
    const bucket = Math.min(119, Math.floor(((point.ts - first) / span) * 120));
    const kept = buckets.get(bucket);
    if (!kept || score(point) > score(kept)) buckets.set(bucket, point);
  }
  const kept = [...buckets.values()];
  if (!kept.includes(points.at(-1))) kept.push(points.at(-1));
  return kept.sort((left, right) => left.ts - right.ts);
}

export function riskColor(risk, flagged = false) {
  if (risk === null || risk === undefined) return 'subtle';
  if (flagged || risk >= 0.7) return 'error';
  if (risk >= 0.4) return 'warning';
  return 'success';
}

export function riskLabel(risk, flagged = false) {
  if (flagged) return 'Flagged';
  if (risk === null || risk === undefined) return 'Unknown';
  if (risk >= 0.7) return 'High';
  if (risk >= 0.4) return 'Elevated';
  return 'Low';
}

export function pct(value) {
  return typeof value === 'number' ? Math.round(value * 100) + '%' : '--';
}

export function clock(ts, seconds = true) {
  return new Date(ts).toLocaleTimeString([], {
    hour: '2-digit', minute: '2-digit', ...(seconds ? { second: '2-digit' } : {}), hour12: false,
  });
}

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}
