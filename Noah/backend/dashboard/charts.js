import { clock, downsample, driftValues, escapeHtml, inWindow, pct } from './model.js';

const C = {
  axis: '#888780', grid: '#88878040', line: '#378ADD', flag: '#E24B4A',
  warn: '#EF9F27', ok: '#1D9E75', pending: '#B4B2A9', trend: '#BFA574',
};

export function chartMarkup(points, kind, window, width, now, height) {
  const list = downsample(inWindow(points, window, now));
  const w = Math.max(260, Math.round(width));
  const h = Number.isFinite(height) && height >= 100
    ? Math.round(height)
    : w < 430 ? Math.max(118, Math.round(w * 290 / 900) + 20) : 218;
  const pad = { left: 39, right: 14, top: 15, bottom: 28 };
  const plotWidth = w - pad.left - pad.right;
  const plotHeight = h - pad.top - pad.bottom;
  const y = value => pad.top + plotHeight * (1 - value);
  const first = list[0]?.ts ?? now;
  const last = list.at(-1)?.ts ?? now;
  const span = Math.max(1, last - first);
  const x = ts => list.length < 2 ? pad.left + plotWidth / 2 : pad.left + plotWidth * (ts - first) / span;
  const scored = list.filter(point => point.risk !== null);
  const values = kind === 'risk' ? scored.map(point => point.risk) : driftValues(scored).map(value => Math.min(1, value));
  const title = kind === 'risk' ? 'Risk per action' : 'Drift';
  const ticks = kind === 'risk' ? [0, .25, .5, .75, 1] : [0, .5, 1];
  let content = ticks.map(value =>
    '<line x1="' + pad.left + '" y1="' + y(value) + '" x2="' + (w - pad.right) + '" y2="' + y(value) +
    '" stroke="' + C.grid + '"/><text x="' + (pad.left - 9) + '" y="' + (y(value) + 4) +
    '" text-anchor="end" fill="' + C.axis + '" font-size="11">' + pct(value) + '</text>').join('');

  if (!list.length || (kind === 'drift' && !scored.length)) {
    const message = window === 'all' ? (kind === 'risk' ? 'Risk appears as the agent acts' : 'Drift appears after the first check') : 'No checks in this window';
    content += '<text x="' + (w / 2 + 10) + '" y="' + (h / 2) +
      '" text-anchor="middle" fill="' + C.axis + '" font-size="12">' + message + '</text>';
  } else {
    const path = scored.map((point, index) =>
      (index ? 'L' : 'M') + x(point.ts).toFixed(1) + ' ' + y(values[index]).toFixed(1)).join(' ');
    if (kind === 'risk' && scored.length > 1) {
      content += '<path d="' + path + ' L' + x(scored.at(-1).ts).toFixed(1) + ' ' + y(0) +
        ' L' + x(scored[0].ts).toFixed(1) + ' ' + y(0) + ' Z" fill="' + C.line + '" fill-opacity=".12"/>';
    }
    content += list.filter(point => point.correction).map(point => {
      const px = x(point.ts);
      return '<line x1="' + px + '" y1="' + pad.top + '" x2="' + px + '" y2="' + y(0) +
        '" stroke="' + C.ok + '" stroke-width="1.5" stroke-dasharray="4 3"/>' +
        '<path d="M' + (px - 4) + ' ' + (pad.top - 7) + ' L' + (px + 4) + ' ' + (pad.top - 7) +
        ' L' + px + ' ' + pad.top + ' Z" fill="' + C.ok + '"/>';
    }).join('');
    content += '<path d="' + path + '" fill="none" stroke="' + (kind === 'risk' ? C.line : C.trend) +
      '" stroke-width="' + (kind === 'risk' ? '2' : '2.5') + '" stroke-linejoin="round"/>';
    content += scored.map((point, index) => {
      const color = kind === 'drift' ? C.trend : point.flagged ? C.flag : point.risk >= .5 ? C.warn : C.line;
      return '<circle cx="' + x(point.ts).toFixed(1) + '" cy="' + y(values[index]).toFixed(1) +
        '" r="' + (kind === 'risk' && point.flagged ? 4 : 2.7) + '" fill="' + color + '"><title>' +
        escapeHtml(clock(point.ts) + ' · ' + point.summary + ' · ' + pct(values[index])) + '</title></circle>';
    }).join('');
    if (kind === 'risk') {
      content += list.filter(point => point.risk === null && point.isPending).map(point =>
        '<circle cx="' + x(point.ts) + '" cy="' + y(0) + '" r="3" fill="none" stroke="' +
        C.pending + '" stroke-width="1.5"><title>Still checking</title></circle>').join('');
    }
    const intervals = [10000, 15000, 30000, 60000, 120000, 300000, 600000, 900000, 1800000,
      3600000, 7200000, 14400000, 43200000, 86400000, 172800000, 604800000];
    const targetTicks = Math.max(2, Math.floor(plotWidth / 75));
    const step = intervals.find(interval => span / interval <= targetTicks) ?? intervals.at(-1);
    const tickTimes = [];
    if (list.length < 2) tickTimes.push(first);
    else for (let time = Math.ceil(first / step) * step; time <= last; time += step) tickTimes.push(time);
    if (list.length > 1 && tickTimes.length < 2) tickTimes.splice(0, tickTimes.length, first, last);
    content += tickTimes.map(time => {
      const label = span >= 86400000
        ? new Date(time).toLocaleDateString([], { month: 'short', day: 'numeric' })
        : clock(time, span < 60000);
      const anchor = time === first ? 'start' : time === last ? 'end' : 'middle';
      return '<text x="' + x(time).toFixed(1) + '" y="' + (h - 6) +
        '" text-anchor="' + anchor + '" fill="' + C.axis + '" font-size="11">' + escapeHtml(label) + '</text>';
    }).join('');
  }
  return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + w + ' ' + h +
    '" role="img" aria-label="' + escapeHtml(title + ', ' + scored.length + ' scored checks') +
    '" font-family="Segoe UI, sans-serif"><title>' + escapeHtml(title) + '</title>' + content + '</svg>';
}
