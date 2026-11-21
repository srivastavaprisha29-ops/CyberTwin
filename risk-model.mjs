export const signals = {
  mfa: { points: 30, reason: 'The email account relies on a password alone.' },
  password: { points: 23, reason: 'The community forum shares a password with another account.' },
  contact: { points: 10, reason: 'The personal website displays private contact details.' }
};

export function calculateRisk(resolvedSignals) {
  const activePoints = Object.fromEntries(Object.entries(signals).map(([key, signal]) => [
    key, resolvedSignals.has(key) ? 0 : signal.points
  ]));
  const total = Object.values(activePoints).reduce((sum, points) => sum + points, 0);
  return { activePoints, total };
}
