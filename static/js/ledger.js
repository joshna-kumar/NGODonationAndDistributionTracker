/* ==========================================================================
   Blockchain Ledger Visualizer & Tamper Verification Engine
   ========================================================================== */

const LedgerUI = {
  currentBlocks: [],
  lastVerificationResult: null,

  async loadLedger() {
    try {
      const res = await fetch('/api/ledger');
      const data = await res.json();
      this.currentBlocks = data.blocks || [];
      this.renderChain(this.currentBlocks);
    } catch (err) {
      console.error('Failed to load ledger:', err);
      App.showToast('Could not fetch blockchain ledger', 'error');
    }
  },

  renderChain(blocks, tamperedIndices = []) {
    const container = document.getElementById('blockchain-chain-container');
    if (!container) return;

    if (!blocks || blocks.length === 0) {
      container.innerHTML = `
        <div class="text-center p-5 text-muted">
          <i class="fas fa-cubes fa-3x mb-3 text-lavender"></i>
          <p>No ledger blocks recorded yet. Genesis block initializing...</p>
        </div>
      `;
      return;
    }

    let html = '';

    blocks.forEach((block, index) => {
      const isTampered = tamperedIndices.includes(block.index);
      const isGenesis = block.record_type === 'GENESIS';

      let typeClass = 'badge-lavender';
      if (block.record_type === 'DONATION') typeClass = 'badge-success';
      if (block.record_type === 'DISTRIBUTION') typeClass = 'badge-info';
      if (isGenesis) typeClass = 'badge-warning';

      const dataStr = typeof block.data === 'object' ? JSON.stringify(block.data, null, 2) : block.data;

      html += `
        <div class="block-card ${isTampered ? 'tampered-highlight' : ''}" id="block-node-${block.index}">
          <div class="block-header">
            <div class="block-index">
              <i class="fas fa-cube text-lavender"></i>
              Block #${block.index}
              <span class="badge ${typeClass} ml-2">${block.record_type}</span>
            </div>
            <div class="text-muted text-xs">
              <i class="far fa-clock mr-1"></i>${block.timestamp} UTC
            </div>
          </div>

          <div class="block-body my-3">
            <div class="row align-items-center">
              <div class="col-md-8">
                <div class="bg-light p-3 rounded text-sm font-monospace" style="max-height: 110px; overflow-y: auto; background-color: var(--light-lavender) !important;">
                  <pre class="mb-0 text-dark" style="font-size: 0.78rem;">${this.escapeHtml(dataStr)}</pre>
                </div>
              </div>
              <div class="col-md-4 text-right">
                <button class="btn btn-outline btn-sm mt-2 mt-md-0" onclick="LedgerUI.showBlockModal(${block.index})">
                  <i class="fas fa-search-plus"></i> View Raw JSON
                </button>
                <button class="btn btn-danger btn-sm mt-2 ml-1" onclick="LedgerUI.triggerTamperDemo(${block.index})" title="Simulate database tampering to test audit verification">
                  <i class="fas fa-bug"></i> Tamper Block
                </button>
              </div>
            </div>
          </div>

          <div class="block-footer d-flex flex-wrap align-items-center justify-content-between text-xs pt-2 border-top">
            <div class="mb-1">
              <strong class="text-muted">Previous Hash:</strong>
              <span class="block-hash-pill" title="${block.previous_hash}">${block.previous_hash.substring(0, 18)}...</span>
            </div>
            <div class="mb-1">
              <strong class="text-muted">Block Hash (SHA-256):</strong>
              <span class="block-hash-pill ${isTampered ? 'bg-danger text-white' : ''}" title="${block.block_hash}">
                ${block.block_hash.substring(0, 22)}...
              </span>
            </div>
          </div>
        </div>
      `;

      if (index < blocks.length - 1) {
        html += `<div class="chain-connector"></div>`;
      }
    });

    container.innerHTML = html;
  },

  async verifyIntegrity() {
    const btn = document.getElementById('verify-ledger-btn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Recalculating Hashes...';
    }

    try {
      const res = await fetch('/api/ledger/verify');
      const data = await res.json();
      this.lastVerificationResult = data;

      const banner = document.getElementById('ledger-verification-banner');
      const tamperedIndices = (data.tampered_blocks || []).map(b => b.index);

      // Re-render chain highlighting tampered blocks if any
      this.renderChain(this.currentBlocks, tamperedIndices);

      if (banner) {
        if (data.is_valid) {
          banner.className = 'ledger-status-banner valid';
          banner.innerHTML = `
            <div class="status-left">
              <div class="status-shield-icon"><i class="fas fa-shield-alt text-success"></i></div>
              <div>
                <h3 class="mb-1 text-success"><i class="fas fa-check-circle mr-1"></i> Ledger Integrity Verified (100% Valid)</h3>
                <p class="mb-0 text-muted">All ${data.total_blocks} blocks sequentially calculated via SHA-256 without any hash mismatch or chain breaks.</p>
              </div>
            </div>
            <div>
              <span class="badge badge-success p-2">Verified at ${data.verified_at}</span>
            </div>
          `;
          App.showToast('Ledger verification successful! Zero tampering detected.', 'success');
        } else {
          banner.className = 'ledger-status-banner tampered';
          banner.innerHTML = `
            <div class="status-left">
              <div class="status-shield-icon" style="background:#FFCDD2; color:#C62828;"><i class="fas fa-exclamation-triangle"></i></div>
              <div>
                <h3 class="mb-1 text-danger"><i class="fas fa-times-circle mr-1"></i> INTEGRITY ALERT: ${data.tamper_count} Block(s) Tampered!</h3>
                <p class="mb-0 text-danger font-weight-bold">Unauthorized modifications detected in blocks: ${tamperedIndices.map(i => '#' + i).join(', ')}</p>
              </div>
            </div>
            <div>
              ${Auth.hasRole('admin') ? `
                <button class="btn btn-success btn-sm" onclick="LedgerUI.repairLedger()">
                  <i class="fas fa-wrench mr-1"></i> Repair Ledger Hashes
                </button>
              ` : ''}
            </div>
          `;
          App.showToast(`Integrity Alert: ${data.tamper_count} tampered block(s) detected!`, 'error');
        }
      }
    } catch (err) {
      console.error('Verification failed:', err);
      App.showToast('Verification failed to execute', 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-shield-alt mr-2"></i> Verify Ledger Integrity';
      }
    }
  },

  async triggerTamperDemo(blockIndex) {
    if (!confirm(`SIMULATE FRAUD: Are you sure you want to simulate payload tampering on Block #${blockIndex}? This tests live SHA-256 fraud detection for reviewers.`)) {
      return;
    }

    try {
      const res = await fetch('/api/ledger/tamper-demo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ block_index: blockIndex, note: 'Simulated Fraudulent Modification' })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Tamper failed');

      App.showToast(data.message, 'warning');
      await this.loadLedger();
      await this.verifyIntegrity();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  async repairLedger() {
    try {
      const res = await fetch('/api/ledger/repair-demo', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Repair failed');

      App.showToast(data.message, 'success');
      await this.loadLedger();
      await this.verifyIntegrity();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  showBlockModal(blockIndex) {
    const block = this.currentBlocks.find(b => b.index === blockIndex);
    if (!block) return;

    const modalBody = document.getElementById('block-details-modal-body');
    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-group">
          <label>Block Index & Record Type</label>
          <input type="text" class="form-control" value="Block #${block.index} (${block.record_type})" readonly>
        </div>
        <div class="form-group">
          <label>Timestamp</label>
          <input type="text" class="form-control" value="${block.timestamp}" readonly>
        </div>
        <div class="form-group">
          <label>Previous Hash</label>
          <input type="text" class="form-control font-monospace text-xs" value="${block.previous_hash}" readonly>
        </div>
        <div class="form-group">
          <label>Block SHA-256 Hash</label>
          <input type="text" class="form-control font-monospace text-xs" value="${block.block_hash}" readonly>
        </div>
        <div class="form-group">
          <label>JSON Data Payload</label>
          <textarea class="form-control font-monospace text-xs" rows="8" readonly>${JSON.stringify(block.data, null, 2)}</textarea>
        </div>
      `;
    }
    App.openModal('block-details-modal');
  },

  escapeHtml(str) {
    return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
};
