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

const termsKey = uid => `redactme.customTerms.v1.${uid || 'anonymous'}`;
export function loadTerms(uid) {
  try {
    const value = JSON.parse(localStorage.getItem(termsKey(uid)) || '[]');
    return Array.isArray(value) ? value.filter(t => typeof t === 'string').join('\n') : '';
  } catch { return ''; }
}
function saveTerms(uid, text) {
  try { localStorage.setItem(termsKey(uid), JSON.stringify(parseTerms(text))); } catch { /* session only */ }
}
// One term per line (commas also separate terms); duplicates ignored; the server enforces limits too.
export function parseTerms(text) {
  const seen = new Set();
  return String(text).split(/[\n,]+/).map(t => t.trim().replace(/\s+/g, ' ')).filter(t => {
    const key = t.toLowerCase();
    if (t.length < 2 || t.length > 100 || seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, 50);
}

export const SENSITIVITY_LEVELS = [
  { value: 'low', label: 'Low', summary: 'Flags only what it is very sure about. Fewer false alarms, but expect more manual redaction.' },
  { value: 'balanced', label: 'Balanced', summary: 'A good mix of coverage and accuracy. Recommended.' },
  { value: 'high', label: 'High', summary: 'Flags anything that might be sensitive. Catches the most, but expect extra suggestions to untick.' },
];
const sensitivityKey = uid => `redactme.sensitivity.v1.${uid || 'anonymous'}`;
export function loadSensitivity(uid) {
  try {
    const value = localStorage.getItem(sensitivityKey(uid));
    return SENSITIVITY_LEVELS.some(level => level.value === value) ? value : 'balanced';
  } catch { return 'balanced'; }
}
function saveSensitivity(uid, value) {
  try { localStorage.setItem(sensitivityKey(uid), value); } catch { /* session only */ }
}

export function optionsPanelHtml() {
  const groups = OPTION_GROUPS.map(group => `<fieldset class="option-group"><legend>${group.title}</legend>${group.items.map(item => `<label class="option"><input type="checkbox" data-type="${item.type}" checked><span><span class="option-label">${item.label}</span>${item.hint ? `<small>${item.hint}</small>` : ''}</span><span class="option-count" data-count="${item.type}" aria-hidden="true"></span></label>`).join('')}</fieldset>`).join('');
  const levels = SENSITIVITY_LEVELS.map(level => `<label class="level"><input type="radio" name="sensitivity" value="${level.value}"><span>${level.label}</span></label>`).join('');
  return `<aside class="options-panel" aria-labelledby="options-title"><div class="panel-heading"><div><p class="eyebrow">YOUR PREFERENCES</p><h2 id="options-title">Redaction options</h2></div></div><p class="options-intro">Choose what Redact Me looks for. Unchecked items are not suggested or redacted.</p><fieldset class="option-group sensitivity"><legend>Detection sensitivity</legend><div class="level-row" role="radiogroup" aria-label="Detection sensitivity">${levels}</div><p id="sensitivity-summary" class="sensitivity-summary"></p><small class="terms-hint">Applied when you start a scan. Rescan to change it.</small></fieldset>${groups}<fieldset class="option-group"><legend>Your custom terms</legend><label class="terms-label" for="custom-terms">Always redact these words or names</label><textarea id="custom-terms" rows="4" maxlength="3000" spellcheck="false" placeholder="One per line, e.g. a client name, company or project"></textarea><small class="terms-hint">Matched everywhere in any capitalization. Applied when you start a scan.</small></fieldset><div class="options-actions"><button id="options-reset" type="button" class="text-button">Reset to defaults</button></div><p class="options-note">Saved in this browser only.</p></aside>`;
}

export function setupRedactionOptions(root, user) {
  const panel = root.querySelector('.options-panel');
  const inputs = [...panel.querySelectorAll('input[data-type]')];
  const disabled = loadDisabled(user.uid);
  const listeners = new Set();
  const levelInputs = [...panel.querySelectorAll('input[name=sensitivity]')];
  let sensitivity = loadSensitivity(user.uid);
  const summaryEl = panel.querySelector('#sensitivity-summary');
  const showLevel = () => {
    levelInputs.forEach(input => { input.checked = input.value === sensitivity; input.closest('.level').classList.toggle('on', input.checked); });
    summaryEl.textContent = SENSITIVITY_LEVELS.find(level => level.value === sensitivity).summary;
  };
  showLevel();
  const onLevel = event => {
    if (event.target.name !== 'sensitivity') return;
    sensitivity = event.target.value;
    saveSensitivity(user.uid, sensitivity);
    showLevel();
  };
  panel.addEventListener('change', onLevel);
  const termsBox = panel.querySelector('#custom-terms');
  termsBox.value = loadTerms(user.uid);
  const onTerms = () => saveTerms(user.uid, termsBox.value);
  termsBox.addEventListener('input', onTerms);
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
    getTerms: () => parseTerms(termsBox.value),
    getSensitivity: () => sensitivity,
    onChange(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    setLocked(locked) { panel.classList.toggle('locked', locked); inputs.forEach(i => { i.disabled = locked; }); panel.querySelector('#options-reset').disabled = locked; termsBox.disabled = locked; levelInputs.forEach(i => { i.disabled = locked; }); },
    setCounts(counts) {
      panel.querySelectorAll('[data-count]').forEach(el => { const n = counts[el.dataset.count]; el.textContent = n ? String(n) : ''; });
    },
    destroy() { panel.removeEventListener('change', onChange); panel.removeEventListener('change', onLevel); termsBox.removeEventListener('input', onTerms); listeners.clear(); },
  };
}
