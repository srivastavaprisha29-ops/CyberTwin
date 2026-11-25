import { calculateRisk, formatRiskReport, prioritizeActions, signals } from './risk-model.mjs';

(() => {
  const demo = document.querySelector('#demo');
  const nodes = [...demo.querySelectorAll('[data-node]')];
  const actions = [...demo.querySelectorAll('[data-action]')];
  const relatedSignal = { email: 'mfa', forum: 'password', site: 'contact' };
  const authMethod = demo.querySelector('#demo-auth-method');
  const authDetail = demo.querySelector('#demo-auth-detail');
  const reuseDetail = demo.querySelector('#demo-reuse-detail');
  const authentication = {
    password: 'A password alone provides no additional sign-in check if the password is exposed.',
    otp: 'An authenticator app adds a second factor. A manually entered one-time code still lacks phishing resistance.',
    passkey: 'WebAuthn binds the sign-in credential to the legitimate site. This provides phishing resistance.'
  };
  const priorities = demo.querySelector('#demo-priorities');
  const priorityStatus = demo.querySelector('#demo-priority-status');
  const storageKey = 'cybertwin.demo.actions.v1';
  let selected = 'profile';

  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (Array.isArray(saved)) {
      actions.forEach(action => { action.checked = saved.includes(action.dataset.action); });
    }
  } catch {
    // The example remains usable when browser storage is unavailable.
  }

  function saveProgress() {
    try {
      const resolved = [...getResolvedSignals()];
      if (resolved.length) {
        localStorage.setItem(storageKey, JSON.stringify(resolved));
      } else {
        localStorage.removeItem(storageKey);
      }
    } catch {
      // Keep the current session usable without persistent storage.
    }
  }

  function getResolvedSignals() {
    return new Set(actions.filter(action => action.checked).map(action => action.dataset.action));
  }

  function render() {
    const { activePoints, total } = calculateRisk(getResolvedSignals());
    const remaining = prioritizeActions(activePoints);
    priorities.replaceChildren(...remaining.map(({ action, points }) => {
      const item = document.createElement('li');
      item.textContent = action + ' (−' + points + ' points)';
      return item;
    }));
    priorityStatus.textContent = remaining.length
      ? remaining.length + (remaining.length === 1 ? ' action remaining.' : ' actions remaining.')
      : 'All protective actions in this scenario are complete.';
    authDetail.textContent = authentication[authMethod.value];
    reuseDetail.textContent = activePoints.password
      ? 'In this scenario, the forum and another service share a password. An exposure at one can put the other at risk.'
      : 'The forum now has a unique password. Exposure of that password no longer compromises the other account through reuse.';
    demo.querySelector('#demo-score').textContent = total + ' / 100';
    nodes.forEach(node => node.setAttribute('aria-pressed', String(node.dataset.node === selected)));
    const key = relatedSignal[selected] ?? selected;
    demo.querySelector('#demo-detail').textContent = key === 'profile'
      ? 'Three accounts contribute to Alex’s overall exposure.'
      : activePoints[key]
        ? signals[key].reason + ' Adds ' + activePoints[key] + ' points.'
        : 'Protective action applied. This signal now adds 0 points.';
  }

  nodes.forEach(node => node.addEventListener('click', () => {
    selected = node.dataset.node;
    render();
  }));
  actions.forEach(action => action.addEventListener('change', () => {
    saveProgress();
    render();
  }));
  authMethod.addEventListener('change', render);
  demo.querySelector('#demo-download').addEventListener('click', () => {
    const report = new Blob([formatRiskReport(getResolvedSignals())], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(report);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'cybertwin-demo-report.txt';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  demo.querySelector('#demo-reset').addEventListener('click', () => {
    actions.forEach(action => { action.checked = false; });
    saveProgress();
    authMethod.value = 'password';
    selected = 'profile';
    render();
  });
  render();
})();
