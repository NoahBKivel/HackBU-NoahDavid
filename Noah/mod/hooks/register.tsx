import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Conn, Correction, Item, Notice, Point, Todo } from '../types'

const PLUGIN = 'alignment-monitor'
const WATCHED_TOOLS = new Set(['Edit', 'Write', 'Bash', 'PowerShell'])
const MAX_EVENT_BYTES = 5_000_000
const FETCH_TIMEOUT_MS = 60_000
const MAX_POINTS = 300
const CHART_POINTS = 60

type $ = EngineInterface
type Action = { type?: string; level?: string; text?: string }
type Result = {
  event_id?: string
  monitor?: string
  flagged?: boolean
  risk?: number
  details?: { [key: string]: unknown }
  actions?: Action[]
}
type Event = { [key: string]: unknown } & { event_id: string; type: string }

// Change a shape tag whenever that value's fields change, so a reload
// drops what an older version stored instead of drawing it wrong.
const points = atom({ plugin: 'alignment-monitor', key: 'points' } as const, [], { shape: 'points-1' })
const conn = atom({ plugin: 'alignment-monitor', key: 'conn' } as const, 'connecting')
const corrections = atom({ plugin: 'alignment-monitor', key: 'corrections' } as const, [])
const pending = atom({ plugin: 'alignment-monitor', key: 'pending' } as const, [])
const seq = atom({ plugin: 'alignment-monitor', key: 'seq' } as const, 0)
const instructionCount = atom({ plugin: 'alignment-monitor', key: 'instructionCount' } as const, 0)
const expanded = atom({ plugin: 'alignment-monitor', key: 'expanded' } as const, null)
const todos = atom({ plugin: 'alignment-monitor', key: 'todos' } as const, [])
const session = atom({ plugin: 'alignment-monitor', key: 'session' } as const, null)

