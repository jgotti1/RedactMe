const DEFAULT_SUBTITLES = ['Start with a document', 'You make the decisions', 'Verify before sharing'];

// Drives the three-step progress strip: earlier steps show a check, the current step is highlighted.
export function setWorkflow(root, step, { sub, complete = false } = {}) {
  const items = root.querySelectorAll('.workflow li');
  items.forEach((item, index) => {
    const done = complete || index < step - 1;
    const current = !complete && index === step - 1;
    item.classList.toggle('done', done);
    item.classList.toggle('busy', current && Boolean(sub) && /…$/.test(sub));
    if (current) item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current');
    item.querySelector(':scope > span').textContent = done ? '✓' : `0${index + 1}`;
    item.querySelector('small').textContent = (current || (complete && index === items.length - 1)) && sub ? sub : (done ? 'Complete' : DEFAULT_SUBTITLES[index]);
  });
  root.querySelector('.workflow')?.setAttribute('aria-label', `Document workflow, step ${Math.min(step, 3)} of 3${complete ? ', complete' : ''}`);
}
