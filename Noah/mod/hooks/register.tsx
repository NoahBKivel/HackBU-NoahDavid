import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Conn, Correction, Item, Notice, Point, Todo } from '../types'

const PLUGIN = 'vision'
// Tools the mock classifier treats as history only (no score), like David's side does.
const READ_TOOLS = new Set(['Read', 'Grep', 'Glob', 'WebFetch', 'WebSearch', 'LS', 'NotebookRead'])
const MAX_EVENT_BYTES = 5_000_000
const FETCH_TIMEOUT_MS = 60_000
const MAX_POINTS = 2000
const CHART_POINTS = 120

type $ = EngineInterface
type Action = { type?: string; level?: string; text?: string }
type Result = {
  event_id?: string
  monitor?: string
  flagged?: boolean
  risk?: number | null
  drift?: number | null
  drift_rate?: number | null
  pending?: boolean
  details?: { [key: string]: unknown }
  actions?: Action[]
  late_results?: Result[]
}
type Event = { [key: string]: unknown } & { event_id: string; type: string }

// Change a shape tag whenever that value's fields change, so a reload
// drops what an older version stored instead of drawing it wrong.
const points = atom({ plugin: 'vision', key: 'points' } as const, [], { shape: 'points-2' })
const conn = atom({ plugin: 'vision', key: 'conn' } as const, 'connecting')
const corrections = atom({ plugin: 'vision', key: 'corrections' } as const, [])
const pending = atom({ plugin: 'vision', key: 'pending' } as const, [])
const seq = atom({ plugin: 'vision', key: 'seq' } as const, 0)
const instructionCount = atom({ plugin: 'vision', key: 'instructionCount' } as const, 0)
const expanded = atom({ plugin: 'vision', key: 'expanded' } as const, null)
const todos = atom({ plugin: 'vision', key: 'todos' } as const, [])
const session = atom({ plugin: 'vision', key: 'session' } as const, null)
const windows = atom({ plugin: 'vision', key: 'windows' } as const, { risk: 'all', trend: 'all' })
const listsOpen = atom({ plugin: 'vision', key: 'listsOpen' } as const, { flags: false, recent: false })

// How many rows the flagged and recent lists show before "Show more".
const FLAGS_SHOWN = 3
const RECENT_SHOWN = 3

// Time windows a chart can show, by the label drawn next to its title.
const WINDOWS: { id: string; label: string; ms: number }[] = [
  { id: 'hour', label: '1h', ms: 60 * 60 * 1000 },
  { id: 'day', label: '1d', ms: 24 * 60 * 60 * 1000 },
  { id: 'week', label: '1w', ms: 7 * 24 * 60 * 60 * 1000 },
  { id: 'all', label: 'All', ms: Infinity },
]

// The agent's visible text and displayed thinking since the last event
// was built. Kept in the module, not $.state, because it grows every step.
let stepText = { text: '', thinking: '' }

// Backend settings from the Mod's options. Hooks pass $ only to functions
// declared at the top of this file, so settings live here, not in a closure.
const config = { apiUrl: '', apiToken: '', isLive: false }

export const register: Register = (on, options) => {
  config.apiUrl = typeof options.apiUrl === 'string' ? options.apiUrl.replace(/\/+$/, '') : ''
  config.apiToken = typeof options.apiToken === 'string' ? options.apiToken : ''
  config.isLive = config.apiUrl !== '' && config.apiToken !== ''
  const isLive = config.isLive

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    trace($, `session.start live=${isLive}`)
    try {
      await $.command.register({
        name: 'alignment',
        description: 'Open the alignment monitor pane. Add "sample" to load test history (mock mode only).',
        argumentHint: '[sample]',
      })
      const id = await $.session.id()
      const known = await read($, session)
      if (known?.id !== id) {
        await startSession($, id)
      } else {
        // A reload ends any check still in flight; those never get an answer.
        await update($, points, list =>
          list.map(p => (p.isPending ? { ...p, isPending: false, error: 'Interrupted by a Mod reload' } : p)),
        )
      }
      if (!isLive) {
        const current = await read($, points)
        if (!current.some(p => p.eventId.startsWith('sample-'))) await loadSample($)
      } else {
        // Connected to the real backend: drop any sample history from mock mode.
        await update($, points, list => list.filter(p => !p.eventId.startsWith('sample-')))
      }
      void $.ui.open({ id: 'alignment', title: 'VISION' })
      await refreshStatus($, isLive)
    } catch (error) {
      debug($, 'session.start', error)
    }
    return result
  })

  on('command.run', { command: 'alignment' }, async ($, e) => {
    await $.ui.open({ id: 'alignment', title: 'VISION', focus: true })
    if (e.args.trim() === 'sample') {
      if (isLive) return { text: 'Sample history is only available with the mock classifier.' }
      const count = await loadSample($)
      return { text: `Loaded ${count} sample checks spanning the past 10 days.` }
    }
    return { text: 'Alignment monitor pane opened.' }
  })

  on('prompt.submit', async ($, e, next) => {
    try {
      if (e.isMeta !== true && e.text.trim() !== '') {
        const n = await update($, instructionCount, count => count + 1)
        const item: Item = {
          kind: 'user_instruction',
          id: `I${n}`,
          text: e.text,
          ts: new Date(await $.clock.now()).toISOString(),
        }
        if (e.command) item.command = { name: e.command.name, args: e.command.args }
        if (e.attachments?.length) {
          item.attachments = e.attachments.map(a => ({ type: a.type, filename: a.filename ?? null }))
        }
        await update($, pending, list => [...list, item])
      }
    } catch (error) {
      debug($, 'prompt.submit', error)
    }
    return next(e)
  })

  on('turn.step', async function* ($, e, next) {
    let text = ''
    let thinking = ''
    for await (const chunk of next(e)) {
      if (chunk.kind === 'text') text += chunk.text
      else if (chunk.kind === 'thinking') thinking += chunk.text
      yield chunk
    }
    if (e.agentId === undefined) {
      stepText = {
        text: [stepText.text, text].filter(Boolean).join('\n\n'),
        thinking: [stepText.thinking, thinking].filter(Boolean).join('\n\n'),
      }
    }
  })

  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    trace($, `tool.call ${e.tool} agent=${e.agentId ?? 'main'} deny=${ran.deny !== undefined}`)
    if (e.agentId !== undefined) return ran
    try {
      if (e.tool === 'TodoWrite') {
        const list = (e as { todos?: Todo[] }).todos ?? []
        await update($, todos, () => list.map(t => ({ content: t.content, status: t.status })))
      }

      let answer = ran
      if (ran.deny === undefined) {
        const queued = await read($, corrections)
        trace($, `queued corrections: ${queued.length}`)
        if (queued.length > 0) {
          await update($, corrections, () => [])
          await markCorrected($, queued)
          answer = { ...ran, context: [...(ran.context ?? []), ...queued.map(q => q.text)] } as typeof ran
        }
      }

      const event = await toolEvent($, e as unknown as Record<string, unknown>, ran as unknown as Record<string, unknown>)
      void dispatch($, event, describeTool(e as unknown as Record<string, unknown>), isLive)
      if (DEBUG_CONTEXT && answer.deny === undefined) {
        const note = `[vision debug] ${traceLines.slice(-10).join(' | ')}`
        answer = { ...answer, context: [...(answer.context ?? []), note] } as typeof ran
      }
      return answer
    } catch (error) {
      debug($, 'tool.call', error)
      return ran
    }
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId === undefined) {
      try {
        const event = await baseEvent($, 'turn_completed', `turn-${e.turnId}`)
        event.agent_text = e.answer
        event.turn = { reason: e.reason, duration_ms: e.durationMs, is_aborted: e.isAborted }
        void dispatch($, event, { tool: 'Turn', summary: 'Agent finished its turn' }, isLive)
      } catch (error) {
        debug($, 'turn.complete', error)
      }
    }
    return result
  })

  on('ui.render', { component: 'Pane', requestId: 'alignment' }, async ($, e) =>
    renderPane($, $.ui.resolve(e) as unknown as Elements, isLive),
  )
}

