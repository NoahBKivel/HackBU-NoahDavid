import test from 'node:test';
import assert from 'node:assert/strict';
import { mergeSessionSnapshot } from './live-data.js';
const session = (id, risk = null) => ({ id, name: 'project', task: 'Task', points: [{ eventId: 'event-1', risk }], lastSeenAt: 1 });
test('incremental updates replace pending history without duplicating agents or dropping other sessions', () => {
  const merged = mergeSessionSnapshot([session('a'), session('b')], { cursor: 'run:2', reset: false, sessions: [session('a', .8)] });
  assert.equal(merged.length, 2);
  assert.equal(merged.find(s => s.id === 'a').points[0].risk, .8);
  assert.equal(merged.find(s => s.id === 'b').points[0].risk, null);
});
test('backend restart/full snapshot replaces old sessions, including an empty store', () => {
  assert.deepEqual(mergeSessionSnapshot([session('a')], { cursor: 'new:0', reset: true, sessions: [] }), []);
});
test('invalid snapshots cannot be mistaken for a successful empty connection', () => {
  assert.throws(() => mergeSessionSnapshot([session('a')], { sessions: [] }));
  assert.throws(() => mergeSessionSnapshot([], { cursor: 'x', reset: true, sessions: [{}] }));
});
