import assert from 'node:assert/strict';
import test from 'node:test';
import { calculateRisk } from './risk-model.mjs';

test('each combination of protective actions has the expected score', () => {
  const scenarios = [
    [[], 63],
    [['mfa'], 33],
    [['password'], 40],
    [['contact'], 53],
    [['mfa', 'password'], 10],
    [['mfa', 'contact'], 23],
    [['password', 'contact'], 30],
    [['mfa', 'password', 'contact'], 0]
  ];

  for (const [resolved, expected] of scenarios) {
    assert.equal(calculateRisk(new Set(resolved)).total, expected, resolved.join(', '));
  }
});

test('the score breakdown stays consistent when an action is undone', () => {
  const resolved = new Set(['password']);
  assert.deepEqual(calculateRisk(resolved).activePoints, { mfa: 30, password: 0, contact: 10 });
  resolved.delete('password');
  assert.deepEqual(calculateRisk(resolved).activePoints, { mfa: 30, password: 23, contact: 10 });
});
