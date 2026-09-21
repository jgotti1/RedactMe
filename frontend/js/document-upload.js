import { uploadPdf, discardPdf, scanPdf } from './api.js';

const MAX_BYTES = 20 * 1024 * 1024;

export function setupDocumentUpload(root, user) {
  const input = root.querySelector('#pdf-file');
  const choose = root.querySelector('#choose-pdf');
  const remove = root.querySelector('#remove-pdf');
  const scan = root.querySelector('#start-scan');
  const alert = root.querySelector('#upload-alert');
  const progress = root.querySelector('#upload-progress');
  const ready = root.querySelector('#upload-ready');
  const prompt = root.querySelector('#upload-prompt');
  let pending;
  let documentId;
  let token;
  let expiry;
  let disposed = false;
  let revision = 0;

  function notify(message, error = false) {
    alert.hidden = false;
    alert.textContent = message;
    alert.classList.toggle('error', error);
    alert.setAttribute('role', error ? 'alert' : 'status');
  }
  let reset = function () {
    clearTimeout(expiry);
    ready.hidden = true;
    prompt.hidden = false;
    progress.hidden = true;
    choose.disabled = false;
    remove.hidden = true;
    scan.disabled = true;
    root.querySelector('#sample-open').disabled = false;
    root.querySelector('#document-tag').textContent = 'No document';
    input.value = '';
  };
  async function discard(keepalive = false) {
    const id = documentId;
    documentId = undefined;
    pending?.abort();
    pending = undefined;
    clearTimeout(expiry);
    if (id && token) {
      try { await discardPdf(id, token, keepalive); return true; }
      catch { return false; }
    }
    return true;
  }

  choose.addEventListener('click', () => {
    if (!user.emailVerified) {
      notify('Verify your email address using the controls above before uploading a PDF.', true);
      return;
    }
    input.click();
  });
  input.addEventListener('change', async () => {
    let file = input.files?.[0];
    input.value = '';
    if (!file) return;
    const current = ++revision;
    await discard();
    if (disposed || current !== revision) return;
    reset();
    alert.hidden = true;
    if (!user.emailVerified || !/\.pdf$/i.test(file.name) || file.size === 0 || file.size > MAX_BYTES) {
      notify(!user.emailVerified ? 'Verify your email address before uploading.' : 'Choose a nonempty .pdf file no larger than 20 MB. Nothing was uploaded.', true);
      file = undefined;
      return;
    }
    prompt.hidden = true;
    progress.hidden = false;
    progress.textContent = 'Uploading and validating your PDF…';
    remove.hidden = false;
    remove.textContent = 'Cancel upload';
    root.querySelector('#sample-open').disabled = true;
    root.querySelector('#document-tag').textContent = 'Validating';
    const controller = new AbortController();
    pending = controller;
    const timeout = setTimeout(() => controller.abort(), 60000);
    try {
      token = await user.getIdToken();
      if (disposed || current !== revision) return;
      documentId = crypto.randomUUID();
      const result = await uploadPdf(documentId, file, token, controller.signal);
      if (disposed || current !== revision) return;
      const remaining = Date.parse(result.expires_at) - Date.now();
      if (result.status !== 'VALIDATED' || result.document_id !== documentId || !Number.isFinite(remaining) || remaining <= 0) {
        throw new Error('This upload has expired. Please upload the PDF again.');
      }
      progress.hidden = true;
      ready.hidden = false;
      root.querySelector('#uploaded-name').textContent = file.name;
      root.querySelector('#uploaded-details').textContent = `${result.page_count} ${result.page_count === 1 ? 'page' : 'pages'} · ${(result.size_bytes / 1024 / 1024).toFixed(2)} MB · PDF validated`;
      root.querySelector('#document-tag').textContent = 'Valid PDF';
      remove.textContent = 'Remove PDF';
      scan.disabled = false;
      expiry = setTimeout(() => {
        ++revision;
        void discard();
        reset();
        notify('Your temporary upload has expired and is no longer available. Upload the PDF again to continue.');
      }, remaining);
    } catch (error) {
      if (disposed || current !== revision) return;
      const cleaned = await discard();
      if (disposed || current !== revision) return;
      reset();
      const message = error.name === 'AbortError' ? 'Upload timed out. Please try again.' : error instanceof TypeError ? 'Could not reach the backend. Check your connection and try again.' : error.message;
      notify(message + (cleaned ? '' : ' Cleanup could not be confirmed; any retained upload expires automatically within 15 minutes.'), true);
    } finally {
      clearTimeout(timeout);
      file = undefined;
      if (pending === controller) pending = undefined;
    }
  });
  remove.addEventListener('click', async () => {
    const current = ++revision;
    remove.disabled = true;
    const cleaned = await discard();
    if (disposed || current !== revision) return;
    remove.disabled = false;
    reset();
    notify(cleaned ? 'The upload was removed from this workspace. Your original file on your device is unchanged.' : 'The upload was cleared from this page, but server cleanup could not be confirmed. It will expire automatically within 15 minutes.', !cleaned);
  });
  const scanReview = root.querySelector('#scan-review');
  const TYPE_LABELS = { SSN: 'Social Security number', EIN: 'Employer ID number', BANK_ACCOUNT: 'Bank account', BANK_ROUTING: 'Bank routing number', CREDIT_CARD: 'Card number', EMAIL: 'Email address', PHONE: 'Phone number', ADDRESS: 'Address', PERSON_NAME: 'Person name', DATE_OF_BIRTH: 'Date of birth', ID_NUMBER: 'ID number', OTHER_SENSITIVE: 'Other sensitive detail' };
  function clearReview() {
    scanReview.hidden = true;
    root.querySelector('#scan-findings').replaceChildren();
    root.querySelector('#finding-count').textContent = '0';
    root.querySelector('#review-empty').hidden = false;
  }
  function renderReview(result) {
    const list = root.querySelector('#scan-findings');
    const banner = root.querySelector('#scan-banner');
    list.replaceChildren();
    const problems = [];
    if (result.ai_status === 'user_skipped') problems.push('AI verification was skipped; only local checks ran.');
    else if (result.ai_status !== 'ok') problems.push(result.ai_status === 'disabled' ? 'AI analysis is turned off.' : 'The AI review could not be completed.');
    if (result.unanalyzed_pages.length) problems.push(`Page${result.unanalyzed_pages.length === 1 ? '' : 's'} ${result.unanalyzed_pages.join(', ')} contain images or scanned content that cannot be analyzed yet.`);
    const count = result.findings.length;
    root.querySelector('#finding-count').textContent = String(count);
    root.querySelector('#review-empty').hidden = true;
    scanReview.hidden = false;
    if (count === 0 && result.complete) {
      banner.textContent = 'Nothing in this PDF looks to need redaction.' + (result.ai_status === 'user_skipped' ? ' (AI verification was skipped; only local checks ran.)' : '');
    } else if (count === 0) {
      banner.textContent = `No suggestions were found, but the scan was incomplete, so this is not a clean result. ${problems.join(' ')}`;
    } else {
      banner.textContent = `${count} suggested ${count === 1 ? 'redaction' : 'redactions'} found. Values are masked here. ${problems.join(' ')}`;
    }
    banner.classList.toggle('error', !result.complete);
    for (const f of result.findings) {
      const label = document.createElement('label');
      label.className = 'finding';
      const box = document.createElement('input');
      box.type = 'checkbox';
      box.checked = f.recommend_redaction;
      const body = document.createElement('span');
      const title = document.createElement('strong');
      title.textContent = TYPE_LABELS[f.type] || f.type;
      const value = document.createElement('span');
      value.className = 'finding-value';
      value.textContent = f.masked_text;
      const detail = document.createElement('small');
      detail.textContent = `Page ${f.page} · ${f.level} confidence · ${f.sources.join(' + ')} · ${f.reason}`;
      body.append(title, value, detail);
      label.append(box, body);
      list.append(label);
    }
  }
  const originalReset = reset;
  reset = function () { originalReset(); clearReview(); };
  scan.addEventListener('click', async () => {
    if (!documentId || scan.disabled) return;
    const current = revision;
    scan.disabled = true;
    root.querySelector('#document-tag').textContent = 'Scanning';
    notify('Scanning your PDF. This can take a minute…');
    try {
      const result = await scanPdf(documentId, await user.getIdToken(), !root.querySelector('#skip-ai').checked);
      if (disposed || current !== revision) return;
      alert.hidden = true;
      root.querySelector('#document-tag').textContent = 'Scan complete';
      renderReview(result);
    } catch (error) {
      if (disposed || current !== revision) return;
      root.querySelector('#document-tag').textContent = 'Scan failed';
      notify(error instanceof TypeError ? 'Unable to reach the backend. No review is available; try again.' : error.message, true);
    } finally {
      if (!disposed && current === revision) scan.disabled = !documentId;
    }
  });
  const onPageHide = () => { ++revision; void discard(true); reset(); };
  window.addEventListener('pagehide', onPageHide);
  return () => {
    disposed = true;
    ++revision;
    void discard(true);
    input.value = '';
    window.removeEventListener('pagehide', onPageHide);
  };
}