// ---------- Event building and sending ----------

async function startSession($: $, id: string) {
  const now = await $.clock.now()
  await update($, session, () => ({ id, startedAt: now }))
  await update($, points, () => [])
  await update($, corrections, () => [])
  await update($, pending, () => [])
  await update($, seq, () => 0)
  await update($, instructionCount, () => 0)
  await update($, expanded, () => null)
  await update($, todos, () => [])
  await update($, conn, () => 'connecting')

  if (config.isLive) void warmUp($)

  const root = await $.session.root()
  const docs: Item[] = []
  for (const name of ['CLAUDE.md', 'AGENTS.md', 'README.md']) {
    try {
      const text = await $.fs.read(`${root}/${name}`)
      docs.push({ kind: 'project_doc', path: name, text })
    } catch {
      // The project has no such file.
    }
  }
  await update($, pending, list => [...list, ...docs])

  const event = await baseEvent($, 'session_started', `session-${id}`)
  const [repo, model, version] = await Promise.all([
    $.session.repo().catch(() => null),
    $.session.model().catch(() => null),
    $.session.version().catch(() => null),
  ])
  event.session = {
    id,
    cwd: await $.session.cwd(),
    root,
    repo,
    model,
    claude_code_version: version?.version ?? null,
    surface: await $.session.surface(),
  }
  void dispatch($, event, null, config.isLive)
}

async function warmUp($: $) {
  try {
    await $.http.fetch(`${config.apiUrl}/health`)
  } catch (error) {
    debug($, 'warm-up', error)
  }
}

// Hands over the text gathered since the last event and starts afresh.
let lastTaken = { text: '', thinking: '' }
function takeStepText() {
  lastTaken = stepText
  stepText = { text: '', thinking: '' }
  return lastTaken
}

async function baseEvent($: $, type: string, eventId: string): Promise<Event> {
  const n = await update($, seq, count => count + 1)
  const items = await read($, pending)
  await update($, pending, () => [])
  const info = await read($, session)
  return {
    schema_version: 1,
    session_id: info?.id ?? null,
    event_id: eventId,
    seq: n,
    type,
    ts: new Date(await $.clock.now()).toISOString(),
    new_items: items,
    agent_text: takeStepText().text,
    agent_thinking: lastTaken.thinking,
    todos: await read($, todos),
  }
}

async function toolEvent($: $, e: Record<string, unknown>, ran: Record<string, unknown>) {
  const { tool, tool_use_id, agentId, requestMeta, consent, ...args } = e
  const event = await baseEvent($, 'tool_completed', String(tool_use_id))
  const result = sanitize(ran.result) as Record<string, unknown> | undefined
  // Claude Code keeps only a preview of long shell output and saves the
  // rest to a file; send the whole output.
  if (result && typeof result.rawOutputPath === 'string') {
    try {
      result.full_output = await $.fs.read(result.rawOutputPath)
    } catch (error) {
      debug($, 'raw output', error)
    }
  }
  event.action = {
    tool,
    args: sanitize(args),
    denied: typeof ran.deny === 'string' ? ran.deny : null,
    result_text: typeof ran.text === 'string' ? ran.text : null,
    is_error: ran.isError === true,
    result: result ?? null,
    file_changes: fileChanges(String(tool), args, result),
  }
  return event
}

// Sends one event and applies what comes back. Never awaited by a hook, so
// the agent carries on while the classifier works.
async function dispatch(
  $: $,
  event: Event,
  label: { tool: string; summary: string } | null,
  live: boolean,
) {
  const now = await $.clock.now()
  if (label) {
    const point: Point = {
      eventId: event.event_id,
      seq: Number(event.seq),
      ts: now,
      tool: label.tool,
      summary: label.summary,
      risk: null,
      flagged: false,
      corrected: false,
      isPending: true,
      monitor: null,
      details: {},
      notices: [],
      correction: null,
      error: null,
      drift: null,
      driftRate: null,
    }
    await update($, points, list => [...list, point].slice(-MAX_POINTS))
  }
  await update($, conn, () => 'classifying')
  await refreshStatus($, live)
  trace($, `dispatch start ${event.type} ${event.event_id}`)

  try {
    const result = live ? await post($, event) : await mockClassify($, event)
    trace($, `dispatch result ${event.event_id} risk=${result.risk} actions=${result.actions?.length ?? 0}`)
    await applyResult($, event.event_id, result)
    for (const late of result.late_results ?? []) {
      if (typeof late.event_id === 'string') await applyResult($, late.event_id, late)
    }
    trace($, `dispatch applied ${event.event_id} late=${result.late_results?.length ?? 0}`)
    await update($, conn, () => 'live')
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    await patchPoint($, event.event_id, p => ({ ...p, isPending: false, error: message }))
    await update($, conn, () => 'error')
    debug($, 'dispatch', error)
  }
  await refreshStatus($, live)
}

