import assert from 'node:assert/strict';
import test from 'node:test';
import { calculateRisk, formatRiskReport, prioritizeActions } from './risk-model.mjs';

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

test('priorities rank unresolved actions by score impact', () => {
  const { activePoints } = calculateRisk(new Set(['mfa']));
  assert.deepEqual(prioritizeActions(activePoints), [
    { action: 'Set a unique forum password', points: 23 },
    { action: 'Remove public contact details', points: 10 }
  ]);
  assert.deepEqual(prioritizeActions(calculateRisk(new Set(['mfa', 'password', 'contact'])).activePoints), []);
});

test('reports reflect completed actions and sorted remaining priorities', () => {
  const report = formatRiskReport(new Set(['mfa']));
  assert.match(report, /Baseline score: 63\/100\nCurrent score: 33\/100\nPoints reduced: 30/);
  assert.match(report, /Completed actions\n- Enable email MFA/);
  assert.match(report, /Remaining actions by score impact\n- Set a unique forum password \(23 points\)\n- Remove public contact details \(10 points\)/);
  assert.match(formatRiskReport(new Set()), /Completed actions\nNone/);
  assert.match(formatRiskReport(new Set(['mfa', 'password', 'contact'])), /Remaining actions by score impact\nNone/);
});
