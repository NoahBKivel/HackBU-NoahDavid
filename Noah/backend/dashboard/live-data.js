// Backend cursor updates replace whole session snapshots, including late edits.
export function mergeSessionSnapshot(current, batch) {
  if (typeof batch?.cursor !== 'string' || typeof batch.reset !== 'boolean' || !Array.isArray(batch.sessions)) {
    throw new Error('Invalid dashboard response');
  }
  const merged = new Map(batch.reset ? [] : current.map(session => [session.id, session]));
  for (const session of batch.sessions) {
    if (typeof session?.id !== 'string' || typeof session.name !== 'string' || typeof session.task !== 'string' || !Array.isArray(session.points)) {
      throw new Error('Invalid agent session');
    }
    merged.set(session.id, session);
  }
  return [...merged.values()].sort((a, b) => (b.lastSeenAt ?? 0) - (a.lastSeenAt ?? 0) || a.id.localeCompare(b.id));
}