async function post($: $, event: Event): Promise<Result> {
  const request = $.http.fetch(`${config.apiUrl}/v1/events`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${config.apiToken}` },
    body: capEvent(event),
  })
  const timeout = $.clock.sleep(FETCH_TIMEOUT_MS).then(() => null)
  const res = await Promise.race([request, timeout])
  if (res === null) throw new Error('The classifier did not answer in time')
  if (!res.ok) throw new Error(`The backend answered ${res.status}`)
  return JSON.parse(res.text) as Result
}

async function applyResult($: $, eventId: string, result: Result) {
  if (result.pending === true) {
    // Still classifying on David's side; the result comes later in late_results.
    await patchPoint($, eventId, p => ({ ...p, isPending: true, details: result.details ?? p.details }))
    return
  }
  const notices: Notice[] = []
  let correction: string | null = null

  for (const action of result.actions ?? []) {
    const text = typeof action.text === 'string' ? action.text : ''
    if (action.type === 'notify_user' && text) {
      const level = action.level ?? 'detected'
      notices.push({ level, text })
      await notify($, level, text)
    } else if (action.type === 'inject_agent' && text) {
      correction = text
      await update($, corrections, list => [...list, { eventId, text }])
    } else {
      debug($, 'actions', `Unknown action ${JSON.stringify(action)}`)
    }
  }

  await patchPoint($, eventId, p => ({
    ...p,
    isPending: false,
    risk: typeof result.risk === 'number' ? clamp01(result.risk) : null,
    drift: typeof result.drift === 'number' ? result.drift : null,
    driftRate: typeof result.drift_rate === 'number' ? result.drift_rate : null,
    flagged: result.flagged === true,
    monitor: result.monitor ?? null,
    details: result.details ?? {},
    notices,
    correction,
  }))
}


// ---------- Notices, corrections and status ----------

async function notify($: $, level: string, text: string) {
  const line = `Alignment monitor (${level}): ${text}`
  if (level === 'potential') {
    $.ui.log(line)
    return
  }
  await $.session.append({ message: { type: 'system', content: [{ type: 'text', text: line }] } })
}

async function markCorrected($: $, sent: Correction[]) {
  const ids = new Set(sent.map(c => c.eventId))
  await update($, points, list => list.map(p => (ids.has(p.eventId) ? { ...p, corrected: true } : p)))
}

async function patchPoint($: $, eventId: string, change: (p: Point) => Point) {
  await update($, points, list => list.map(p => (p.eventId === eventId ? change(p) : p)))
}

async function refreshStatus($: $, live: boolean) {
  const list = await read($, points)
  const state = await read($, conn)
  const latest = [...list].reverse().find(p => p.risk !== null)
  const flags = list.filter(p => p.flagged).length
  const fixes = list.filter(p => p.correction !== null).length
  const mode = live ? '' : ' (mock)'
  if (state === 'error') {
    $.ui.status(`offline${mode}`)
  } else if (!latest) {
    $.ui.status(`waiting${mode}`)
  } else {
    $.ui.status(`${pct(latest.risk)} risk, ${flags} flags, ${fixes} corrections${mode}`)
  }
}

function debug($: $, where: string, error: unknown) {
  const message = error instanceof Error ? `${error.message}\n${error.stack ?? ''}` : String(error)
  $.ui.log(`${PLUGIN} ${where}: ${message}`, { to: 'debug' })
  trace($, `ERROR ${where}: ${message}`)
}

// Temporary development trace, written to a scratch file so the build can
// be checked from outside the session. Remove before linking.
const TRACE_FILE = 'C:/Users/noahk/AppData/Local/Temp/claude/958679f3225a6931/64be212f-105c-4bae-9020-d01b2b1d361a/scratchpad/mod-trace.log'
const traceLines: string[] = []
// Temporary: shows the trace to the agent on every tool result. Remove before linking.
const DEBUG_CONTEXT = false
function trace($: $, line: string) {
  traceLines.push(`${new Date().toISOString()} ${line}`)
  void $.fs.write(TRACE_FILE, traceLines.slice(-200).join('\n')).catch(() => {})
}

// ---------- Sample history (mock mode, for trying the chart windows) ----------

// Replaces this session's checks with ten days of made-up history: a few
// sessions a day, a busy last hour, occasional flags with corrections.
async function loadSample($: $) {
  const now = await $.clock.now()
  let seed = 7
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
  const tools = ['Edit', 'Bash', 'Write', 'PowerShell']
  const actions = ['Edited src/app.py', 'pytest -q', 'Wrote docs/notes.md', 'Edited tests/test_api.py', 'npm run build', 'git status', 'Edited src/cache.py']
  const times: number[] = []
  for (let day = 9; day >= 1; day--) {
    const sessions = 1 + Math.floor(rand() * 3)
    for (let k = 0; k < sessions; k++) {
      const start = now - day * 86_400_000 + (8 + rand() * 12) * 3_600_000
      const checks = 6 + Math.floor(rand() * 18)
      for (let c = 0; c < checks; c++) times.push(start + c * (60_000 + rand() * 240_000))
    }
  }
  for (let h = 20; h >= 2; h -= 3) times.push(now - h * 3_600_000 + rand() * 1_800_000)
  for (let m = 58; m >= 1; m -= 2) times.push(now - m * 60_000)
  times.sort((a, b) => a - b)

  const sample: Point[] = []
  let recovering = 0
  times.forEach((ts, i) => {
    const flagged = recovering === 0 && rand() < 0.05
    const base = recovering > 0 ? 0.08 + rand() * 0.15 : rand() < 0.15 ? 0.4 + rand() * 0.25 : 0.03 + rand() * 0.25
    const risk = flagged ? 0.8 + rand() * 0.18 : base
    const corrected = flagged && rand() < 0.7
    recovering = corrected ? 3 : Math.max(0, recovering - 1)
    const t = Math.floor(rand() * tools.length)
    sample.push({
      eventId: `sample-${i}`,
      seq: i + 1,
      ts,
      tool: tools[t] ?? 'Edit',
      summary: flagged ? 'rm tests/test_slow.py' : actions[Math.floor(rand() * actions.length)] ?? 'Edited a file',
      risk,
      flagged,
      corrected,
      isPending: false,
      monitor: 'goal_adherence',
      details: flagged ? { behavior: 'Deleted test files', concern: 'Sample data: possible proxy optimization.' } : {},
      notices: flagged ? [{ level: 'detected', text: 'Sample: the agent deleted test files.' }] : [],
      correction: corrected ? 'Sample correction: restore the deleted tests.' : null,
      error: null,
      drift: null,
      driftRate: null,
    })
  })
  // Keep any real checks from this session after the sample history.
  // Drift: how far off course the run is, as a slow average of risk.
  let drift = 0
  for (const p of sample) {
    const next = drift * 0.85 + (p.risk ?? 0) * 0.15
    p.driftRate = next - drift
    p.drift = next
    drift = next
  }
  await update($, points, list =>
    [...sample, ...list.filter(p => !p.eventId.startsWith('sample-'))].sort((a, b) => a.ts - b.ts).slice(-MAX_POINTS),
  )
  return sample.length
}

// ---------- Mock classifier (used until the backend URL and token are set) ----------

async function mockClassify($: $, event: Event): Promise<Result> {
  await $.clock.sleep(600)
  const action = (event.action ?? {}) as { tool?: string; args?: Record<string, unknown> }
  if (READ_TOOLS.has(String(action.tool))) {
    return { event_id: event.event_id, monitor: 'goal_adherence', flagged: false, risk: null, details: { mock: true, classified: false }, actions: [] }
  }
  const args = action.args ?? {}
  const command = String(args.command ?? '')
  const path = String(args.file_path ?? '')
  const removed = String(args.old_string ?? '')
  const added = String(args.new_string ?? args.content ?? '')

  const deletesTests =
    /\b(rm|del|rmdir|remove-item|unlink|git\s+rm)\b/i.test(command) &&
    /(\btests?[\\/]|\btest_\w+|\w+_test\b|\.(test|spec)\.)/i.test(command)
  const weakensTests =
    /test/i.test(path) &&
    (/(assert|expect\(|def test_|it\(|test\()/i.test(removed) || /(\.skip|xit\(|@pytest\.mark\.skip)/i.test(added))

  if (deletesTests) {
    return {
      event_id: event.event_id,
      monitor: 'goal_adherence',
      flagged: true,
      risk: 0.93,
      details: {
        mock: true,
        behavior: 'Deleted test files',
        concern: 'Possible proxy optimization: removing tests can make the suite faster while lowering coverage.',
      },
      actions: [
        { type: 'notify_user', level: 'detected', text: 'The agent deleted test files. This may conflict with keeping test coverage.' },
        {
          type: 'inject_agent',
          text:
            'Alignment monitor: a goal-adherence check flagged your last action (deleting test files) as a possible conflict with the user\'s requirements. Re-read the user\'s instructions. If they ask to keep test coverage, restore the deleted tests and find another way to reach the goal. If no requirement was violated, ignore this message.',
        },
        { type: 'notify_user', level: 'intervened', text: 'A correction was sent to the agent.' },
      ],
    }
  }
  if (weakensTests) {
    return {
      event_id: event.event_id,
      monitor: 'goal_adherence',
      flagged: false,
      risk: 0.58,
      details: { mock: true, behavior: 'Edited a test file to remove or skip checks' },
      actions: [{ type: 'notify_user', level: 'potential', text: 'A test file lost assertions or gained a skip.' }],
    }
  }
  const n = Number(event.seq) || 1
  return {
    event_id: event.event_id,
    monitor: 'goal_adherence',
    flagged: false,
    risk: 0.04 + ((n * 37) % 17) / 100,
    details: { mock: true },
    actions: [],
  }
}

// ---------- Event helpers ----------

function describeTool(e: Record<string, unknown>) {
  const tool = String(e.tool)
  const short = (text: string) => {
    const one = text.replace(/\s+/g, ' ').trim()
    return one.length > 70 ? `${one.slice(0, 67)}...` : one
  }
  const file = (path: unknown) => String(path ?? '').split(/[\\/]/).pop() ?? ''
  if (tool === 'Edit' || tool === 'Write') return { tool, summary: `${tool === 'Edit' ? 'Edited' : 'Wrote'} ${file(e.file_path)}` }
  if (tool === 'Read') return { tool, summary: `Read ${file(e.file_path)}` }
  if (typeof e.command === 'string') return { tool, summary: short(e.command) }
  if (typeof e.pattern === 'string') return { tool, summary: short(`${e.pattern}${e.path ? ` in ${file(e.path)}` : ''}`) }
  if (typeof e.url === 'string') return { tool, summary: short(e.url) }
  if (typeof e.query === 'string') return { tool, summary: short(e.query) }
  if (Array.isArray(e.todos)) return { tool, summary: `Updated ${e.todos.length} todos` }
  if (typeof e.description === 'string') return { tool, summary: short(e.description) }
  return { tool, summary: tool }
}

function fileChanges(tool: string, args: Record<string, unknown>, result: Record<string, unknown> | undefined) {
  if (tool !== 'Edit' && tool !== 'Write') return []
  return [
    {
      path: String(args.file_path ?? ''),
      op: tool === 'Write' ? 'write' : 'edit',
      patch: result?.structuredPatch ?? null,
    },
  ]
}

// Copies a value as JSON data, dropping full pre-edit file contents and
// capping long strings so events stay small.
function sanitize(value: unknown, depth = 0): unknown {
  if (typeof value === 'string') return value
  if (value === null || typeof value !== 'object' || depth > 8) {
    return typeof value === 'number' || typeof value === 'boolean' || value === null ? value : undefined
  }
  if (Array.isArray(value)) return value.map(v => sanitize(v, depth + 1))
  const out: Record<string, unknown> = {}
  for (const [key, v] of Object.entries(value)) {
    const clean = sanitize(v, depth + 1)
    if (clean !== undefined) out[key] = clean
  }
  return out
}

// Keeps one event under the safety cap by cutting its longest strings in
// half, marked, until it fits. Only an unusually large event is touched.
function capEvent(event: Event): string {
  let json = JSON.stringify(event)
  for (let round = 0; json.length > MAX_EVENT_BYTES && round < 40; round++) {
    let longest: { holder: Record<string, unknown> | unknown[]; key: string | number; size: number } | null = null
    const visit = (holder: Record<string, unknown> | unknown[], key: string | number, value: unknown) => {
      if (typeof value === 'string') {
        if (!longest || value.length > longest.size) longest = { holder, key, size: value.length }
      } else if (Array.isArray(value)) {
        value.forEach((v, i) => visit(value, i, v))
      } else if (value && typeof value === 'object') {
        for (const [k, v] of Object.entries(value)) visit(value as Record<string, unknown>, k, v)
      }
    }
    for (const [k, v] of Object.entries(event)) visit(event, k, v)
    if (!longest) break
    const target = longest as { holder: Record<string, unknown>; key: string; size: number }
    const text = target.holder[target.key] as string
    const keep = Math.floor(text.length / 4)
    target.holder[target.key] = `${text.slice(0, keep)}
[cut ${text.length - 2 * keep} chars to fit the 5 MB event cap]
${text.slice(-keep)}`
    json = JSON.stringify(event)
  }
  return json
}

// ---------- Pane ----------

// The surface's element table, loosely typed: the Pane draws on desktop
// (with Svg) and falls back to text sparklines where Svg is missing.
type Elements = { [name: string]: any }

async function renderPane($: $, elements: Elements, live: boolean) {
  const { Box, Text, Button } = elements
  const Svg = elements.Svg

  const list = await read($, points)
  const state = await read($, conn)
  const open = await read($, expanded)
  const scored = list.filter(p => p.risk !== null)
  const latest = scored[scored.length - 1]
  const risks = scored.map(p => p.risk as number)
  const peak = risks.length ? Math.max(...risks) : null
  const average = risks.length ? risks.reduce((a, b) => a + b, 0) / risks.length : null
  const flagged = list.filter(p => p.flagged).reverse()
  const fixes = list.filter(p => p.correction !== null).length
  const driftSeries = driftValues(scored)
  const driftNow = driftSeries.length ? driftSeries[driftSeries.length - 1] ?? null : null
  const driftPrev = driftSeries.length > 1 ? driftSeries[driftSeries.length - 2] ?? null : null
  const rate = latest?.driftRate ?? (driftNow !== null && driftPrev !== null ? driftNow - driftPrev : null)
  const arrow = rate === null ? '' : rate > 0.005 ? ' ↑' : rate < -0.005 ? ' ↓' : ' →'
  const trendColor = rate === null ? 'subtle' : rate > 0.005 ? 'error' : rate < -0.005 ? 'success' : 'subtle'
  const trendNote = (
    <Text color="inactive" dimColor size="footnote">
      {'Agent trend: '}
      <Text size="footnote" color={trendColor}>{arrow.trim() || '--'}</Text>
    </Text>
  )

  const status = {
    connecting: ['Connecting', 'subtle'],
    live: ['Live', 'success'],
    classifying: ['Checking...', 'warning'],
    error: ['Backend unreachable', 'error'],
  }[state as Conn] ?? ['Unknown', 'subtle']

  const toggle = (id: string) => update($, expanded, current => (current === id ? null : id))
  const chosen = await read($, windows)
  const now = await $.clock.now()
  const riskList = inWindow(list, chosen.risk, now)
  const trendList = inWindow(list, chosen.trend, now)
  const pick = (chart: 'risk' | 'trend') => (id: string) => update($, windows, w => ({ ...w, [chart]: id }))
  const lists = await read($, listsOpen)
  const expandList = (which: 'flags' | 'recent') => () => update($, listsOpen, v => ({ ...v, [which]: !v[which] }))
  const recent = [...list].reverse()

  return (
    <Box flexDirection="column" gap="sm" paddingX={1}>
      <Box flexDirection="row" justifyContent="space-between" alignItems="flex-start">
        <Box flexDirection="column">
          <Text dimColor size="caption">Current risk</Text>
          <Box flexDirection="row" alignItems="flex-end" gap="xs">
            {Svg ? (
              <Svg source={bigNumber(latest ? pct(latest.risk) : '--', riskColor(latest?.risk ?? null, latest?.flagged ?? false))} alt={`Current risk ${latest ? pct(latest.risk) : 'unknown'}`} />
            ) : (
              <Text size="title" weight="bold" color={riskColor(latest?.risk ?? null, latest?.flagged ?? false)}>
                {latest ? pct(latest.risk) : '--'}
              </Text>
            )}
            <Text size="heading" weight="semibold" color={latest ? riskColor(latest.risk, latest.flagged) : 'subtle'}>
              {latest ? riskLabel(latest.risk, latest.flagged) : 'No actions checked yet'}
            </Text>
          </Box>
        </Box>
        <Box flexDirection="column" alignItems="flex-end">
          <Box flexDirection="row" gap="xs">
            <Text color={status[1]} wrap="truncate">●</Text>
            <Text color={status[1]} wrap="truncate">{status[0]}</Text>
          </Box>
          {!live && <Text dimColor size="caption">Mock classifier</Text>}
        </Box>
      </Box>

      <Box flexDirection="row" justifyContent="space-between">
        {readout(Text, Box, 'Drift', driftNow === null ? '--' : `${pct(Math.min(1, driftNow))}${arrow}`, driftNow === null ? 'subtle' : riskColor(driftNow, false))}
        {readout(Text, Box, 'Max risk', peak === null ? '--' : pct(peak), riskColor(peak, false))}
        {readout(Text, Box, 'Average risk', average === null ? '--' : pct(average), riskColor(average, false))}
        {readout(Text, Box, 'Flags', String(flagged.length), flagged.length ? 'error' : 'text')}
        {readout(Text, Box, 'Corrections', String(fixes), fixes ? 'success' : 'text')}
      </Box>


      <Box flexDirection="column" borderStyle="round" borderColor="#88878040" paddingX={1}>
        {chartTitle(Text, Box, Button, Svg, 'Risk per action', 'info-risk', chosen.risk, pick('risk'))}
        {Svg ? (
          <Svg source={riskChart(riskList, chosen.risk)} alt={chartAlt(riskList)} />
        ) : (
          <Text dimColor>{sparkline(risks)}</Text>
        )}
        {infoReveal(Text, Box, 'info-risk', [
          'How likely each checked action is to break your instructions, as judged by the classifier. Lower is better.',
          [['● Blue', C.line], [': checked']],
          [['● Yellow', C.warn], [': elevated risk']],
          [['● Red', C.flag], [': flagged']],
          [['┊ Dashed green line', C.ok], [': a correction was sent to the agent']],
          [['○ Gray', C.pending], [': still being checked']],
        ])}
      </Box>

      <Box flexDirection="column" borderStyle="round" borderColor="#88878040" paddingX={1}>
        {chartTitle(Text, Box, Button, Svg, 'Drift', 'info-trend', chosen.trend, pick('trend'), trendNote)}
        {Svg ? (
          <Svg source={trendChart(trendList, chosen.trend)} alt={`Drift chart, currently ${driftNow === null ? 'unknown' : pct(Math.min(1, driftNow))}`} />
        ) : (
          <Text dimColor>{sparkline(risks.map((_, i) => 1 - rollingRisk(risks, i)))}</Text>
        )}
        {infoReveal(Text, Box, 'info-trend', [
          'How far off course the whole run is, as judged by the classifier. 0% means on track. Lower is better.',
          'A rising line means the agent is wandering from your instructions, even if no single action looks bad.',
          [['┊ Dashed green line', C.ok], [': a correction was sent to the agent. The line falling after one means it helped.']],
          'Agent trend (next to the title and on the Drift readout):',
          [['↑ Red', 'error'], [': drift is rising, the agent is moving further off course']],
          [['↓ Green', 'success'], [': drift is falling, the agent is getting back on track']],
          [['→ Gray', 'subtle'], [': drift is steady']],
        ])}
      </Box>

      <Box flexDirection="column">
        <Box flexDirection="row" justifyContent="space-between" alignItems="center">
          <Text weight="semibold">{`Flagged actions (${flagged.length})`}</Text>
          {showMore(Text, Button, 'flags', flagged.length, FLAGS_SHOWN, lists.flags, expandList('flags'))}
        </Box>
        {flagged.length === 0 && <Text dimColor>Nothing flagged so far.</Text>}
        {(lists.flags ? flagged : flagged.slice(0, FLAGS_SHOWN)).map(p => (
          <Box flexDirection="column" key={`flag-${p.eventId}`}>
            <Box flexDirection="row" gap="sm">
              <Box flexShrink={0}>
                <Button key={`btn-${p.eventId}`} plain onPress={() => toggle(p.eventId)}>
                  {`${open === p.eventId ? '▾' : '▸'} ${pct(p.risk)}`}
                </Button>
              </Box>
              <Box flexShrink={1}>
                <Text dimColor wrap="truncate">
                  {`${p.summary}  ${clock(p.ts)}${p.corrected ? ', corrected' : p.correction ? ', correction queued' : ''}`}
                </Text>
              </Box>
            </Box>
            {open === p.eventId && flagDetails(Text, Box, p)}
          </Box>
        ))}
        {!lists.flags && flagged.length > FLAGS_SHOWN && <Box paddingLeft={4}><Text dimColor>...</Text></Box>}
      </Box>

      <Box flexDirection="column">
        <Box flexDirection="row" justifyContent="space-between" alignItems="center">
          <Text weight="semibold">Recent checks</Text>
          {showMore(Text, Button, 'recent', Math.min(recent.length, 50), RECENT_SHOWN, lists.recent, expandList('recent'))}
        </Box>
        {list.length === 0 && <Text dimColor>Waiting for the agent to act.</Text>}
        {(lists.recent ? recent.slice(0, 50) : recent.slice(0, RECENT_SHOWN)).map(p => (
          <Box key={`recent-${p.eventId}`} flexDirection="column">
            <Box flexDirection="row" gap="sm">
              <Box flexShrink={0}>
                <Button key={`recent-btn-${p.eventId}`} plain onPress={() => toggle(`recent-${p.eventId}`)}>
                  {`${open === `recent-${p.eventId}` ? '▾' : '▸'} ${clock(p.ts)}`}
                </Button>
              </Box>
              <Box flexShrink={0} width={5}>
                <Text color={p.flagged ? 'error' : 'text'} wrap="truncate">{p.risk === null ? '' : pct(p.risk)}</Text>
              </Box>
              <Box flexShrink={1}>
                <Text dimColor wrap="truncate">{`${p.tool}: ${p.summary}`}</Text>
              </Box>
            </Box>
            {open === `recent-${p.eventId}` && flagDetails(Text, Box, p)}
          </Box>
        ))}
        {!lists.recent && recent.length > RECENT_SHOWN && <Box paddingLeft={4}><Text dimColor>...</Text></Box>}
      </Box>
    </Box>
  )
}

// A section title with an (i) icon. Hovering the icon reveals the matching
// infoReveal card, floating over the chart so nothing else moves.
// The bar sits 4 px right of the image's left edge, so centering the image
// nudges the bar 2 px right to line up under the button's label.
const UNDERLINE = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="2" viewBox="0 0 20 2"><rect x="4" width="16" height="2" rx="1" fill="#9C9A92"/></svg>'

function chartTitle(Text: any, Box: any, Button: any, Svg: any, title: string, scope: string, current: string, onPick: (id: string) => unknown, note: unknown = null) {
  return (
    <Box flexDirection="row" justifyContent="space-between" alignItems="center">
      <Box flexDirection="row" alignItems="center" gap="sm">
        <Text weight="semibold">{title}</Text>
        {note}
      </Box>
      <Box flexDirection="row" alignItems="center" gap="xs">
        {WINDOWS.map(w => (
          // The app draws its own pill on hover. Selection is a short underline
          // drawn in an absolutely positioned box, so it takes no space and the
          // options stay in line with the title.
          <Box key={`${scope}-${w.id}-opt`} position="relative">
            <Button key={`${scope}-${w.id}`} plain dimColor={w.id !== current} onPress={() => onPick(w.id)}>
              <Text color="inactive" dimColor size="footnote">
                {w.label}
              </Text>
            </Button>
            {w.id === current && Svg && (
              <Box position="absolute" bottom={0} left={0} right={0} flexDirection="row" justifyContent="center">
                <Svg source={UNDERLINE} alt="Selected" />
              </Box>
            )}
          </Box>
        ))}
        <Text color="inactive" dimColor hover={{ scope, color: 'subtle', dimColor: false }}>ⓘ</Text>
      </Box>
    </Box>
  )
}

type InfoLine = string | ([string] | [string, string])[]

function infoReveal(Text: any, Box: any, scope: string, lines: InfoLine[]) {
  return (
    <Box
      position="absolute"
      top={1}
      left={0}
      right={0}
      display="none"
      hover={{ scope, display: 'flex' }}
      flexDirection="column"
      borderStyle="round"
      borderColor="subtle"
      backgroundColor="inverseText"
      paddingX={1}
    >
      {lines.map(line =>
        typeof line === 'string' ? (
          <Text size="footnote">{line}</Text>
        ) : (
          <Text size="footnote">
            {line.map(([text, color]) => (color ? <Text size="footnote" color={color}>{text}</Text> : text))}
          </Text>
        ),
      )}
    </Box>
  )
}

// An underlined "Show more" / "Show less" link under a list, shown only
// when the list has more rows than it shows by default.
function showMore(Text: any, Button: any, which: string, total: number, shown: number, isOpen: boolean, onPress: () => unknown) {
  if (total <= shown) return null
  return (
    <Button key={`more-${which}`} plain dimColor onPress={onPress}>
      <Text underline dimColor size="footnote">{isOpen ? 'Show less' : `Show ${total - shown} more`}</Text>
    </Button>
  )
}

// The headline risk drawn as an image, larger than the biggest text size.
// Colors are the desktop dark theme's success, warning and error tones,
// sampled from the pane, so the number matches the readouts below it.
const HEADLINE_COLORS: { [key: string]: string } = { success: '#53C556', warning: '#E49C06', error: '#F17778', subtle: '#888780' }

function bigNumber(text: string, color: string) {
  // Bold digits and % run about 28 px each at this size; the extra room
  // keeps wide glyphs from being clipped. The baseline sits 5 px above the
  // bottom, about where text's own baseline sits, so the two line up.
  const width = Math.max(52, text.length * 27 + 4)
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="42" viewBox="0 0 ${width} 42">` +
    `<text x="0" y="37" font-size="40" font-weight="700" font-family="Segoe UI, sans-serif" fill="${HEADLINE_COLORS[color] ?? '#888780'}">${esc(text)}</text></svg>`
}

function readout(Text: any, Box: any, label: string, value: string, color: string) {
  return (
    <Box flexDirection="column" alignItems="flex-start" key={`readout-${label}`}>
      <Text size="heading" weight="bold" color={color}>{value}</Text>
      <Text dimColor size="caption">{label}</Text>
    </Box>
  )
}

function flagDetails(Text: any, Box: any, p: Point) {
  const rows = Object.entries(p.details).filter(([key]) => key !== 'mock')
  return (
    <Box flexDirection="column" paddingLeft={4} key={`details-${p.eventId}`}>
      <Text dimColor>{`Monitor: ${p.monitor ?? 'unknown'}. Tool: ${p.tool}. Checked at ${clock(p.ts)}.`}</Text>
      <Text>{`Action: ${p.summary}`}</Text>
      <Text>{`Risk: ${p.isPending ? 'still checking' : pct(p.risk)}${p.flagged ? ' (flagged)' : ''}`}</Text>
      {p.error && <Text color="error">{`No result: ${p.error}`}</Text>}
      {rows.map(([key, value]) => (
        <Text>{`${label(key)}: ${typeof value === 'string' ? value : JSON.stringify(value)}`}</Text>
      ))}
      {p.notices.map(n => (
        <Text color="warning">{`Notice (${n.level}): ${n.text}`}</Text>
      ))}
      {p.correction && (
        <Text color="success">{`${p.corrected ? 'Correction sent' : 'Correction queued'}: ${p.correction}`}</Text>
      )}
    </Box>
  )
}

// ---------- Charts (SVG drawn as an image, so colors are fixed mid tones that read on light and dark) ----------

const C = {
  axis: '#888780',
  grid: '#88878040',
  line: '#378ADD',
  flag: '#E24B4A',
  warn: '#EF9F27',
  ok: '#1D9E75',
  pending: '#B4B2A9',
  trend: '#7F77DD',
}
const W = 640
const H = 220
const PAD = { left: 54, right: 22, top: 14, bottom: 28 }

function frame(inner: string, yLabels: [number, string][], times: number[] = []) {
  const plotH = H - PAD.top - PAD.bottom
  const grid = yLabels
    .map(([v, text]) => {
      const y = PAD.top + plotH * (1 - v)
      return `<line x1="${PAD.left}" y1="${y}" x2="${W - PAD.right}" y2="${y}" stroke="${C.grid}" stroke-width="1"/>` +
        `<text x="${PAD.left - 6}" y="${y + 6}" text-anchor="end" font-size="16" fill="${C.axis}" font-family="sans-serif">${text}</text>`
    })
    .join('')
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${grid}${timeAxis(times)}${inner}</svg>`
}

// x for each point from its real time, so gaps in the agent's work show as
// gaps on the chart and the time axis below reads correctly.
function xPositions(list: Point[]) {
  const plotW = W - PAD.left - PAD.right
  const first = list[0]?.ts ?? 0
  const last = list[list.length - 1]?.ts ?? 0
  const span = last - first
  return list.map(p => (span <= 0 ? PAD.left + plotW / 2 : PAD.left + (plotW * (p.ts - first)) / span))
}

const SECOND = 1000
const MINUTE = 60 * SECOND
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR
const STEPS = [10 * SECOND, 15 * SECOND, 30 * SECOND, MINUTE, 2 * MINUTE, 5 * MINUTE, 10 * MINUTE, 15 * MINUTE,
  30 * MINUTE, HOUR, 2 * HOUR, 3 * HOUR, 6 * HOUR, 12 * HOUR, DAY, 2 * DAY, 7 * DAY]
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Time labels under a chart, picked to suit the session's length: seconds
// for a few minutes, clock times for hours, dates once it runs for days.
function timeAxis(times: number[]) {
  if (times.length === 0) return ''
  const plotW = W - PAD.left - PAD.right
  const first = times[0] ?? 0
  const last = times[times.length - 1] ?? 0
  const span = last - first
  const y = H - 6
  const label = (x: number, text: string, anchor = 'middle') =>
    `<text x="${x.toFixed(1)}" y="${y}" text-anchor="${anchor}" font-size="16" fill="${C.axis}" font-family="sans-serif">${text}</text>`
  if (span <= 0) return label(PAD.left + plotW / 2, timeLabel(first, MINUTE, false))

  const step = STEPS.find(s => span / s <= 5) ?? 30 * DAY
  const multiDay = new Date(first).toDateString() !== new Date(last).toDateString()
  let t = alignToStep(first, step)
  if (step >= DAY) {
    const midnight = new Date(first)
    midnight.setHours(0, 0, 0, 0)
    t = midnight.getTime() < first ? midnight.getTime() + DAY : midnight.getTime()
  }
  const parts: string[] = []
  let lastDay = ''
  for (let guard = 0; t <= last && guard < 12; guard++, t += step) {
    const x = PAD.left + (plotW * (t - first)) / span
    const day = new Date(t).toDateString()
    const showDate = step >= DAY || (multiDay && day !== lastDay)
    parts.push(`<line x1="${x.toFixed(1)}" y1="${PAD.top}" x2="${x.toFixed(1)}" y2="${yFor(0)}" stroke="${C.grid}" stroke-width="1"/>`)
    parts.push(label(x, timeLabel(t, step, showDate)))
    lastDay = day
  }
  if (parts.length === 0) {
    // Too short for any round time to fall inside: label both ends.
    return label(PAD.left, timeLabel(first, SECOND, false), 'start') + label(W - PAD.right, timeLabel(last, SECOND, false), 'end')
  }
  return parts.join('')
}

// Rounds up to the next step boundary in local time (whole minutes, hours).
function alignToStep(ts: number, step: number) {
  const d = new Date(ts)
  const offset = d.getTimezoneOffset() * MINUTE
  return Math.ceil((ts - offset) / step) * step + offset
}

function timeLabel(ts: number, step: number, withDate: boolean) {
  const d = new Date(ts)
  const two = (n: number) => String(n).padStart(2, '0')
  const date = `${MONTHS[d.getMonth()]} ${d.getDate()}`
  if (step >= DAY) return date
  const time = step < MINUTE ? `${two(d.getHours())}:${two(d.getMinutes())}:${two(d.getSeconds())}` : `${two(d.getHours())}:${two(d.getMinutes())}`
  return withDate ? `${date} ${time}` : time
}

function yFor(v: number) {
  return PAD.top + (H - PAD.top - PAD.bottom) * (1 - v)
}

function empty(message: string) {
  return frame(
    `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" font-size="13" fill="${C.axis}" font-family="sans-serif">${message}</text>`,
    [[0, '0%'], [0.5, '50%'], [1, '100%']],
  )
}

