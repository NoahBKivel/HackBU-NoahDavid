import { chartMarkup } from './charts.js';
import { assessment, fleetAssessment, sessionHealth, clock, escapeHtml as esc, pct, riskColor, riskLabel, WINDOWS } from './model.js';
import { previewSessions } from './preview-data.js';
import { mergeSessionSnapshot } from './live-data.js';

const preview = new URLSearchParams(location.search).get('preview') === '1';
let sessions = preview ? previewSessions() : [];
let sourceStatus = preview ? 'Sample data' : 'Connecting…';
let sourceLoaded = preview;
let cursor = '';
let lastRenderedAt = 0;
const hosted = !['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
const dashboardEndpoint = hosted ? 'https://davidkny22--alignment-monitor-api.us-east.modal.run/v1/dashboard/sessions' : '/api/dashboard/sessions';
let dashboardReadToken = '';
const agentNav = document.querySelector('#agents');
const view = document.querySelector('#agent-view');
const states = new Map();
let selected = sessions[0];
let resizeObserver;
let route = { page: 'home' };
let renderedRoute;
let stoppedAgentsOnly = false;

function stateFor(session) {
  if (!states.has(session.id)) states.set(session.id, { risk: 'all', drift: 'all', flags: false, recent: false });
  return states.get(session.id);
}

function relativeTime(ts) {
  const minutes = Math.max(0, Math.floor((Date.now() - ts) / 60000));
  return minutes < 1 ? 'Last seen just now' : 'Last seen ' + minutes + ' min ago';
}

function icon(name) {
  const paths = {
    folder: '<path d="M3 5.5h5l1.5 2H17v9H3z"/>',
    session: '<circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="2" fill="currentColor" stroke="none"/>',
    checking: '<path d="M10 3.5a6.5 6.5 0 1 1-6.5 6.5"/><path d="M3.5 4v6H9"/>',
    chevron: '<path d="m7.5 5 5 5-5 5"/>',
    back: '<path d="m12 5-5 5 5 5"/>',
    info: '<circle cx="10" cy="10" r="7"/><path d="M10 9v4"/><path d="M10 6.5h.01"/>',
    home: '<path d="m3 9 7-6 7 6v8h-5v-5H8v5H3z"/>',
    agents: '<rect x="3" y="3" width="14" height="14" rx="2"/><path d="M7 7h6M7 10h6M7 13h3"/>',
    arrow: '<path d="M4 10h12m-5-5 5 5-5 5"/>',
    attention: '<path d="m10 3 8 14H2z"/><path d="M10 8v4m0 2h.01"/>',
    healthy: '<path d="m4 10 4 4 8-8"/>',
    intervention: '<path d="M8.3 3.8a2 2 0 0 1 3.4 0l6 10.4a2 2 0 0 1-1.7 3H4a2 2 0 0 1-1.7-3z"/><path d="M10 7.5v4.5m0 2.5h.01"/>',
  };
  return '<svg class="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + paths[name] + '</svg>';
}

function renderAgents() {
  document.querySelector('#agent-count').textContent = String(sessions.length);
  const projects = new Map();
  for (const session of sessions) {
    if (!projects.has(session.name)) projects.set(session.name, []);
    projects.get(session.name).push(session);
  }
  agentNav.innerHTML = [...projects].map(([name, agents]) =>
    '<section class="project-group"><h3 class="project-name">' + icon('folder') + esc(name) + '</h3>' +
    agents.map(session => {
    const minutes = Math.max(0, Math.floor((Date.now() - (session.lastSeenAt ?? session.points.at(-1)?.ts ?? Date.now())) / 60000));
    const age = minutes < 1 ? 'now' : minutes + 'm';
    const checking = session.points.some(point => point.isPending);
    const intervention = sessionHealth(session) === 'attention';
    return '<a class="agent-link" href="#agent/' + encodeURIComponent(session.id) + '" title="' + esc(session.task) +
      '" aria-label="' + esc(session.task + ' in ' + session.name + (intervention ? ', user intervention needed' : checking ? ', checking' : '')) + '"' +
      (route.page === 'agent' && selected?.id === session.id ? ' aria-current="page"' : '') + '>' +
      '<span class="agent-state ' + (intervention ? 'error' : checking ? 'warning' : '') + '">' + icon(intervention ? 'attention' : checking ? 'checking' : 'session') + '</span>' +
      '<span class="agent-task">' + esc(session.task) + '</span>' +
      '<span class="agent-age">' + age + '</span></a>';
    }).join('') + '</section>').join('');
}

function metric(label, value, color) {
  return '<div class="metric"><dt class="metric-label">' + label + '</dt><dd class="metric-value ' + color +
    '">' + esc(value) + '</dd></div>';
}

function info(kind) {
  const rows = kind === 'risk'
    ? '<p>How likely each checked action is to break your instructions. Lower is better.</p>' +
      '<div class="legend-row"><span class="legend-dot" style="--legend-color:#378add"></span>Blue: checked</div>' +
      '<div class="legend-row"><span class="legend-dot" style="--legend-color:#ef9f27"></span>Yellow: elevated risk</div>' +
      '<div class="legend-row"><span class="legend-dot" style="--legend-color:#e24b4a"></span>Red: flagged</div>' +
      '<div class="legend-row"><span class="legend-line"></span>Correction sent to the agent</div>' +
      '<div class="legend-row"><span class="legend-dot" style="--legend-color:#b4b2a9"></span>Gray outline: still checking</div>'
    : '<p>How far off course the run is. Lower is better.</p>' +
      '<p>Uses the classifier’s drift when available, or the average risk of the last five checks as an estimate.</p>' +
      '<p>↑ Rising · ↓ Falling · → Steady<br>A dashed green line marks a correction.</p>';
  return '<details class="info"><summary aria-label="About ' + (kind === 'risk' ? 'risk per action' : 'drift') +
    '">' + icon('info') + '</summary><div class="info-popup">' + rows + '</div></details>';
}

function chartCard(kind) {
  const title = kind === 'risk' ? 'Risk per action' : 'Drift';
  const state = stateFor(selected);
  return '<section class="chart-card" aria-label="' + title + '">' +
    '<div class="chart-heading"><h2>' + title + '</h2>' +
    '<div class="chart-tools"><div class="windows" role="group" aria-label="' + title + ' window">' +
    WINDOWS.map(option => '<button class="window-button" type="button" data-chart="' + kind +
      '" data-window="' + option.id + '" aria-pressed="' + (state[kind] === option.id) + '">' +
      option.label + '</button>').join('') + '</div>' + info(kind) + '</div></div>' +
    '<div class="chart" id="' + kind + '-chart"></div></section>';
}

function details(point) {
  const rows = Object.entries(point.details ?? {}).filter(([key]) => key !== 'mock');
  return '<div class="event-detail">' +
    '<div class="detail-meta">Monitor: ' + esc(point.monitor ?? 'unknown') + ' · Tool: ' +
    esc(point.tool) + ' · ' + clock(point.ts) + '</div>' +
    '<p class="detail-entry"><strong>Action:</strong> ' + esc(point.summary) + '</p>' +
    '<p class="detail-entry"><strong>Risk:</strong> ' + (point.isPending ? 'Still checking' : pct(point.risk)) +
    (point.flagged ? ' (flagged)' : '') + '</p>' +
    (point.error ? '<p class="detail-entry error">No result: ' + esc(point.error) + '</p>' : '') +
    rows.map(([key, value]) => '<p class="detail-entry"><strong>' + esc(label(key)) + ':</strong> ' +
      esc(typeof value === 'string' ? value : JSON.stringify(value)) + '</p>').join('') +
    point.notices.map(notice => '<p class="detail-entry warning">Notice (' + esc(notice.level) + '): ' +
      esc(notice.text) + '</p>').join('') +
    (point.correction ? '<p class="detail-entry success">' +
      (point.corrected ? 'Correction sent: ' : 'Correction queued: ') + esc(point.correction) + '</p>' : '') +
    '</div>';
}

function label(key) {
  const words = key.replaceAll('_', ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function eventList(kind) {
  const state = stateFor(selected);
  const points = selected.points.filter(point => kind !== 'flags' || point.flagged).slice().reverse();
  const total = kind === 'recent' ? Math.min(50, points.length) : points.length;
  const shown = state[kind] ? points.slice(0, total) : points.slice(0, 3);
  const title = kind === 'flags' ? 'Flagged actions (' + total + ')' : 'Recent checks';
  return '<div class="section-heading"><h2>' + title + '</h2>' +
    (total > 3 ? '<button class="more-button" type="button" data-more="' + kind + '">' +
      (state[kind] ? 'Show less' : 'Show ' + (total - 3) + ' more') + '</button>' : '') + '</div>' +
    (points.length ? shown.map(point =>
      '<details class="event-row" data-event-id="' + esc(kind + '-' + point.eventId) + '">' +
      '<summary><span class="disclosure">' + icon('chevron') + '</span>' +
      '<time class="event-time">' + clock(point.ts) + '</time>' +
      (kind === 'recent' ? '<span class="event-tool">' + esc(point.tool) + '</span>' : '') +
      '<span class="event-summary">' + esc(point.summary) + '</span>' +
      '<span class="event-risk ' + (point.flagged ? 'error' : '') + '">' +
      (point.risk === null ? '' : pct(point.risk)) + '</span></summary>' + details(point) + '</details>').join('') :
      '<p class="empty-list">' + (kind === 'flags' ? 'Nothing flagged so far.' : 'Waiting for the agent to act.') + '</p>');
}

function drawCharts() {
  for (const kind of ['risk', 'drift']) {
    const chart = document.querySelector('#' + kind + '-chart');
    if (chart) {
      const height = matchMedia('(min-width: 1000px)').matches ? chart.clientHeight : undefined;
      chart.innerHTML = chartMarkup(selected.points, kind, stateFor(selected)[kind], chart.clientWidth, Date.now(), height);
    }
  }
}

function renderView() {
  resizeObserver?.disconnect();
  const stats = assessment(selected.points);
  const risk = stats.latest?.risk ?? null;
  const color = riskColor(risk, stats.latest?.flagged);
  const checking = selected.points.some(point => point.isPending);
  document.title = 'VISION — ' + selected.name;
  view.innerHTML = '<div class="session-header"><div class="session-heading"><h1>' + esc(selected.task) + '</h1></div>' +
    '<div class="connection">' + (checking ? '<span class="connection-line warning"><span class="mini-dot"></span>Checking...</span>' : '') +
    '<span class="last-seen">' + relativeTime(selected.points.at(-1)?.ts ?? Date.now()) + '</span></div></div>' +
    '<dl class="metrics" aria-label="Session statistics">' +
    '<div class="metric current-risk"><dt class="metric-label">Current risk</dt><dd class="metric-value"><span>' + pct(risk) +
    '</span><span class="risk-label ' + color + '">' + (stats.latest ? riskLabel(risk, stats.latest.flagged) : 'Unscored') +
    '</span></dd></div>' +
    metric('Drift', pct(stats.drift === null ? null : Math.min(1, stats.drift)) + (stats.arrow ? ' ' + stats.arrow : ''), '') +
    metric('Max risk', pct(stats.peak), '') +
    metric('Average risk', pct(stats.average), '') +
    metric('Flags', String(stats.flags), stats.flags ? 'error' : '') +
    metric('Corrections', String(stats.corrections), '') +
    '</dl><div class="charts">' + chartCard('risk') + chartCard('drift') + '</div>' +
    '<div class="event-lists"><section class="list-section" id="flags-list" aria-label="Flagged actions">' +
    eventList('flags') + '</section><section class="list-section" id="recent-list" aria-label="Recent checks">' +
    eventList('recent') + '</section></div>';
  drawCharts();
  let previousSize = '';
  resizeObserver = new ResizeObserver(entries => {
    const { width, height } = entries[0].contentRect;
    const size = Math.round(width) + ':' + Math.round(height);
    if (size !== previousSize) { previousSize = size; drawCharts(); }
  });
  resizeObserver.observe(document.querySelector('.charts'));
}

function healthPie(fleet) {
  const slices = [
    { value: fleet.healthy, color: '#7eac8b' },
    { value: fleet.attention, color: '#cf8d82' },
    { value: fleet.unknown, color: '#606060' },
  ];
  let angle = -Math.PI / 2;
  const polar = theta => [100 + 90 * Math.cos(theta), 100 + 90 * Math.sin(theta)];
  const paths = slices.filter(slice => slice.value > 0).map(slice => {
    if (slice.value === fleet.active) return '<circle cx="100" cy="100" r="90" fill="' + slice.color + '"/>';
    const start = polar(angle);
    const sweep = slice.value / fleet.active * Math.PI * 2;
    angle += sweep;
    const end = polar(angle);
    return '<path d="M100 100 L' + start.join(' ') + ' A90 90 0 ' + (sweep > Math.PI ? 1 : 0) + ' 1 ' + end.join(' ') +
      ' Z" fill="' + slice.color + '" stroke="var(--bg)" stroke-width="2"/>';
  }).join('');
  return '<svg viewBox="0 0 200 200" role="img" aria-label="Agent health: ' + fleet.healthy + ' good health, ' +
    fleet.attention + ' need user attention, ' + fleet.unknown + ' unreported">' +
    '<defs><mask id="home-health-ring"><rect width="200" height="200" fill="white"/><circle cx="100" cy="100" r="54" fill="black"/></mask></defs>' +
    '<g mask="url(#home-health-ring)">' + (paths || '<circle cx="100" cy="100" r="90" fill="var(--line)"/>') + '</g></svg>';
}

function renderHome() {
  if (!sourceLoaded && !sessions.length) {
    view.innerHTML = '<div class="home-overview"><div class="home-heading"><p class="home-wordmark">VISION</p><h1>Agent overview</h1></div>' +
      '<p class="empty-list">' + (sourceStatus === 'Connecting…' ? 'Loading agent activity…' : 'Unable to load agent activity. Retrying…') + '</p></div>';
    return;
  }
  const fleet = fleetAssessment(sessions);
  const recent = [...sessions].sort((a, b) =>
    Number(sessionHealth(b) === 'attention') - Number(sessionHealth(a) === 'attention') ||
    (b.lastSeenAt ?? b.points.at(-1)?.ts ?? 0) - (a.lastSeenAt ?? a.points.at(-1)?.ts ?? 0)).slice(0, 3);
  const attentionInfo = '<span class="health-info"><button type="button" aria-label="About needs attention" aria-describedby="attention-tooltip">' + icon('info') +
    '</button><span class="health-tooltip" id="attention-tooltip" role="tooltip">Needs attention indicates that the classifier requested a stop for user input.</span></span>';
  const legendRow = (label, value, state) => '<div><dt><span class="health-dot ' + state + '"></span><span>' + label + '</span>' +
    (state === 'attention' ? attentionInfo : '') + '</dt><dd>' + value +
    '<span>' + (fleet.active ? Math.round(value / fleet.active * 100) : 0) + '%</span></dd></div>';
  view.innerHTML = '<div class="home-overview"><div class="home-heading"><p class="home-wordmark">VISION</p><h1>Agent overview</h1></div>' +
    '<div class="home-body"><section class="home-health" aria-label="Agent health summary"><div class="health-pie">' + healthPie(fleet) + '</div>' +
    '<div class="health-summary"><div class="health-summary-heading"><p class="health-total"><strong>' + fleet.active +
    '</strong> active agent' + (fleet.active === 1 ? '' : 's') + '</p></div>' +
    '<dl class="health-legend" aria-label="Agent health counts">' + legendRow('Good health', fleet.healthy, 'healthy') +
    legendRow('Needs attention', fleet.attention, 'attention') + (fleet.unknown ? legendRow('Unreported', fleet.unknown, 'unknown') : '') +
    '</dl></div></section>' +
    '<section class="home-agents" aria-labelledby="home-activity-title"><div class="panel-heading"><h2 id="home-activity-title">Agents</h2>' +
    '<a class="home-agents-link" href="#agents">See all' + icon('arrow') + '</a></div>' +
    '<ul class="home-activity">' + recent.map(session => {
      const point = session.points.at(-1);
      const health = sessionHealth(session);
      const attention = health === 'attention';
      return '<li><a class="home-activity-row" href="#agent/' + encodeURIComponent(session.id) + '">' +
        '<span class="home-activity-main"><strong class="home-agent-title" title="' + esc(session.task) + '">' + esc(session.task) + '</strong>' +
        '<span class="home-agent-project" title="' + esc(session.name) + '">' + icon('folder') + '<span>' + esc(session.name) + '</span></span>' +
        '<span class="home-agent-state agent-health-status ' + health + '">' + icon(attention ? 'intervention' : health === 'healthy' ? 'healthy' : 'info') +
        (attention ? 'Needs attention' : health === 'healthy' ? 'Healthy' : 'Unreported') + '</span><span class="home-agent-time">' +
        esc(relativeTime(session.lastSeenAt ?? point?.ts ?? Date.now()).replace('Last seen ', '')) + '</span></span></a></li>';
    }).join('') + '</ul>' + (recent.length ? '' : '<p class="empty-list">No agents reporting yet.</p>') + '</section></div></div>';
}

function renderAgentDirectory() {
  const fleet = fleetAssessment(sessions);
  const visibleSessions = stoppedAgentsOnly ? sessions.filter(session => sessionHealth(session) === 'attention') : sessions;
  const projects = new Map();
  for (const session of visibleSessions) {
    if (!projects.has(session.name)) projects.set(session.name, []);
    projects.get(session.name).push(session);
  }
  view.innerHTML = '<div class="page-heading directory-page-heading"><h1>Agents</h1>' +
    '<div class="directory-controls"><p class="directory-health-counts"><span>' + icon('healthy') + '<strong>' + fleet.healthy + '</strong> healthy</span>' +
    '<span>' + icon('intervention') + '<strong>' + fleet.attention + '</strong> ' + (fleet.attention === 1 ? 'needs' : 'need') + ' attention</span>' +
    (fleet.unknown ? '<span>' + fleet.unknown + ' unreported</span>' : '') + '</p>' +
    '<button class="directory-filter" type="button" data-stopped-filter aria-controls="agent-directory" aria-pressed="' + stoppedAgentsOnly + '">' +
    (stoppedAgentsOnly ? 'Remove filter' : 'View problems') + '</button></div></div>' +
    '<p class="directory-total">' + fleet.active + ' agent' + (fleet.active === 1 ? '' : 's') + ' total</p>' +
    '<div class="agent-directory" id="agent-directory" aria-live="polite">' + [...projects].map(([project, agents], index) =>
      '<section class="directory-project" aria-labelledby="directory-project-' + index + '"><h2 id="directory-project-' + index + '">' +
      icon('folder') + esc(project) + '</h2><ul class="directory-project-agents">' + agents.map(session => {
      const latest = assessment(session.points).latest;
      const health = sessionHealth(session);
      const status = health === 'attention' ? 'Needs attention' : health === 'healthy' ? 'Healthy' : 'Unreported';
      return '<li><a class="directory-row" href="#agent/' + encodeURIComponent(session.id) + '">' +
        '<strong class="directory-task">' + esc(session.task) + '</strong>' +
        '<span class="directory-risk"><span>Risk:</span><strong>' + pct(latest?.risk ?? null) + '</strong></span>' +
        '<span class="directory-status agent-health-status ' + health + '">' + icon(health === 'attention' ? 'intervention' : health === 'healthy' ? 'healthy' : 'info') + status +
        '</span><span class="directory-seen">' + relativeTime(session.lastSeenAt ?? session.points.at(-1)?.ts ?? Date.now()).replace('Last seen ', '') + '</span></a></li>';
    }).join('') + '</ul></section>').join('') +
    (visibleSessions.length ? '' : '<p class="empty-list">' + (stoppedAgentsOnly ? 'No agents need attention.' : 'No agents reporting yet.') + '</p>') + '</div>';
}

function readRoute() {
  if (location.hash === '#agents') return { page: 'agents' };
  if (location.hash.startsWith('#agent/')) {
    try {
      const session = sessions.find(item => item.id === decodeURIComponent(location.hash.slice(7)));
      if (session) return { page: 'agent', session };
    } catch { /* Unknown or malformed routes return home. */ }
  }
  return { page: 'home' };
}

function navigate(options = {}) {
  const refresh = options.refresh === true;
  const openDetails = refresh ? new Set([...view.querySelectorAll('details[open]')].map(item => item.dataset.eventId)) : new Set();
  const focusFilter = refresh && document.activeElement?.hasAttribute('data-stopped-filter');
  const focused = refresh && view.contains(document.activeElement) ? document.activeElement : null;
  const focusedWindow = focused?.dataset.window;
  const focusedChart = focused?.dataset.chart;
  const focusedMore = focused?.dataset.more;
  const focusedSummary = focused?.tagName === 'SUMMARY' ? focused.parentElement.dataset.eventId : null;
  route = readRoute();
  const key = route.page + (route.session?.id ?? '');
  if (renderedRoute === key && !refresh) return;
  renderedRoute = key;
  resizeObserver?.disconnect();
  if (route.session) selected = route.session;
  document.querySelectorAll('[data-page]').forEach(link => {
    const active = link.dataset.page === (route.page === 'agent' ? 'agents' : route.page);
    if (active) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  document.querySelector('#navigation-back').disabled = route.page === 'home' && !(history.state?.visionDepth > 0);
  renderAgents();
  if (route.page === 'agent') renderView();
  else if (route.page === 'agents') renderAgentDirectory();
  else renderHome();
  renderDataNote();
  if (refresh) {
    view.querySelectorAll('details').forEach(item => { item.open = openDetails.has(item.dataset.eventId); });
    if (focusFilter) view.querySelector('[data-stopped-filter]')?.focus({ preventScroll: true });
    if (focusedWindow) [...view.querySelectorAll('[data-window]')].find(button => button.dataset.window === focusedWindow && button.dataset.chart === focusedChart)?.focus({ preventScroll: true });
    if (focusedMore) [...view.querySelectorAll('[data-more]')].find(button => button.dataset.more === focusedMore)?.focus({ preventScroll: true });
    if (focusedSummary) [...view.querySelectorAll('details')].find(item => item.dataset.eventId === focusedSummary)?.querySelector('summary')?.focus({ preventScroll: true });
  }
  document.title = 'VISION — ' + (route.page === 'agent' ? selected.name : route.page === 'agents' ? 'Agents' : 'Home');
  if (!refresh) window.scrollTo(0, 0);
  lastRenderedAt = Date.now();
}

function renderDataNote() {
  view.insertAdjacentHTML('beforeend', '<p class="data-note" role="status">' + esc(sourceStatus) + '</p>');
  document.querySelector('#data-status').textContent = sourceStatus;
}

function setSourceStatus(status) {
  sourceStatus = status;
  document.querySelector('#data-status').textContent = status;
  const note = view.querySelector('.data-note');
  if (note) note.textContent = status;
}

async function pollSessions() {
  try {
    const response = await fetch(dashboardEndpoint + (cursor ? '?cursor=' + encodeURIComponent(cursor) : ''), {
      cache: 'no-store', signal: AbortSignal.timeout(15000),
      ...(hosted ? { headers: { Authorization: 'Bearer ' + dashboardReadToken } } : {}),
    });
    if (hosted && response.status === 401) {
      sessionStorage.removeItem('vision-dashboard-read-token');
      setSourceStatus('Access key rejected · reload to try again');
      return;
    }
    if (!response.ok) throw new Error('Dashboard answered ' + response.status);
    const batch = await response.json();
    const updated = mergeSessionSnapshot(sessions, batch);
    const changed = !sourceLoaded || batch.cursor !== cursor;
    sessions = updated;
    cursor = batch.cursor;
    sourceLoaded = true;
    selected = sessions.find(session => session.id === selected?.id) ?? sessions[0];
    setSourceStatus('Live data');
    if (changed || Date.now() - lastRenderedAt > 60000) navigate({ refresh: true });
  } catch {
    setSourceStatus(sourceLoaded ? 'Connection lost · showing last received data' : 'Connection unavailable · retrying');
    if (!sourceLoaded) navigate({ refresh: true });
  } finally {
    if (!hosted || sourceStatus !== 'Access key rejected · reload to try again') setTimeout(pollSessions, 1000);
  }
}

function go(hash) {
  if (location.hash === hash || (!location.hash && hash === '#home')) return;
  history.pushState({ visionDepth: (history.state?.visionDepth ?? 0) + 1 }, '', hash);
  navigate();
  view.focus({ preventScroll: true });
}

document.querySelectorAll('[data-icon]').forEach(element => { element.innerHTML = icon(element.dataset.icon); });
document.addEventListener('click', event => {
  const link = event.target.closest('a[href^="#"]');
  if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  go(link.getAttribute('href') === '#' ? '#home' : link.getAttribute('href'));
});
document.querySelector('#navigation-back').addEventListener('click', () => {
  if (history.state?.visionDepth > 0) history.back();
  else go(route.page === 'agent' ? '#agents' : '#home');
});

view.addEventListener('click', event => {
  if (event.target.closest('[data-stopped-filter]')) {
    stoppedAgentsOnly = !stoppedAgentsOnly;
    renderAgentDirectory();
    renderDataNote();
    view.querySelector('[data-stopped-filter]').focus({ preventScroll: true });
    return;
  }
  const windowButton = event.target.closest('[data-window]');
  if (windowButton) {
    const kind = windowButton.dataset.chart;
    stateFor(selected)[kind] = windowButton.dataset.window;
    windowButton.closest('.windows').querySelectorAll('button').forEach(button =>
      button.setAttribute('aria-pressed', String(button === windowButton)));
    drawCharts();
  }
  const moreButton = event.target.closest('[data-more]');
  if (moreButton) {
    const kind = moreButton.dataset.more;
    const list = document.querySelector('#' + kind + '-list');
    const open = new Set([...list.querySelectorAll('details[open]')].map(item => item.dataset.eventId));
    stateFor(selected)[kind] = !stateFor(selected)[kind];
    list.innerHTML = eventList(kind);
    list.querySelectorAll('details').forEach(item => { item.open = open.has(item.dataset.eventId); });
    list.querySelector('.more-button')?.focus();
  }
});

window.addEventListener('hashchange', navigate);
window.addEventListener('popstate', navigate);
if (!Number.isInteger(history.state?.visionDepth)) history.replaceState({ visionDepth: 0 }, '');
navigate();
if (!preview) {
  if (hosted) {
    dashboardReadToken = sessionStorage.getItem('vision-dashboard-read-token') || window.prompt('VISION dashboard access key (read-only):')?.trim() || '';
    if (dashboardReadToken) sessionStorage.setItem('vision-dashboard-read-token', dashboardReadToken);
  }
  if (!hosted || dashboardReadToken) void pollSessions();
  else setSourceStatus('Access key required · reload to connect');
}
