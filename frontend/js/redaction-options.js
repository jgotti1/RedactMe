// What Redact Me looks for. Every option defaults to on; the user's choices are remembered per account.
// Storage is isolated behind load/save so it can move from browser storage to a database later.
export const OPTION_GROUPS = [
  { title: 'Identity', items: [
    { type: 'PERSON_NAME', label: 'Names', hint: 'People, spouses, dependents' },
    { type: 'DATE_OF_BIRTH', label: 'Dates of birth' },
    { type: 'SSN', label: 'Social Security numbers' },
    { type: 'ID_NUMBER', label: 'ID numbers', hint: 'License, passport, ITIN' },
  ] },
  { title: 'Contact', items: [
    { type: 'ADDRESS', label: 'Addresses' },
    { type: 'PHONE', label: 'Phone numbers' },
    { type: 'EMAIL', label: 'Email addresses' },
  ] },
  { title: 'Financial', items: [
    { type: 'BANK_ACCOUNT', label: 'Bank account numbers' },
    { type: 'BANK_ROUTING', label: 'Routing numbers' },
    { type: 'CREDIT_CARD', label: 'Card numbers' },
    { type: 'EIN', label: 'Employer ID numbers' },
  ] },
  { title: 'Other', items: [
    { type: 'OTHER_SENSITIVE', label: 'Other sensitive details', hint: 'Found by AI review' },
  ] },
];

const storageKey = uid => `redactme.redactionOptions.v1.${uid || 'anonymous'}`;

// Stores only the types the user turned OFF, so any type added later starts enabled.
export function loadDisabled(uid) {
  try {
    const value = JSON.parse(localStorage.getItem(storageKey(uid)) || '{}');
    return new Set(Array.isArray(value.disabled) ? value.disabled.filter(t => typeof t === 'string') : []);
  } catch { return new Set(); }
}
export function saveDisabled(uid, disabled) {
  try { localStorage.setItem(storageKey(uid), JSON.stringify({ disabled: [...disabled] })); } catch { /* storage unavailable: choices apply for this session only */ }
}

export function optionsPanelHtml() {
  const groups = OPTION_GROUPS.map(group => `<fieldset class="option-group"><legend>${group.title}</legend>${group.items.map(item => `<label class="option"><input type="checkbox" data-type="${item.type}" checked><span><span class="option-label">${item.label}</span>${item.hint ? `<small>${item.hint}</small>` : ''}</span><span class="option-count" data-count="${item.type}" aria-hidden="true"></span></label>`).join('')}</fieldset>`).join('');
  return `<aside class="options-panel" aria-labelledby="options-title"><div class="panel-heading"><div><p class="eyebrow">YOUR PREFERENCES</p><h2 id="options-title">Redaction options</h2></div></div><p class="options-intro">Choose what Redact Me looks for. Unchecked items are not suggested or redacted.</p>${groups}<div class="options-actions"><button id="options-reset" type="button" class="text-button">Reset to defaults</button></div><p class="options-note">Saved in this browser only.</p></aside>`;
}

export function setupRedactionOptions(root, user) {
  const panel = root.querySelector('.options-panel');
  const inputs = [...panel.querySelectorAll('input[data-type]')];
  const disabled = loadDisabled(user.uid);
  const listeners = new Set();
  const sync = () => inputs.forEach(input => { input.checked = !disabled.has(input.dataset.type); });
  const notify = () => listeners.forEach(fn => fn());
  sync();
  const onChange = event => {
    const type = event.target.dataset?.type;
    if (!type) return;
    event.target.checked ? disabled.delete(type) : disabled.add(type);
    saveDisabled(user.uid, disabled);
    notify();
  };
  const onReset = () => { disabled.clear(); saveDisabled(user.uid, disabled); sync(); notify(); };
  panel.addEventListener('change', onChange);
  panel.querySelector('#options-reset').addEventListener('click', onReset);
  return {
    isEnabled: type => !disabled.has(type),
    onChange(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    setLocked(locked) { panel.classList.toggle('locked', locked); inputs.forEach(i => { i.disabled = locked; }); panel.querySelector('#options-reset').disabled = locked; },
    setCounts(counts) {
      panel.querySelectorAll('[data-count]').forEach(el => { const n = counts[el.dataset.count]; el.textContent = n ? String(n) : ''; });
    },
    destroy() { panel.removeEventListener('change', onChange); listeners.clear(); },
  };
}
