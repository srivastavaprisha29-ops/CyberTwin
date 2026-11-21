export const signals = {
  mfa: { action: 'Enable email MFA', points: 30, reason: 'The email account relies on a password alone.' },
  password: { action: 'Set a unique forum password', points: 23, reason: 'The community forum shares a password with another account.' },
  contact: { action: 'Remove public contact details', points: 10, reason: 'The personal website displays private contact details.' }
};

export function calculateRisk(resolvedSignals) {
  const activePoints = Object.fromEntries(Object.entries(signals).map(([key, signal]) => [
    key, resolvedSignals.has(key) ? 0 : signal.points
  ]));
  const total = Object.values(activePoints).reduce((sum, points) => sum + points, 0);
  return { activePoints, total };
}

export function prioritizeActions(activePoints) {
  return Object.entries(activePoints)
    .filter(([, points]) => points > 0)
    .sort(([, first], [, second]) => second - first)
    .map(([key, points]) => ({ action: signals[key].action, points }));
}

export function formatRiskReport(resolvedSignals) {
  const { activePoints, total } = calculateRisk(resolvedSignals);
  const { total: baseline } = calculateRisk(new Set());
  const completed = Object.entries(signals)
    .filter(([key]) => resolvedSignals.has(key))
    .map(([, signal]) => '- ' + signal.action);
  const remaining = prioritizeActions(activePoints)
    .map(({ action, points }) => '- ' + action + ' (' + points + ' points)');
  return [
    'CyberTwin demo report',
    'Fictional profile: Alex Rivera',
    '',
    'Baseline score: ' + baseline + '/100',
    'Current score: ' + total + '/100',
    'Points reduced: ' + (baseline - total),
    '',
    'Completed actions',
    ...(completed.length ? completed : ['None']),
    '',
    'Remaining actions by score impact',
    ...(remaining.length ? remaining : ['None']),
    '',
    'Scores use illustrative weights for this fictional scenario.',
    ''
  ].join('\n');
}
