import { setupDocumentUpload } from './document-upload.js';
import { optionsPanelHtml } from './redaction-options.js';

let disposeUpload;
export function disposeWorkspace() {
  disposeUpload?.();
  disposeUpload = undefined;
}
const sampleFindings = [
  { id: 'name', label: 'Full name', value: 'Alex Example', reason: 'Personal information', selected: true },
  { id: 'email', label: 'Email address', value: 'alex@example.com', reason: 'Contact information', selected: true },
  { id: 'reference', label: 'Account reference', value: 'DEMO-0042', reason: 'Account information', selected: true },
];

export function showWorkspace(user) {
  disposeWorkspace();
  const root = document.querySelector('#workspace-content');
  root.innerHTML = `

    <ol class="workflow" aria-label="Document workflow"><li aria-current="step"><span>01</span><div><strong>Upload your PDF</strong><small>Start with a document</small></div></li><li><span>02</span><div><strong>Review & approve</strong><small>You make the decisions</small></div></li><li><span>03</span><div><strong>Redact & download</strong><small>Verify before sharing</small></div></li></ol>
    <div class="workspace-grid">
      ${optionsPanelHtml()}
      <section class="document-area" aria-labelledby="document-title"><div class="panel-heading"><div><p class="eyebrow">YOUR DOCUMENT</p><h2 id="document-title">Start with a PDF</h2></div><span id="document-tag" class="workspace-label">No document</span></div>
        <div id="upload-empty" class="upload-empty">
          <div id="upload-prompt"><span class="upload-symbol" aria-hidden="true">↑</span><h3>Your next document starts here</h3><p>Choose a PDF to upload and validate.<br>You’ll review changes before any redaction.</p><input id="pdf-file" type="file" accept=".pdf,application/pdf" hidden><button id="choose-pdf" class="primary" type="button" aria-describedby="upload-note">Choose PDF <span aria-hidden="true">+</span></button></div>
          <p id="upload-progress" role="status" aria-live="polite" hidden></p>
          <div id="upload-ready" hidden><span class="upload-symbol" aria-hidden="true">✓</span><h3 id="uploaded-name"></h3><p id="uploaded-details"></p><button id="start-scan" class="primary" type="button" disabled>Start scan <span aria-hidden="true">→</span></button><p class="availability">The scan runs on our server; your PDF is not stored permanently.</p></div>
          <button id="remove-pdf" class="text-button" type="button" hidden>Remove PDF</button>
          <p id="upload-alert" class="upload-alert" role="alert" hidden></p>
          <p id="upload-note" class="availability">PDF only · Up to 20 MB · 200 pages<br>Temporary upload expires after 15 minutes. No permanent storage.</p><button id="sample-open" class="text-button" type="button">Explore a sample review →</button>
        </div>
        <div id="review-view" hidden>
          <div class="sample-toolbar"><span id="page-label">Page 1</span><span class="page-nav"><button id="review-cancel" class="text-button" type="button">Discard document</button><button id="first-page" class="text-button" type="button" aria-label="First page">⇤ First</button><button id="prev-page" class="text-button" type="button">← Previous</button><button id="next-page" class="text-button" type="button">Next →</button><button id="last-page" class="text-button" type="button" aria-label="Last page">Last ⇥</button></span></div>
          <div class="live-sensitivity"><label for="live-sensitivity"><strong>Detection sensitivity</strong></label><div class="live-slider"><span aria-hidden="true">Low</span><input id="live-sensitivity" type="range" min="0" max="2" step="1" value="1" aria-describedby="live-sensitivity-note"><span aria-hidden="true">High</span></div><div class="live-stops" role="group" aria-label="Set detection sensitivity"><button type="button" class="level-stop" data-level="low">Low</button><button type="button" class="level-stop" data-level="balanced">Balanced</button><button type="button" class="level-stop" data-level="high">High</button></div><p id="live-sensitivity-note" class="live-note" role="status" aria-live="polite"></p></div>
          <div class="paper-stage"><div id="page-stage" class="page-stage"><img id="page-image" alt="Document page preview" draggable="false"><div id="page-overlay" class="page-overlay"></div></div></div>
          <p id="draw-hint" class="availability" hidden>Drag on the page to draw an area to redact. Select a drawn box to remove it.</p>
        </div>
        <div id="sample-view" hidden><div class="sample-toolbar"><span>Sample document · Page 1 of 1</span><button id="sample-close" class="text-button" type="button">Close sample</button></div><div class="paper-stage"><article class="sample-paper" aria-label="Fictional sample document"><p class="sample-overline">EXAMPLE DOCUMENT / NOT A REAL PDF</p><h3>Client summary</h3><p class="sample-date">Prepared for document review</p><hr><p>This summary contains fictional details to demonstrate how a review could look.</p><dl><dt>Client name</dt><dd><mark data-finding="name">Alex Example</mark></dd><dt>Email address</dt><dd><mark data-finding="email">alex@example.com</mark></dd><dt>Account reference</dt><dd><mark data-finding="reference">DEMO-0042</mark></dd></dl><p class="sample-end">Review each highlighted detail before approving any changes.</p></article></div></div>
        <div class="document-footnote"><span class="dot" aria-hidden="true"></span>You stay in control of every redaction.</div>
      </section>
      <aside class="review-panel" aria-labelledby="review-title"><div class="panel-heading"><div><p class="eyebrow">YOU HAVE THE FINAL SAY</p><h2 id="review-title">Review changes</h2></div><span id="finding-count" class="count-pill">0</span></div><div id="review-empty" class="review-empty"><span aria-hidden="true">☷</span><h3>Nothing to review yet</h3><p>Suggested redactions will appear here. Keep what matters and approve what should stay private.</p></div><div id="scan-review" hidden><p id="scan-banner" class="sample-disclaimer" role="status" aria-live="polite"></p><div id="scan-findings"></div></div><div id="sample-review" hidden><p class="sample-disclaimer">Sample only. Toggle the fictional findings to preview your choices.</p><div id="findings"></div><p id="selection-summary" class="selection-summary" role="status" aria-live="polite"></p></div><div class="review-actions"><button id="manual-toggle" type="button" class="outline" disabled aria-pressed="false">Add manual redaction</button><button id="next-unviewed" type="button" class="secondary" hidden>Go to next unviewed page →</button><button id="approve-redact" type="button" class="primary" disabled>Approve & redact <span aria-hidden="true">→</span></button><button id="discard-restart" type="button" class="text-button danger" hidden>Discard & start over</button><p id="review-note">Scan a document to review suggestions. Nothing is redacted until you approve.</p></div></aside>
    </div>
    <section class="download-panel" aria-labelledby="download-title"><div class="download-icon" aria-hidden="true">↓</div><div><h2 id="download-title">Your finished PDF, ready to share</h2><p id="download-note">Download becomes available after approved redactions pass verification.</p><p id="download-warning" class="download-warning"><strong>Important:</strong> Once you download your redacted PDF, the copy held in temporary memory is permanently deleted from our server to protect the privacy and security of your document. It cannot be downloaded a second time, so please save it in a secure location.</p></div><button id="download-pdf" class="secondary" type="button" disabled>Download PDF</button></section>`;
  document.querySelector('#workspace-status').textContent = '';
  const findings = sampleFindings.map(finding => ({ ...finding }));
  const renderSelections = () => {
    const count = findings.filter(finding => finding.selected).length;
    document.querySelector('#selection-summary').textContent = `${count} of ${findings.length} sample details selected for redaction`;
    for (const finding of findings) {
      const mark = root.querySelector(`[data-finding="${finding.id}"]`);
      mark.classList.toggle('selected', finding.selected);
    }
  };
  document.querySelector('#findings').innerHTML = findings.map(finding => `<label class="finding"><input type="checkbox" value="${finding.id}" checked><span><strong>${finding.label}</strong><span class="finding-value">${finding.value}</span><small>${finding.reason}</small></span></label>`).join('');
  document.querySelector('#findings').addEventListener('change', event => {
    const finding = findings.find(item => item.id === event.target.value);
    if (finding) finding.selected = event.target.checked;
    renderSelections();
  });
  const setSample = (active) => {
    document.querySelector('#upload-empty').hidden = active;
    document.querySelector('#review-empty').hidden = active;
    document.querySelector('#sample-view').hidden = !active;
    document.querySelector('#sample-review').hidden = !active;
    document.querySelector('#document-title').textContent = active ? 'Sample review' : 'Start with a PDF';
    document.querySelector('#document-tag').textContent = active ? 'Fictional sample' : 'No document';
    document.querySelector('#finding-count').textContent = active ? '3' : '0';
    if (!active) {
      findings.forEach(finding => { finding.selected = true; });
      root.querySelectorAll('#findings input').forEach(input => { input.checked = true; });
    }
    renderSelections();
    document.querySelector(active ? '#sample-close' : '#sample-open').focus();
  };
  disposeUpload = setupDocumentUpload(root, user);
  document.querySelector('#sample-open').addEventListener('click', () => setSample(true));
  document.querySelector('#sample-close').addEventListener('click', () => setSample(false));
}
