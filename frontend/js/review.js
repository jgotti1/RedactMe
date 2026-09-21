import { previewPage, redactPdf, downloadPdf } from './api.js';
import { setWorkflow } from './workflow.js';

const TYPE_LABELS = { SSN: 'Social Security number', EIN: 'Employer ID number', BANK_ACCOUNT: 'Bank account', BANK_ROUTING: 'Bank routing number', CREDIT_CARD: 'Card number', EMAIL: 'Email address', PHONE: 'Phone number', ADDRESS: 'Address', PERSON_NAME: 'Person name', DATE_OF_BIRTH: 'Date of birth', ID_NUMBER: 'ID number', OTHER_SENSITIVE: 'Other sensitive detail' };

// Review, manual redaction, approval and download for one scanned document.
export function createReview({ root, result, documentId, user, options, fileName = '', onFinished }) {
  const base = fileName.replace(/\.pdf$/i, '').replace(/[\\/:*?"<>|\x00-\x1f]/g, '_').trim().slice(0, 120) || 'document';
  const outputName = `${base}_redacted.pdf`;
  let finished = false;
  let approved = false;
  const view = root.querySelector('#review-view');
  const image = root.querySelector('#page-image');
  const overlay = root.querySelector('#page-overlay');
  const label = root.querySelector('#page-label');
  const toggle = root.querySelector('#manual-toggle');
  const approve = root.querySelector('#approve-redact');
  const note = root.querySelector('#review-note');
  const list = root.querySelector('#scan-findings');
  const banner = root.querySelector('#scan-banner');
  const download = root.querySelector('#download-pdf');
  const downloadNote = root.querySelector('#download-note');
  const pages = new Map(result.pages.map(p => [p.page, p]));
  const enabled = f => options.isEnabled(f.type);
  const visible = () => result.findings.filter(enabled);
  const selected = new Set(result.findings.filter(f => f.recommend_redaction && enabled(f)).map(f => f.id));
  const manual = [];
  let page = 1;
  let drawing = false;
  let draft;
  let previewUrl;
  let controller;
  let busy = false;
  let loadingPage = false;
  let pageRequest = 0;
  let disposed = false;
  let manualSeq = 0;
  const cleanups = [];
  const on = (el, type, fn, opts) => { el.addEventListener(type, fn, opts); cleanups.push(() => el.removeEventListener(type, fn, opts)); };

  function box(rect, kind, id) {
    const p = pages.get(page);
    const el = document.createElement(kind === 'manual' ? 'button' : 'div');
    el.className = `redact-box ${kind}`;
    if (kind === 'manual') { el.type = 'button'; el.title = 'Remove this manual redaction'; el.dataset.manual = id; }
    el.style.left = `${(rect[0] / p.width) * 100}%`;
    el.style.top = `${(rect[1] / p.height) * 100}%`;
    el.style.width = `${((rect[2] - rect[0]) / p.width) * 100}%`;
    el.style.height = `${((rect[3] - rect[1]) / p.height) * 100}%`;
    return el;
  }
  function paintOverlay() {
    overlay.replaceChildren();
    for (const f of visible()) {
      if (f.page !== page) continue;
      for (const r of f.rects) overlay.append(box(r, selected.has(f.id) ? 'on' : 'off'));
    }
    for (const m of manual) if (m.page === page) overlay.append(box(m.rect, 'manual', m.id));
    if (draft) overlay.append(box(draft.rect, 'draft'));
  }
  async function showPage(n) {
    const request = ++pageRequest;
    page = n;
    draft = undefined;
    loadingPage = true;
    image.hidden = true;
    overlay.hidden = true;
    label.textContent = `Page ${page} of ${result.pages.length}`;
    root.querySelector('#prev-page').disabled = page <= 1;
    root.querySelector('#next-page').disabled = page >= result.pages.length;
    renderList();
    summary();
    controller?.abort();
    const pending = new AbortController();
    controller = pending;
    try {
      const blob = await previewPage(documentId, n, await user.getIdToken(), pending.signal);
      if (disposed || request !== pageRequest) return;
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = URL.createObjectURL(blob);
      image.src = previewUrl;
      await image.decode();
      if (disposed || request !== pageRequest) return;
      loadingPage = false;
      image.hidden = false;
      overlay.hidden = false;
      paintOverlay();
      summary();
    } catch (error) {
      if (error.name !== 'AbortError' && !disposed && request === pageRequest) {
        note.textContent = `Page ${n} could not be loaded. Switch pages and try again before adding manual areas.`;
      }
    }
  }
  function invalidateDownload() {
    approved = false;
    approve.classList.remove('approved');
    if (!busy) approve.textContent = 'Approve & redact';
    download.disabled = true;
    download.closest('.download-panel').classList.remove('ready');
    downloadNote.textContent = 'Selections changed. Approve and verify the updated redactions before downloading.';
  }
  function summary() {
    if (finished) { approve.disabled = true; toggle.disabled = true; return; }
    const total = selected.size + manual.length;
    root.querySelector('#finding-count').textContent = String(visible().filter(f => f.page === page).length);
    toggle.disabled = busy || loadingPage;
    for (const input of list.querySelectorAll('input')) input.disabled = busy || finished;
    approve.disabled = busy || total === 0 || approved;
    note.textContent = total === 0 ? 'Select at least one item or add a manual area to continue. Nothing is redacted until you approve.' : `Showing page ${page}. ${total} selected ${total === 1 ? 'item' : 'items'} across the whole document will be redacted when you approve. Your original file is unchanged.`;
  }
  function renderList() {
    list.replaceChildren();
    const currentFindings = visible().filter(f => f.page === page);
    if (!currentFindings.length) {
      const empty = document.createElement('p');
      empty.className = 'sample-disclaimer';
      const hidden = result.findings.filter(f => f.page === page && !enabled(f)).length;
      empty.textContent = hidden ? `${hidden} detected ${hidden === 1 ? 'item is' : 'items are'} hidden by your redaction options on page ${page}. You can still add a manual area.` : `No suggested changes on page ${page}. You can still add a manual area.`;
      list.append(empty);
    }
    for (const f of currentFindings) {
      const row = document.createElement('label');
      row.className = 'finding';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.checked = selected.has(f.id);
      input.dataset.id = f.id;
      const body = document.createElement('span');
      const title = document.createElement('strong');
      title.textContent = TYPE_LABELS[f.type] || f.type;
      const value = document.createElement('span');
      value.className = 'finding-value';
      value.textContent = f.masked_text;
      const detail = document.createElement('small');
      detail.textContent = `Page ${f.page} · ${f.level} confidence · ${f.sources.join(' + ')} · ${f.reason}`;
      body.append(title, value, detail);
      row.append(input, body);
      list.append(row);
    }
  }
  on(list, 'change', event => {
    const id = event.target.dataset?.id;
    if (!id || busy || finished) return;
    invalidateDownload();
    event.target.checked ? selected.add(id) : selected.delete(id);
    paintOverlay();
    summary();
  });
  on(list, 'click', event => {
    const row = event.target.closest('.finding');
    const id = row?.querySelector('input')?.dataset.id;
    const target = result.findings.find(f => f.id === id);
    if (target && event.target.tagName !== 'INPUT' && target.page !== page) showPage(target.page);
  });
  on(root.querySelector('#prev-page'), 'click', () => page > 1 && showPage(page - 1));
  on(root.querySelector('#next-page'), 'click', () => page < result.pages.length && showPage(page + 1));

  toggle.disabled = false;
  on(toggle, 'click', () => {
    if (busy || finished || loadingPage) return;
    drawing = !drawing;
    toggle.setAttribute('aria-pressed', String(drawing));
    toggle.textContent = drawing ? 'Done adding manual areas' : 'Add manual redaction';
    root.querySelector('#draw-hint').hidden = !drawing;
    overlay.classList.toggle('drawing', drawing);
  });
  function point(event) {
    const b = overlay.getBoundingClientRect();
    const p = pages.get(page);
    const x = Math.min(Math.max((event.clientX - b.left) / b.width, 0), 1) * p.width;
    const y = Math.min(Math.max((event.clientY - b.top) / b.height, 0), 1) * p.height;
    return [x, y];
  }
  on(overlay, 'pointerdown', event => {
    if (!drawing || busy || finished || loadingPage || event.target.closest('.manual')) return;
    overlay.setPointerCapture(event.pointerId);
    draft = { start: point(event), rect: [0, 0, 0, 0] };
    event.preventDefault();
  });
  on(overlay, 'pointermove', event => {
    if (!draft) return;
    const [x, y] = point(event);
    draft.rect = [Math.min(draft.start[0], x), Math.min(draft.start[1], y), Math.max(draft.start[0], x), Math.max(draft.start[1], y)];
    paintOverlay();
  });
  on(overlay, 'pointerup', () => {
    if (!draft || busy || finished || loadingPage) return;
    invalidateDownload();
    const [x0, y0, x1, y1] = draft.rect;
    if (x1 - x0 >= 4 && y1 - y0 >= 4) manual.push({ id: `m${++manualSeq}`, page, rect: draft.rect.map(v => Math.round(v * 100) / 100) });
    draft = undefined;
    paintOverlay();
    summary();
  });
  on(overlay, 'pointercancel', () => { draft = undefined; paintOverlay(); });
  on(overlay, 'click', event => {
    const el = event.target.closest('.manual');
    if (!el || busy || finished || loadingPage) return;
    invalidateDownload();
    const index = manual.findIndex(m => m.id === el.dataset.manual);
    if (index >= 0) manual.splice(index, 1);
    paintOverlay();
    summary();
  });

  on(approve, 'click', async () => {
    if (busy || approve.disabled) return;
    busy = true;
    options.setLocked(true);
    draft = undefined;
    summary();
    approve.textContent = 'Redacting & verifying…';
    approve.classList.add('working');
    setWorkflow(root, 3, { sub: 'Redacting & verifying…' });
    approve.disabled = true;
    downloadNote.textContent = 'Working: removing the selected content and verifying the new PDF. This can take up to a minute; please keep this page open.';
    download.closest('.download-panel').classList.add('working');
    toggle.disabled = true;
    download.disabled = true;
    download.closest('.download-panel').classList.remove('ready');
    banner.classList.remove('error');
    banner.textContent = 'Applying redactions and verifying the result…';
    note.removeAttribute('role');
    let failure = '';
    try {
      const outcome = await redactPdf(documentId, {
        finding_ids: [...selected].filter(id => result.findings.some(f => f.id === id && enabled(f))),
        manual: manual.map(m => ({ page: m.page, rect: m.rect })),
      }, await user.getIdToken());
      if (disposed) return;
      if (outcome.status !== 'VERIFIED') throw new Error('Verification did not finish. Download remains blocked.');
      banner.textContent = `Verified. ${outcome.redaction_count} ${outcome.redaction_count === 1 ? 'area was' : 'areas were'} permanently removed and the new PDF passed verification. Download it below; it can be downloaded once.`;
      downloadNote.textContent = 'Verified redacted PDF is ready. The download is available once and then the temporary copy is deleted.';
      approved = true;
      download.disabled = false;
      download.classList.replace('secondary', 'primary');
      setWorkflow(root, 3, { sub: 'Verified. Ready to download' });
      const panel = download.closest('.download-panel');
      panel.classList.add('ready');
      panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
      download.focus({ preventScroll: true });
    } catch (error) {
      if (disposed) return;
      banner.classList.add('error');
      setWorkflow(root, 2, { sub: 'Not released. See the message' });
      failure = error instanceof TypeError ? 'Unable to reach the backend. Nothing was released; try again.' : error.message;
      banner.textContent = failure;
    } finally {
      busy = false;
      options.setLocked(finished);
      if (!disposed) {
        approve.textContent = approved ? 'PDF ready to download below ↓' : 'Approve & redact';
        approve.classList.toggle('approved', approved);
        approve.classList.remove('working');
        download.closest('.download-panel').classList.remove('working');
        if (failure) downloadNote.textContent = 'The redacted file was not released. Review the message beside the Approve & redact button.';
        renderList();
        summary();
        if (failure) { note.textContent = `Redaction did not complete: ${failure}`; note.setAttribute('role', 'alert'); }
        banner.scrollIntoView({ block: 'nearest' });
      }
    }
  });
  let savedUrl;
  on(download, 'click', async () => {
    if (finished) { onFinished?.(); return; }
    if (download.disabled) return;
    download.disabled = true;
    downloadNote.textContent = 'Preparing your verified PDF…';
    try {
      const blob = await downloadPdf(documentId, await user.getIdToken());
      // The server copy is deleted after this response, so keep the file in this browser tab until the user finishes.
      savedUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = savedUrl;
      link.download = outputName;
      document.body.append(link);
      link.click();
      link.remove();
      finished = true;
      setWorkflow(root, 3, { complete: true, sub: 'Downloaded and cleared' });
      approve.disabled = true;
      toggle.disabled = true;
      const panel = download.closest('.download-panel');
      panel.classList.remove('ready');
      downloadNote.replaceChildren(`Your redacted PDF was downloaded as ${outputName} and the temporary copy was deleted from our server. If the file did not save, `);
      const again = document.createElement('a');
      again.href = savedUrl;
      again.download = outputName;
      again.textContent = 'save it again from this page';
      downloadNote.append(again, '. Finishing clears this copy from your browser.');
      download.textContent = 'Finish and start a new document';
      download.disabled = false;
      download.focus({ preventScroll: true });
    } catch (error) {
      download.disabled = false;
      downloadNote.textContent = error instanceof TypeError ? 'The download could not reach the backend. Please try again.' : `The download could not be completed: ${error.message}`;
      download.closest('.download-panel').classList.add('ready');
    }
  });

  const counts = {};
  for (const f of result.findings) counts[f.type] = (counts[f.type] || 0) + 1;
  options.setCounts(counts);
  const wasEnabled = new Map(result.findings.map(f => [f.id, enabled(f)]));
  const stopOptions = options.onChange(() => {
    if (busy || finished || disposed) return;
    invalidateDownload();
    for (const f of result.findings) {
      const now = enabled(f);
      if (!now) selected.delete(f.id);
      else if (!wasEnabled.get(f.id) && f.recommend_redaction) selected.add(f.id);
      wasEnabled.set(f.id, now);
    }
    paintOverlay();
    renderList();
    summary();
  });
  view.hidden = false;
  root.querySelector('.workspace-grid').classList.add('reviewing');
  root.querySelector('#discard-restart').hidden = false;
  root.querySelector('#upload-empty').hidden = true;
  renderList();
  summary();
  showPage(1);

  return function destroy() {
    disposed = true;
    stopOptions();
    options.setLocked(false);
    options.setCounts({});
    controller?.abort();
    cleanups.forEach(fn => fn());
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (savedUrl) URL.revokeObjectURL(savedUrl);
    image.removeAttribute('src');
    overlay.replaceChildren();
    view.hidden = true;
    root.querySelector('.workspace-grid').classList.remove('reviewing');
    root.querySelector('#discard-restart').hidden = true;
    root.querySelector('#upload-empty').hidden = false;
    root.querySelector('#draw-hint').hidden = true;
    toggle.disabled = true;
    toggle.setAttribute('aria-pressed', 'false');
    toggle.textContent = 'Add manual redaction';
    approve.disabled = true;
    approve.textContent = 'Approve & redact';
    approve.classList.remove('approved');
    download.disabled = true;
    download.closest('.download-panel').classList.remove('ready');
    download.textContent = 'Download PDF';
    finished = false;
    download.classList.replace('primary', 'secondary');
    root.querySelector('#download-note').textContent = 'Download becomes available after approved redactions pass verification.';
    root.querySelector('#review-note').textContent = 'Scan a document to review suggestions. Nothing is redacted until you approve.';
    list.replaceChildren();
  };
}
