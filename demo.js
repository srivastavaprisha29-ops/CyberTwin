(() => {
  const demo = document.querySelector('#demo');
  const nodes = [...demo.querySelectorAll('[data-node]')];
  const actions = [...demo.querySelectorAll('[data-action]')];
  const signals = {
    mfa: { points: 30, reason: 'The email account relies on a password alone.' },
    password: { points: 23, reason: 'The community forum shares a password with another account.' },
    contact: { points: 10, reason: 'The personal website displays private contact details.' }
  };
  const relatedSignal = { email: 'mfa', forum: 'password', site: 'contact' };
  const authMethod = demo.querySelector('#demo-auth-method');
  const authDetail = demo.querySelector('#demo-auth-detail');
  const reuseDetail = demo.querySelector('#demo-reuse-detail');
  const authentication = {
    password: 'A password alone provides no additional sign-in check if the password is exposed.',
    otp: 'An authenticator app adds a second factor. A manually entered one-time code still lacks phishing resistance.',
    passkey: 'WebAuthn binds the sign-in credential to the legitimate site. This provides phishing resistance.'
  };
  let selected = 'profile';

  function render() {
    const activePoints = Object.fromEntries(actions.map(action => [
      action.dataset.action,
      action.checked ? 0 : signals[action.dataset.action].points
    ]));
    authDetail.textContent = authentication[authMethod.value];
    reuseDetail.textContent = activePoints.password
      ? 'In this scenario, the forum and another service share a password. An exposure at one can put the other at risk.'
      : 'The forum now has a unique password. Exposure of that password no longer compromises the other account through reuse.';
    const total = Object.values(activePoints).reduce((sum, points) => sum + points, 0);
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
  actions.forEach(action => action.addEventListener('change', render));
  authMethod.addEventListener('change', render);
  demo.querySelector('#demo-reset').addEventListener('click', () => {
    actions.forEach(action => { action.checked = false; });
    authMethod.value = 'password';
    selected = 'profile';
    render();
  });
  render();
})();
