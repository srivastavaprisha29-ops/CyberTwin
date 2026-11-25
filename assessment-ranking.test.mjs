import assert from 'node:assert/strict';
import test from 'node:test';
import { buildActionPlan, describeAction } from './assessment-model.mjs';

const account = (label, options = {}) => ({
  label, id: label, mfa: 'enabled', password: 'enabled', ...options
});

const scenarios = [
  {
    name: 'Essential payroll takes priority over three casual accounts',
    expected: 'Payroll recovery',
    accounts: [
      account('Forum recovery', { mfa: 'missing' }),
      account('Payroll recovery', { mfa: 'missing' }),
      ...['Forum', 'Recipes', 'Games'].map(label => account(label, { recovery: 'Forum recovery' })),
      account('Payroll', { importance: 'essential', recovery: 'Payroll recovery' })
    ]
  },
  {
    name: 'Essential account with its own confirmed gap takes priority',
    expected: 'Banking',
    accounts: [
      account('Forum recovery', { mfa: 'missing' }),
      account('Forum', { recovery: 'Forum recovery' }),
      account('Banking', { importance: 'essential', mfa: 'missing' })
    ]
  },
  {
    name: 'Confirmed gap precedes an unknown state',
    expected: 'Known gap',
    accounts: [
      account('Unknown state', { importance: 'essential', mfa: 'unknown' }),
      account('Known gap', { password: 'missing' })
    ]
  },
  {
    name: 'Unrated accounts retain the direct-link ranking',
    expected: 'Shared recovery',
    accounts: [
      account('Standalone', { mfa: 'missing' }),
      account('Shared recovery', { mfa: 'missing' }),
      account('Forum', { recovery: 'Shared recovery' })
    ]
  }
];

for (const { name, expected, accounts } of scenarios) {
  test(name, () => {
    assert.equal(buildActionPlan(accounts)[0].label, expected);
  });
}

test('the recommendation names essential recovery dependents', () => {
  const recommendation = buildActionPlan(scenarios[0].accounts)[0];
  assert.match(describeAction(recommendation), /Essential accounts relying on it: Payroll\./);
});

test('one-time codes receive an optional upgrade after unresolved protections', () => {
  const actions = buildActionPlan([
    account('Payroll', { importance: 'essential', mfa: 'code' }),
    account('Bank', { mfa: 'enabled' }),
    account('Forum', { mfa: 'unknown' }),
    account('Notes', { mfa: 'missing' })
  ]);
  assert.deepEqual(actions.map(action => action.label), ['Notes', 'Forum', 'Payroll']);
  assert.match(describeAction(actions[2]), /phishing-resistant sign-in/);
});

test('reuse guidance names only accounts in the same group', () => {
  const accounts = [
    account('Email', { password: 'reuse-a' }),
    account('Forum', { password: 'reuse-a' }),
    account('Store', { password: 'reuse-b' }),
    account('Notes', { password: 'missing' })
  ];
  const actions = buildActionPlan(accounts);
  assert.deepEqual(actions.map(action => action.state), Array(4).fill('missing'));
  assert.deepEqual(actions.map(action => action.reusePartners), [['Forum'], ['Email'], [], []]);
  accounts[1].password = 'enabled';
  assert.deepEqual(buildActionPlan(accounts)[0].reusePartners, []);
});
