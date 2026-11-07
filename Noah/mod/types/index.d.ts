export type Conn = 'connecting' | 'live' | 'classifying' | 'error'

export type Notice = { level: string; text: string }

export type Point = {
  eventId: string
  seq: number
  ts: number
  tool: string
  summary: string
  risk: number | null
  flagged: boolean
  corrected: boolean
  isPending: boolean
  monitor: string | null
  details: { [key: string]: unknown }
  notices: Notice[]
  correction: string | null
  error: string | null
}

export type Item = { [key: string]: unknown }

export type Correction = { eventId: string; text: string }

export type Todo = { content: string; status: string }

export type SessionInfo = { id: string; startedAt: number }

declare module 'claude-code' {
  interface PluginState {
    'alignment-monitor': {
      points: Shaped<Point[]>
      conn: Conn
      corrections: Correction[]
      pending: Item[]
      seq: number
      instructionCount: number
      expanded: string | null
      todos: Todo[]
      session: SessionInfo | null
    }
  }
}
