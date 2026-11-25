const protectionAdvice = {
  mfa: {
    missing: 'Enable multifactor authentication where available.',
    unknown: 'Check whether multifactor authentication is enabled.'
  },
  password: {
    missing: 'Replace the reused password with a unique password.',
    unknown: 'Check whether this account uses a unique password.'
  }
};

export function buildActionPlan(accounts) {
  const dependentCounts = new Map();
  const essentialByRecovery = new Map();
  for (const { recovery, importance, label } of accounts) {
    if (!recovery) continue;
    dependentCounts.set(recovery, (dependentCounts.get(recovery) ?? 0) + 1);
    if (importance === 'essential') {
      const essential = essentialByRecovery.get(recovery) ?? [];
      essential.push(label);
      essentialByRecovery.set(recovery, essential);
    }
  }

  const actions = [];
  for (const account of accounts) {
    const dependents = dependentCounts.get(account.id) ?? 0;
    const essentialDependents = essentialByRecovery.get(account.id) ?? [];
    const essential = account.importance === 'essential';
    const essentialImpact = Number(essential) + essentialDependents.length;
    for (const [protection, advice] of Object.entries(protectionAdvice)) {
      const state = account[protection];
      if (advice[state]) {
        actions.push({ label: account.label, advice: advice[state], state, dependents, essential, essentialDependents, essentialImpact });
      }
    }
  }

  // Address confirmed gaps first, then consider essential accounts and direct recovery links.
  return actions.sort((a, b) =>
    Number(b.state === 'missing') - Number(a.state === 'missing') ||
    b.essentialImpact - a.essentialImpact ||
    b.dependents - a.dependents
  );
}

export function describeAction({ label, advice, dependents, essential, essentialDependents }) {
  const reason = dependents
    ? ' It is the recovery account for ' + dependents + (dependents === 1 ? ' account.' : ' accounts.')
    : '';
  const importance = essential ? ' You marked this account as essential.' : '';
  const recovery = essentialDependents.length
    ? ' Essential accounts relying on it: ' + essentialDependents.join(', ') + '.'
    : '';
  return label + ' — ' + advice + reason + importance + recovery;
}

export function formatActionPlan(accounts, actions) {
  const labels = new Map(accounts.map(account => [account.id, account.label]));
  const links = accounts.filter(account => labels.has(account.recovery));
  return [
    'My CyberTwin action plan',
    '',
    'Recovery connections',
    ...(links.length ? links.map(account => account.label + ' uses ' + labels.get(account.recovery) + ' for recovery.') : ['None entered.']),
    '',
    'Prioritized actions',
    ...(actions.length ? actions.map((action, i) => (i + 1) + '. ' + describeAction(action)) : ['All listed protections are marked enabled.']),
    '',
    'Based on the protections and recovery connections you entered.',
    ''
  ].join('\n');
}
