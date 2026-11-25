import assert from 'node:assert/strict';
import test from 'node:test';
import { buildActionPlan, describeAction, formatActionPlan } from './assessment-model.mjs';

const account = (id, label, states) => ({
  id, label, recovery: '', mfa: 'enabled', password: 'enabled', ...states
});

test('confirmed gaps precede unknown protections and recovery links break ties', () => {
  const accounts = [
    account('forum', 'Old forum', { recovery: 'email', password: 'missing' }),
    account('notes', 'Cloud notes', { recovery: 'email', mfa: 'unknown' }),
    account('email', 'Primary email', { mfa: 'missing', password: 'unknown' })
  ];
  const actions = buildActionPlan(accounts);
  assert.deepEqual(actions.map(({ label, state }) => [label, state]), [
    ['Primary email', 'missing'], ['Old forum', 'missing'],
    ['Primary email', 'unknown'], ['Cloud notes', 'unknown']
  ]);
  assert.match(describeAction(actions[0]), /recovery account for 2 accounts/);
  assert.match(formatActionPlan(accounts, actions), /Old forum uses Primary email for recovery/);
});

test('reciprocal recovery links count once and enabled protections produce no action', () => {
  const accounts = [
    account('a', 'Account A', { recovery: 'b', mfa: 'unknown' }),
    account('b', 'Account B', { recovery: 'a' })
  ];
  const actions = buildActionPlan(accounts);
  assert.equal(actions.length, 1);
  assert.match(describeAction(actions[0]), /recovery account for 1 account\./);
  assert.deepEqual(buildActionPlan([accounts[1]]), []);
});
