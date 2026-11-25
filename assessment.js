import { buildActionPlan, describeAction, formatActionPlan } from './assessment-model.mjs?v=3';

const section = document.querySelector('#my-cybertwin');
const form = section.querySelector('form');
const rows = section.querySelector('#assessment-accounts');
const links = section.querySelector('#assessment-links');
const plan = section.querySelector('#assessment-plan');
const status = section.querySelector('#assessment-status');
const exportButton = section.querySelector('#assessment-export');
const template = section.querySelector('template');
const accounts = [];
let nextId = 1;
let actions = [];

function renderList(list, entries, emptyMessage) {
  list.replaceChildren(...(entries.length ? entries : [emptyMessage]).map(entry => {
    const item = document.createElement('li');
    item.textContent = entry;
    return item;
  }));
}

function renderPlan() {
  const labels = new Map(accounts.map(account => [account.id, account.label]));
  const connections = accounts.filter(account => labels.has(account.recovery)).map(account =>
    account.label + ' uses ' + labels.get(account.recovery) + ' for recovery.'
  );
  renderList(links, connections, 'Choose a recovery account to add a connection.');
  actions = buildActionPlan(accounts);
  renderList(plan, actions.map(describeAction), accounts.length
    ? 'All listed protections are marked enabled.'
    : 'Add an account to see your action plan.');
  exportButton.disabled = accounts.length === 0;
}

function renderAccounts() {
  rows.replaceChildren(...accounts.map(account => {
    const row = template.content.firstElementChild.cloneNode(true);
    row.querySelector('legend').textContent = account.label;
    const recovery = row.querySelector('[name="recovery"]');
    for (const option of accounts) {
      if (option.id !== account.id) recovery.add(new Option(option.label, option.id));
    }
    for (const select of row.querySelectorAll('select')) {
      select.value = account[select.name];
      select.addEventListener('change', () => {
        account[select.name] = select.value;
        renderPlan();
        status.textContent = 'Action plan updated.';
      });
    }
    const remove = row.querySelector('button');
    remove.setAttribute('aria-label', 'Remove ' + account.label);
    remove.addEventListener('click', () => {
      accounts.splice(accounts.indexOf(account), 1);
      for (const other of accounts) {
        if (other.recovery === account.id) other.recovery = '';
      }
      renderAccounts();
      form.elements.label.focus();
      status.textContent = account.label + ' removed.';
    });
    return row;
  }));
  renderPlan();
}

form.addEventListener('submit', event => {
  event.preventDefault();
  const input = form.elements.label;
  const label = input.value.trim();
  if (!label || label.includes('@')) {
    status.textContent = 'Use a short label such as Primary email.';
  } else if (accounts.some(account => account.label.toLowerCase() === label.toLowerCase())) {
    status.textContent = 'Choose a different label for this account.';
  } else if (accounts.length >= 30) {
    status.textContent = 'This assessment supports up to 30 accounts.';
  } else {
    accounts.push({ id: String(nextId++), label, recovery: '', importance: 'unrated', mfa: 'unknown', password: 'unknown' });
    form.reset();
    renderAccounts();
    status.textContent = label + ' added.';
  }
  input.focus();
});

exportButton.addEventListener('click', () => {
  const blob = new Blob([formatActionPlan(accounts, actions)], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'my-cybertwin-action-plan.txt';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

renderAccounts();
form.querySelector("button").disabled = false;