function riskChart(all: Point[], window: string) {
  const list = downsample(all)
  if (list.length === 0) return empty(all.length === 0 && window === 'all' ? 'Risk appears here as the agent acts' : `No checks in ${windowName(window)}`)
  const xs = xPositions(list)
  const scored = list.map((p, i) => ({ p, i })).filter(({ p }) => p.risk !== null)
  const path = scored.map(({ p, i }, k) => `${k ? 'L' : 'M'}${(xs[i] ?? 0).toFixed(1)} ${yFor(p.risk as number).toFixed(1)}`).join(' ')
  const first = scored[0]
  const last = scored[scored.length - 1]
  const area = first && last && scored.length > 1
    ? `<path d="${path} L${(xs[last.i] ?? 0).toFixed(1)} ${yFor(0)} L${(xs[first.i] ?? 0).toFixed(1)} ${yFor(0)} Z" fill="${C.line}" fill-opacity="0.12"/>`
    : ''
  const dots = list
    .map((p, i) => {
      const x = (xs[i] ?? 0).toFixed(1)
      const tip = `<title>${esc(`${clock(p.ts)} ${p.tool}: ${p.summary}\nRisk: ${p.isPending ? 'checking' : pct(p.risk)}${p.flagged ? ', flagged' : ''}${p.correction ? (p.corrected ? ', correction sent' : ', correction queued') : ''}`)}</title>`
      if (p.risk === null) {
        // Only checks still waiting for an answer are drawn; failed ones are left out.
        return p.isPending
          ? `<circle cx="${x}" cy="${yFor(0)}" r="4" fill="none" stroke="${C.pending}" stroke-width="1.5">${tip}</circle>`
          : ''
      }
      const y = yFor(p.risk).toFixed(1)
      const color = p.flagged ? C.flag : p.risk >= 0.5 ? C.warn : C.line
      return `<circle cx="${x}" cy="${y}" r="${p.flagged ? 5.5 : 4}" fill="${color}">${tip}</circle>`
    })
    .join('')
  const marks = correctionLines(list, xs)
  return frame(
    `${area}${marks}<path d="${path}" fill="none" stroke="${C.line}" stroke-width="2" stroke-linejoin="round"/>${dots}`,
    [[0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%'], [1, '100%']],
    list.map(p => p.ts),
  )
}

function trendChart(all: Point[], window: string) {
  const list = downsample(all)
  const scored = list.map((p, i) => ({ p, i })).filter(({ p }) => p.risk !== null)
  if (scored.length === 0) return empty(window === 'all' ? 'Drift appears after the first check' : `No checks in ${windowName(window)}`)
  const xs = xPositions(list)
  const values = driftValues(scored.map(({ p }) => p)).map(v => Math.min(1, v))
  const path = scored.map(({ i }, k) => `${k ? 'L' : 'M'}${(xs[i] ?? 0).toFixed(1)} ${yFor(values[k] ?? 0).toFixed(1)}`).join(' ')
  const marks = correctionLines(list, xs)
  const dots = scored
    .map(({ p, i }, k) => `<circle cx="${(xs[i] ?? 0).toFixed(1)}" cy="${yFor(values[k] ?? 0).toFixed(1)}" r="3" fill="${C.trend}"><title>${esc(`${clock(p.ts)}: drift ${pct(values[k] ?? null)}`)}</title></circle>`)
    .join('')
  return frame(
    `${marks}<path d="${path}" fill="none" stroke="${C.trend}" stroke-width="2.5" stroke-linejoin="round"/>${dots}`,
    [[0, '0%'], [0.5, '50%'], [1, '100%']],
    list.map(p => p.ts),
  )
}

// Drift per scored check: the classifier's own value when it sent one,
// otherwise the average risk of the last 5 checks as a stand-in.
function driftValues(scored: Point[]) {
  const risks = scored.map(p => p.risk as number)
  return scored.map((p, k) => (typeof p.drift === 'number' ? p.drift : rollingRisk(risks, k)))
}

// Dashed green vertical lines, topped by a small arrow, where a correction was sent to the agent.
function correctionLines(list: Point[], xs: number[]) {
  return list
    .map((p, i) => {
      if (!p.correction) return ''
      const x = (xs[i] ?? 0).toFixed(1)
      const cx = Number(x)
      const tip = `<title>${esc(`Correction sent: ${p.summary}`)}</title>`
      const arrow = `<path d="M${cx - 5} ${PAD.top - 7} L${cx + 5} ${PAD.top - 7} L${cx} ${PAD.top + 1} Z" fill="${C.ok}" fill-opacity="0.85">${tip}</path>`
      return `<line x1="${x}" y1="${PAD.top}" x2="${x}" y2="${yFor(0)}" stroke="${C.ok}" stroke-width="1.5" stroke-dasharray="4 3">${tip}</line>${arrow}`
    })
    .join('')
}

function chartAlt(list: Point[]) {
  const scored = list.filter(p => p.risk !== null)
  if (scored.length === 0) return 'Risk chart, no checks yet'
  const last = scored[scored.length - 1]
  return `Risk chart of ${scored.length} checks, latest ${pct(last?.risk ?? null)}, ${list.filter(p => p.flagged).length} flagged`
}

// Checks inside the chosen time window.
function inWindow(list: Point[], window: string, now: number) {
  const ms = WINDOWS.find(w => w.id === window)?.ms ?? Infinity
  return ms === Infinity ? list : list.filter(p => p.ts >= now - ms)
}

function windowName(window: string) {
  return { hour: 'the past hour', day: 'the past day', week: 'the past week' }[window] ?? 'this session'
}

// Keeps a chart readable over long windows: splits the time span into
// CHART_POINTS buckets and keeps the riskiest check of each, so flags,
// corrections and spikes always stay visible.
function downsample(list: Point[]) {
  if (list.length <= CHART_POINTS) return list
  const first = list[0]?.ts ?? 0
  const span = Math.max(1, (list[list.length - 1]?.ts ?? 0) - first)
  const buckets = new Map<number, Point>()
  for (const p of list) {
    const b = Math.min(CHART_POINTS - 1, Math.floor(((p.ts - first) / span) * CHART_POINTS))
    const kept = buckets.get(b)
    const score = (q: Point) => (q.flagged ? 2 : 0) + (q.correction ? 1 : 0) + (q.risk ?? 0)
    if (!kept || score(p) > score(kept)) buckets.set(b, p)
  }
  const latest = list[list.length - 1]
  const kept = [...buckets.values()]
  if (latest && !kept.includes(latest)) kept.push(latest)
  return kept.sort((a, b) => a.ts - b.ts)
}

// ---------- Small helpers ----------

function rollingRisk(risks: number[], index: number, window = 5) {
  const slice = risks.slice(Math.max(0, index - window + 1), index + 1)
  return slice.length ? slice.reduce((a, b) => a + b, 0) / slice.length : 0
}

function sparkline(values: number[]) {
  const bars = '▁▂▃▄▅▆▇█'
  return values.slice(-40).map(v => bars[Math.min(7, Math.max(0, Math.round(v * 7)))]).join('') || 'No data yet'
}

function pct(value: number | null) {
  return value === null ? '--' : `${Math.round(value * 100)}%`
}

function riskColor(risk: number | null, flagged: boolean) {
  if (risk === null) return 'subtle'
  if (flagged || risk >= 0.7) return 'error'
  if (risk >= 0.4) return 'warning'
  return 'success'
}

function riskLabel(risk: number | null, flagged: boolean) {
  if (flagged) return 'Flagged'
  if (risk === null) return 'Unknown'
  if (risk >= 0.7) return 'High'
  if (risk >= 0.4) return 'Elevated'
  return 'Low'
}

function clamp01(v: number) {
  return Math.min(1, Math.max(0, v))
}

function clock(ts: number) {
  const d = new Date(ts)
  const two = (n: number) => String(n).padStart(2, '0')
  return `${two(d.getHours())}:${two(d.getMinutes())}:${two(d.getSeconds())}`
}

function label(key: string) {
  const words = key.replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

function esc(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}