// The latest model step's visible text and displayed thinking. Kept in the
// module, not $.state, because it is rewritten on every step.
let lastStep = { text: '', thinking: '' }

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
        description: 'Open the alignment monitor pane',
      })
      const id = await $.session.id()
      const known = await read($, session)
      if (known?.id !== id) {
        await startSession($, id)
      }
      void $.ui.open({ id: 'alignment', title: 'Alignment' })
      await refreshStatus($, isLive)
    } catch (error) {
      debug($, 'session.start', error)
    }
    return result
  })

  on('command.run', { command: 'alignment' }, async $ => {
    await $.ui.open({ id: 'alignment', title: 'Alignment', focus: true })
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
      lastStep = { text, thinking }
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

      if (WATCHED_TOOLS.has(e.tool)) {
        const event = await toolEvent($, e as unknown as Record<string, unknown>, ran as unknown as Record<string, unknown>)
        void dispatch($, event, describeTool(e as unknown as Record<string, unknown>), isLive)
      }
      if (DEBUG_CONTEXT && answer.deny === undefined) {
        const note = `[alignment-monitor debug] ${traceLines.slice(-10).join(' | ')}`
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
    agent_text: lastStep.text,
    agent_thinking: lastStep.thinking,
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
    trace($, `dispatch applied ${event.event_id}`)
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
    $.ui.status(`Alignment: offline${mode}`)
  } else if (!latest) {
    $.ui.status(`Alignment: waiting${mode}`)
  } else {
    $.ui.status(`Alignment: ${pct(latest.risk)} risk, ${flags} flags, ${fixes} corrections${mode}`)
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

// ---------- Mock classifier (used until the backend URL and token are set) ----------

async function mockClassify($: $, event: Event): Promise<Result> {
  await $.clock.sleep(600)
  const action = (event.action ?? {}) as { tool?: string; args?: Record<string, unknown> }
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
  if (tool === 'Edit' || tool === 'Write') {
    const path = String(e.file_path ?? '')
    return { tool, summary: `${tool === 'Edit' ? 'Edited' : 'Wrote'} ${path.split(/[\\/]/).pop() ?? path}` }
  }
  const command = String(e.command ?? '').replace(/\s+/g, ' ').trim()
  return { tool, summary: command.length > 70 ? `${command.slice(0, 67)}...` : command }
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
  const alignment = latest ? 1 - rollingRisk(risks, risks.length - 1) : null

  const status = {
    connecting: ['Connecting', 'subtle'],
    live: ['Live', 'success'],
    classifying: ['Checking...', 'warning'],
    error: ['Backend unreachable', 'error'],
  }[state as Conn] ?? ['Unknown', 'subtle']

  const toggle = (id: string) => update($, expanded, current => (current === id ? null : id))

  return (
    <Box flexDirection="column" gap="md" paddingX={1}>
      <Box flexDirection="row" justifyContent="space-between" alignItems="flex-start">
        <Box flexDirection="column">
          <Text dimColor size="caption">Current risk</Text>
          <Text size="title" weight="bold" color={riskColor(latest?.risk ?? null, latest?.flagged ?? false)}>
            {latest ? pct(latest.risk) : '--'}
          </Text>
          <Text dimColor size="footnote">
            {latest ? `${riskLabel(latest.risk, latest.flagged)}, last check: ${latest.summary}` : 'No actions checked yet'}
          </Text>
        </Box>
        <Box flexDirection="column" alignItems="flex-end">
          <Text color={status[1]}>{`● ${status[0]}`}</Text>
          {!live && <Text dimColor size="caption">Mock classifier</Text>}
        </Box>
      </Box>

      <Box flexDirection="row" justifyContent="space-between">
        {readout(Text, Box, 'Alignment', alignment === null ? '--' : pct(alignment), alignment === null ? 'subtle' : riskColor(1 - alignment, false))}
        {readout(Text, Box, 'Peak risk', peak === null ? '--' : pct(peak), riskColor(peak, false))}
        {readout(Text, Box, 'Average risk', average === null ? '--' : pct(average), riskColor(average, false))}
        {readout(Text, Box, 'Flags', String(flagged.length), flagged.length ? 'error' : 'text')}
        {readout(Text, Box, 'Corrections', String(fixes), fixes ? 'success' : 'text')}
      </Box>

      <Box flexDirection="column">
        <Text weight="semibold">Risk per action</Text>
        {Svg ? (
          <Svg source={riskChart(list)} alt={chartAlt(list)} isInteractive />
        ) : (
          <Text dimColor>{sparkline(risks)}</Text>
        )}
        <Text dimColor size="caption">Red: flagged. Green ring: correction sent to the agent. Gray: still being checked.</Text>
      </Box>

      <Box flexDirection="column">
        <Text weight="semibold">Alignment trend</Text>
        {Svg ? (
          <Svg source={trendChart(list)} alt={`Alignment trend, currently ${alignment === null ? 'unknown' : pct(alignment)}`} isInteractive />
        ) : (
          <Text dimColor>{sparkline(risks.map((_, i) => 1 - rollingRisk(risks, i)))}</Text>
        )}
        <Text dimColor size="caption">Rolling alignment over the last 5 checks. Dashed lines mark corrections.</Text>
      </Box>

      <Box flexDirection="column">
        <Text weight="semibold">{`Flagged actions (${flagged.length})`}</Text>
        {flagged.length === 0 && <Text dimColor>Nothing flagged so far.</Text>}
        {flagged.map(p => (
          <Box flexDirection="column" key={`flag-${p.eventId}`}>
            <Button key={`btn-${p.eventId}`} plain onPress={() => toggle(p.eventId)}>
              {`${open === p.eventId ? '▾' : '▸'} ${pct(p.risk)}  ${p.summary} `}
              <Text dimColor>{`${clock(p.ts)}${p.corrected ? ', corrected' : p.correction ? ', correction queued' : ''}`}</Text>
            </Button>
            {open === p.eventId && flagDetails(Text, Box, p)}
          </Box>
        ))}
      </Box>

      <Box flexDirection="column">
        <Text weight="semibold">Recent checks</Text>
        {list.length === 0 && <Text dimColor>Waiting for the agent to act.</Text>}
        {[...list].reverse().slice(0, 8).map(p => (
          <Text dimColor={!p.flagged} color={p.flagged ? 'error' : 'text'}>
            {`${clock(p.ts)}  ${p.isPending ? '...' : p.error ? 'err' : pct(p.risk)}  ${p.tool}: ${p.summary}`}
          </Text>
        ))}
      </Box>
    </Box>
  )
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
    <Box flexDirection="column" paddingLeft={2} key={`details-${p.eventId}`}>
      <Text dimColor>{`Monitor: ${p.monitor ?? 'unknown'}. Tool: ${p.tool}. Checked at ${clock(p.ts)}.`}</Text>
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
}
const W = 640
const H = 190
const PAD = { left: 40, right: 14, top: 12, bottom: 24 }

function frame(inner: string, yLabels: [number, string][]) {
  const plotH = H - PAD.top - PAD.bottom
  const grid = yLabels
    .map(([v, text]) => {
      const y = PAD.top + plotH * (1 - v)
      return `<line x1="${PAD.left}" y1="${y}" x2="${W - PAD.right}" y2="${y}" stroke="${C.grid}" stroke-width="1"/>` +
        `<text x="${PAD.left - 6}" y="${y + 4}" text-anchor="end" font-size="11" fill="${C.axis}" font-family="sans-serif">${text}</text>`
    })
    .join('')
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${grid}${inner}</svg>`
}

function xFor(i: number, count: number) {
  const plotW = W - PAD.left - PAD.right
  return count <= 1 ? PAD.left + plotW / 2 : PAD.left + (plotW * i) / (count - 1)
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

function riskChart(all: Point[]) {
  const list = all.slice(-CHART_POINTS)
  if (list.length === 0) return empty('Risk appears here as the agent acts')
  const n = list.length
  const scored = list.map((p, i) => ({ p, i })).filter(({ p }) => p.risk !== null)
  const path = scored.map(({ p, i }, k) => `${k ? 'L' : 'M'}${xFor(i, n).toFixed(1)} ${yFor(p.risk as number).toFixed(1)}`).join(' ')
  const first = scored[0]
  const last = scored[scored.length - 1]
  const area = first && last && scored.length > 1
    ? `<path d="${path} L${xFor(last.i, n).toFixed(1)} ${yFor(0)} L${xFor(first.i, n).toFixed(1)} ${yFor(0)} Z" fill="${C.line}" fill-opacity="0.12"/>`
    : ''
  const dots = list
    .map((p, i) => {
      const x = xFor(i, n).toFixed(1)
      const tip = `<title>${esc(`${clock(p.ts)} ${p.tool}: ${p.summary}\nRisk: ${p.isPending ? 'checking' : pct(p.risk)}${p.flagged ? ', flagged' : ''}${p.correction ? (p.corrected ? ', correction sent' : ', correction queued') : ''}`)}</title>`
      if (p.risk === null) {
        return `<circle cx="${x}" cy="${yFor(0)}" r="4" fill="none" stroke="${C.pending}" stroke-width="1.5">${tip}</circle>`
      }
      const y = yFor(p.risk).toFixed(1)
      const color = p.flagged ? C.flag : p.risk >= 0.5 ? C.warn : C.line
      const ring = p.correction
        ? `<circle cx="${x}" cy="${y}" r="9" fill="none" stroke="${C.ok}" stroke-width="2"/>`
        : ''
      return `${ring}<circle cx="${x}" cy="${y}" r="${p.flagged ? 5.5 : 4}" fill="${color}">${tip}</circle>`
    })
    .join('')
  return frame(
    `${area}<path d="${path}" fill="none" stroke="${C.line}" stroke-width="2" stroke-linejoin="round"/>${dots}`,
    [[0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%'], [1, '100%']],
  )
}

function trendChart(all: Point[]) {
  const list = all.slice(-CHART_POINTS)
  const scored = list.map((p, i) => ({ p, i })).filter(({ p }) => p.risk !== null)
  if (scored.length === 0) return empty('Alignment trend appears after the first check')
  const n = list.length
  const risks = scored.map(({ p }) => p.risk as number)
  const values = risks.map((_, k) => 1 - rollingRisk(risks, k))
  const path = scored.map(({ i }, k) => `${k ? 'L' : 'M'}${xFor(i, n).toFixed(1)} ${yFor(values[k] ?? 0).toFixed(1)}`).join(' ')
  const marks = list
    .map((p, i) => {
      if (!p.correction) return ''
      const x = xFor(i, n).toFixed(1)
      return `<line x1="${x}" y1="${PAD.top}" x2="${x}" y2="${yFor(0)}" stroke="${C.ok}" stroke-width="1.5" stroke-dasharray="4 3"><title>${esc(`Correction: ${p.summary}`)}</title></line>`
    })
    .join('')
  const dots = scored
    .map(({ p, i }, k) => `<circle cx="${xFor(i, n).toFixed(1)}" cy="${yFor(values[k] ?? 0).toFixed(1)}" r="3" fill="${C.ok}"><title>${esc(`${clock(p.ts)}: alignment ${pct(values[k] ?? null)}`)}</title></circle>`)
    .join('')
  return frame(
    `${marks}<path d="${path}" fill="none" stroke="${C.ok}" stroke-width="2.5" stroke-linejoin="round"/>${dots}`,
    [[0, '0%'], [0.5, '50%'], [1, '100%']],
  )
}

function chartAlt(list: Point[]) {
  const scored = list.filter(p => p.risk !== null)
  if (scored.length === 0) return 'Risk chart, no checks yet'
  const last = scored[scored.length - 1]
  return `Risk chart of ${scored.length} checks, latest ${pct(last?.risk ?? null)}, ${list.filter(p => p.flagged).length} flagged`
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
