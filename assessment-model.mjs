const protectionAdvice = {
  mfa: {
    missing: 'Enable multifactor authentication where available.',
    unknown: 'Check whether multifactor authentication is enabled.',
    code: 'Consider a phishing-resistant sign-in option, such as a passkey, where supported.'
  },
  password: {
    missing: 'Replace the reused password with a unique password.',
    unknown: 'Check whether this account uses a unique password.'
  }
};

export function buildActionPlan(accounts) {
  const dependentCounts = new Map();
  const essentialByRecovery = new Map();
  const reuseGroups = new Map();
  for (const account of accounts) {
    if (account.password?.startsWith('reuse-')) {
      const group = reuseGroups.get(account.password) ?? [];
      group.push(account);
      reuseGroups.set(account.password, group);
    }
  }
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
      const reuseGroup = protection === 'password' ? reuseGroups.get(account.password) : undefined;
      const state = reuseGroup ? 'missing' : account[protection];
      if (advice[state]) {
        actions.push({ label: account.label, advice: advice[state], state, dependents, essential, essentialDependents, essentialImpact,
          reusePartners: reuseGroup?.filter(member => member.id !== account.id).map(member => member.label) ?? []
        });
      }
    }
  }

  const priority = { missing: 0, unknown: 1, code: 2 };
  // Address gaps and unknown protections before optional upgrades.
  return actions.sort((a, b) =>
    priority[a.state] - priority[b.state] ||
    b.essentialImpact - a.essentialImpact ||
    b.dependents - a.dependents
  );
}

export function describeAction({ label, advice, dependents, essential, essentialDependents, reusePartners = [] }) {
  const reason = dependents
    ? ' It is the recovery account for ' + dependents + (dependents === 1 ? ' account.' : ' accounts.')
    : '';
  const importance = essential ? ' You marked this account as essential.' : '';
  const recovery = essentialDependents.length
    ? ' Essential accounts relying on it: ' + essentialDependents.join(', ') + '.'
    : '';
  const reuse = reusePartners.length ? ' Replace it on these accounts too: ' + reusePartners.join(', ') + '.' : '';
  return label + ' — ' + advice + reason + importance + recovery + reuse;
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
