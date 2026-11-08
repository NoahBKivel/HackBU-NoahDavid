import test from 'node:test';
import assert from 'node:assert/strict';
import { fleetAssessment, sessionHealth } from './model.js';

test('ordinary flags do not imply a request for user intervention', () => {
  assert.equal(sessionHealth({ points: [{ seq: 1, risk: .95, flagged: true, requires_user_intervention: false }] }), 'healthy');
});

test('missing and malformed signals remain unreported', () => {
  for (const points of [[], [{ risk: .1 }], [{ requires_user_intervention: 'false' }]]) {
    assert.equal(sessionHealth({ points }), 'unknown');
  }
});

test('pending, unscored and low-risk events without a state do not clear a stop request', () => {
  assert.equal(sessionHealth({ points: [
    { seq: 1, requires_user_intervention: true },
    { seq: 2, risk: .1 },
    { seq: 3, isPending: true, requires_user_intervention: false },
    { seq: 4, risk: null },
  ] }), 'attention');
});

test('an explicit later snapshot clears the state, including an unscored instruction result', () => {
  assert.equal(sessionHealth({ points: [
    { seq: 1, requires_user_intervention: true },
    { seq: 2, risk: null, requires_user_intervention: false },
  ] }), 'healthy');
});

test('late older results cannot override a newer state', () => {
  assert.equal(sessionHealth({ points: [
    { seq: 5, requires_user_intervention: false },
    { seq: 2, requires_user_intervention: true },
  ] }), 'healthy');
});

test('fleet counts include unreported sessions without labeling them healthy', () => {
  assert.deepEqual(fleetAssessment([
    { points: [{ requires_user_intervention: false }] },
    { points: [{ requires_user_intervention: true }] },
    { points: [] },
  ]), { active: 3, healthy: 1, attention: 1, unknown: 1 });
  assert.deepEqual(fleetAssessment([]), { active: 0, healthy: 0, attention: 0, unknown: 0 });
});
