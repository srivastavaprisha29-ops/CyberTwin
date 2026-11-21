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
