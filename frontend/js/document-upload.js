import { uploadPdf, discardPdf, scanPdf } from './api.js';
import { createReview } from './review.js';
import { setWorkflow } from './workflow.js';
import { setupRedactionOptions } from './redaction-options.js';

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
  const options = setupRedactionOptions(root, user);
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
    let fileError = '';
    if (!user.emailVerified) fileError = 'Verify your email address before uploading.';
    else if (file.size === 0) fileError = 'This file is empty (0 bytes) and contains no PDF data. Export or download it again.';
    else if (file.size > MAX_BYTES) fileError = 'This file exceeds the 20 MB limit. Choose a smaller PDF.';
    else if (file.type.startsWith('image/') || /\.(png|jpe?g|gif|bmp|tiff?|webp|heic)$/i.test(file.name)) fileError = 'This file appears to be an image, not a PDF. Export the image as a PDF and try again.';
    else if (!/\.pdf$/i.test(file.name)) fileError = 'This file is not a .pdf document. Export it as a PDF instead of renaming its extension.';
    if (fileError) {
      notify(`${fileError} Nothing was uploaded.`, true);
      file = undefined;
      return;
    }
    prompt.hidden = true;
    progress.hidden = false;
    progress.textContent = 'Uploading and validating your PDF…';
    setWorkflow(root, 1, { sub: 'Uploading and validating…' });
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
      setWorkflow(root, 1, { sub: 'PDF ready. Start the scan' });
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
  let destroyReview;
  function clearReview() {
    destroyReview?.();
    destroyReview = undefined;
    scanReview.hidden = true;
    root.querySelector('#finding-count').textContent = '0';
    root.querySelector('#review-empty').hidden = false;
  }
  function renderReview(result) {
    const banner = root.querySelector('#scan-banner');
    destroyReview?.();
    const problems = [];
    if (result.unanalyzed_pages.length) problems.push(`Page${result.unanalyzed_pages.length === 1 ? '' : 's'} ${result.unanalyzed_pages.join(', ')} could not be fully analyzed (scanned content was unreadable or low confidence). Review those pages manually.`);
    const count = result.findings.filter(f => (f.levels || []).includes(result.sensitivity)).length;
    root.querySelector('#review-empty').hidden = true;
    scanReview.hidden = false;
    if (count === 0 && result.complete) {
      banner.textContent = 'Nothing in this PDF looks to need redaction.' + ' You can still add manual redactions.';
    } else if (count === 0) {
      banner.textContent = `No suggestions were found, but the scan was incomplete, so this is not a clean result. ${problems.join(' ')}`;
    } else {
      banner.textContent = `${count} suggested ${count === 1 ? 'redaction' : 'redactions'} found. Values are masked here. Review them, add manual areas if needed, then approve. ${problems.join(' ')}`;
    }
    if (count === 0 && result.findings.length) banner.textContent += ' Move the sensitivity slider above the page to see more possibilities.';
    banner.classList.toggle('error', !result.complete);
    setWorkflow(root, 2, { sub: 'Choose what to redact' });
    destroyReview = createReview({ root, result, documentId, user, options, fileName: root.querySelector('#uploaded-name').textContent, onFinished: () => {
      ++revision;
      void discard();
      reset();
      notify('Your redacted PDF was downloaded and the temporary copy was deleted from our server.');
    } });
  }
  const originalReset = reset;
  reset = function () { originalReset(); clearReview(); setWorkflow(root, 1); };
  scan.addEventListener('click', async () => {
    if (!documentId || scan.disabled) return;
    const current = revision;
    scan.disabled = true;
    root.querySelector('#document-tag').textContent = 'Scanning';
    notify('Scanning your PDF. This can take a minute…');
    setWorkflow(root, 2, { sub: 'Scanning your document…' });
    try {
      const result = await scanPdf(documentId, await user.getIdToken(), options.getTerms(), options.getSensitivity());
      if (disposed || current !== revision) return;
      alert.hidden = true;
      root.querySelector('#document-tag').textContent = 'Scan complete';
      renderReview(result);
    } catch (error) {
      if (disposed || current !== revision) return;
      root.querySelector('#document-tag').textContent = 'Scan failed';
      setWorkflow(root, 1, { sub: 'Scan failed. Try again' });
      notify(error instanceof TypeError ? 'Unable to reach the backend. No review is available; try again.' : error.message, true);
    } finally {
      if (!disposed && current === revision) scan.disabled = !documentId;
    }
  });
  root.querySelector('#review-cancel').addEventListener('click', () => remove.click());
  root.querySelector('#discard-restart').addEventListener('click', () => {
    if (window.confirm('Discard this document and start over? Your selections and any redacted copy will be deleted. Your original file on your device is unchanged.')) remove.click();
  });
  const onPageHide = () => { ++revision; void discard(true); reset(); };
  window.addEventListener('pagehide', onPageHide);
  return () => {
    disposed = true;
    options.destroy();
    destroyReview?.();
    ++revision;
    void discard(true);
    input.value = '';
    window.removeEventListener('pagehide', onPageHide);
  };
}
