/* ==========================================================================
   CRUD Modules & UI Renderers (Donors, Donations, Inventory, Beneficiaries, Distributions)
   ========================================================================== */

// --- PUBLIC LANDING UI ---
const PublicLandingUI = {
  async loadPublicImpact() {
    try {
      const res = await fetch('/api/public/impact');
      const data = await res.json();
      const s = data.impact_summary;

      const publicMetrics = {
        'pub-total-donations': s.total_donations.toLocaleString(),
        'pub-total-inventory': s.total_inventory_items.toLocaleString(),
        'pub-total-beneficiaries': s.total_beneficiaries.toLocaleString(),
        'pub-total-distributions': s.total_distributions.toLocaleString(),
        'dash-monetary-val': `₹${s.total_monetary_donated.toLocaleString('en-IN')}`,
        'dash-ledger-blocks': `${s.ledger_blocks_count} Blocks`
      };

      Object.entries(publicMetrics).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
      });

      const badge = document.getElementById('pub-ledger-badge');
      if (badge) {
        if (s.ledger_integrity.is_valid) {
          badge.className = 'badge badge-success p-2 font-weight-bold';
          badge.innerHTML = '<i class="fas fa-shield-alt mr-1"></i> Ledger Verified 100% Immutable';
        } else {
          badge.className = 'badge badge-danger p-2 font-weight-bold';
          badge.innerHTML = '<i class="fas fa-exclamation-triangle mr-1"></i> Integrity Warning';
        }
      }
    } catch (err) {
      console.error('Failed to load public impact stats:', err);
    }
  }
};

// --- DONORS MODULE ---
const DonorsUI = {
  async loadDonors(search = '') {
    try {
      const res = await fetch(`/api/donors?search=${encodeURIComponent(search)}`);
      const data = await res.json();
      this.renderTable(data.donors || []);
    } catch (err) {
      App.showToast('Failed to load donors list', 'error');
    }
  },

  renderTable(donors) {
    const tbody = document.getElementById('donors-table-body');
    if (!tbody) return;

    if (donors.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted p-4">No donor records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = donors.map(d => `
      <tr>
        <td><strong>${App.escapeHtml(d.name)}</strong></td>
        <td>${App.escapeHtml(d.email)}</td>
        <td>${App.escapeHtml(d.phone || 'N/A')}</td>
        <td><span class="badge badge-lavender">${App.escapeHtml(d.preferred_causes)}</span></td>
        <td><strong class="text-success">₹${d.total_donated.toLocaleString('en-IN')}</strong></td>
        <td><span class="badge badge-info">${d.donation_count} Donations</span></td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="DonorsUI.viewDonor(${d.id})"><i class="fas fa-eye"></i> Profile</button>
        </td>
      </tr>
    `).join('');
  },

  async handleCreate(e) {
    e.preventDefault();
    const form = e.target;
    const payload = {
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      address: form.address.value.trim(),
      preferred_causes: form.preferred_causes.value.trim()
    };

    try {
      const res = await fetch('/api/donors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.status === 409 && data.require_force) {
        // Handle fuzzy duplicate warning!
        if (confirm(`DUPLICATE WARNING: A similar donor "${data.duplicates[0].donor.name}" already exists (${data.duplicates[0].reasons.join(', ')}). Do you still want to create this new profile?`)) {
          payload.force = true;
          const forceRes = await fetch('/api/donors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const forceData = await forceRes.json();
          App.showToast(forceData.message, 'success');
          App.closeModal('add-donor-modal');
          form.reset();
          this.loadDonors();
          PublicLandingUI.loadPublicImpact();
        }
        return;
      }

      if (!res.ok) throw new Error(data.error || 'Failed to create donor');

      App.showToast(data.message, 'success');
      App.closeModal('add-donor-modal');
      form.reset();
      this.loadDonors();
      PublicLandingUI.loadPublicImpact();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  async viewDonor(id) {
    try {
      const res = await fetch(`/api/donors/${id}`);
      const data = await res.json();
      const d = data.donor;

      const body = document.getElementById('donor-profile-modal-body');
      body.innerHTML = `
        <div class="row">
          <div class="col-md-6">
            <h4 class="mb-1">${App.escapeHtml(d.name)}</h4>
            <p class="text-muted text-sm">${App.escapeHtml(d.email)} | ${App.escapeHtml(d.phone)}</p>
            <p><strong>Address:</strong> ${App.escapeHtml(d.address || 'Not provided')}</p>
            <p><strong>Preferred Causes:</strong> ${App.escapeHtml(d.preferred_causes)}</p>
          </div>
          <div class="col-md-6 text-right">
            <div class="p-3 bg-light rounded text-center" style="background-color: var(--light-lavender) !important;">
              <small class="text-muted text-uppercase">Lifetime Cumulative Donations</small>
              <h2 class="text-success mt-1">₹${d.total_donated.toLocaleString('en-IN')}</h2>
              <span class="badge badge-lavender">${d.donation_count} Total Contributions</span>
            </div>
          </div>
        </div>
        <div class="text-right mb-3">
          <button class="btn btn-primary" onclick="DonationsUI.openDonationModal(${d.id})">
            <i class="fas fa-plus-circle mr-1"></i> Add Donation Made
          </button>
        </div>
        <hr>
        <h5 class="mb-3">Donation History</h5>
        <div class="table-responsive">
          <table class="custom-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Category</th>
                <th>Value</th>
                <th>Status</th>
                <th>Ledger Hash</th>
              </tr>
            </thead>
            <tbody>
              ${d.donations.map(don => `
                <tr>
                  <td>${don.date}</td>
                  <td>${App.escapeHtml(don.category)}</td>
                  <td><strong>${don.type === 'Monetary' ? '₹' + don.amount.toLocaleString('en-IN') : don.quantity + ' ' + don.unit}</strong></td>
                  <td>
                    <span class="badge" style="${don.status === 'Payment Successful' ? 'background:#e6f4ea;color:#137333;font-weight:700;border:1px solid #ceead6;' : 'background:var(--light-lavender);color:var(--deep-accent);'}">
                      ${don.status === 'Payment Successful' ? '<i class="fas fa-check-circle mr-1"></i> Payment Successful' : App.escapeHtml(don.status || 'Verified')}
                    </span>
                  </td>
                  <td>
                    ${don.product_photo ? `<a href="/static/${don.product_photo}" target="_blank">Product photo</a>` : ''}
                    ${don.payment_screenshot ? `<a href="/static/${don.payment_screenshot}" target="_blank">Payment proof</a>` : ''}
                    <span class="block-hash-pill" title="${don.block_hash}">${don.block_hash.substring(0, 12)}...</span>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
      App.openModal('donor-profile-modal');
    } catch (err) {
      App.showToast('Could not load donor profile', 'error');
    }
  },

  openDonationForm(donorId) {
    App.closeModal('donor-profile-modal');
    DonationsUI.openDonationModal(donorId);
  }
};

// --- DONATIONS MODULE ---
const DonationsUI = {
  pollTimer: null,
  cachedDonations: [],

  handleCategoryChange(category) {
    const monetaryGroup = document.getElementById('monetary-group');
    const inkindGroup = document.getElementById('inkind-group');
    const isMoney = category === 'Money';

    if (monetaryGroup) monetaryGroup.style.display = isMoney ? 'block' : 'none';
    if (inkindGroup) inkindGroup.style.display = isMoney ? 'none' : 'block';

    const phoneField = document.getElementById('donation-donor-phone');
    const addrField = document.getElementById('donation-donor-address');
    const itemField = document.getElementById('donation-item-name');
    const qtyField = document.getElementById('donation-quantity');
    const amtField = document.getElementById('donation-amount-input');

    if (amtField) amtField.required = isMoney;
    if (phoneField) phoneField.required = !isMoney;
    if (addrField) addrField.required = !isMoney;
    if (itemField) itemField.required = !isMoney;
    if (qtyField) qtyField.required = !isMoney;
  },

  setQuickAmount(amount) {
    const input = document.getElementById('donation-amount-input');
    if (input) {
      input.value = amount;
      input.focus();
    }
  },

  payViaGPay() {
    const amountInput = document.getElementById('donation-amount-input');
    const amount = parseFloat(amountInput ? amountInput.value : 0);
    if (!amount || amount <= 0) {
      App.showToast('Please enter a valid donation amount in ₹ to proceed with GPay.', 'error');
      if (amountInput) amountInput.focus();
      return;
    }

    const donorSelect = document.getElementById('log-donation-donor-select');
    let donorId = donorSelect && donorSelect.value ? donorSelect.value : '';
    const notesInput = document.getElementById('donation-notes-input');
    const notes = notesInput ? notesInput.value.trim() : '';

    App.closeModal('add-donation-modal');
    const query = new URLSearchParams();
    query.set('amount', amount);
    if (donorId) query.set('donor_id', donorId);
    if (notes) query.set('notes', notes);

    window.location.href = `/gpay?${query.toString()}`;
  },

  async openDonationModal(donorId = null, category = 'Goods') {
    const donorSelect = document.getElementById('log-donation-donor-select');
    const donorSection = document.getElementById('log-donation-donor-section');
    const donorNote = document.getElementById('donor-self-note');
    const phoneField = document.getElementById('donation-donor-phone');
    const addrField = document.getElementById('donation-donor-address');

    if (Auth.currentUser && Auth.currentUser.role === 'donor') {
      if (donorSection) donorSection.style.display = 'none';
      if (donorNote) donorNote.style.display = 'block';
      if (donorSelect) donorSelect.required = false;

      // Prefill donor contact info
      if (phoneField && Auth.currentUser.phone) {
        phoneField.value = Auth.currentUser.phone;
      }
      try {
        const dRes = await fetch('/api/donors');
        const dData = await dRes.json();
        const myDonor = (dData.donors || []).find(d => d.email === Auth.currentUser.email || d.user_id === Auth.currentUser.id);
        if (myDonor) {
          if (phoneField && myDonor.phone) phoneField.value = myDonor.phone;
          if (addrField && myDonor.address) addrField.value = myDonor.address;
        }
      } catch (err) {}
    } else if (donorId && donorSelect) {
      donorSelect.value = donorId;
      if (donorSection) donorSection.style.display = 'block';
      if (donorNote) donorNote.style.display = 'none';
    }

    const catSelect = document.getElementById('log-donation-category');
    if (catSelect) {
      catSelect.value = category;
    }
    this.handleCategoryChange(category);

    App.openModal('add-donation-modal');
  },

  async loadDonations() {
    if (!this.pollTimer) {
      this.pollTimer = setInterval(() => {
        if (App.currentView === 'donations' || App.currentView === 'dashboard') {
          this.loadDonations();
        }
      }, 7000);
    }
    try {
      const res = await fetch('/api/donations');
      const data = await res.json();
      this.cachedDonations = data.donations || [];
      this.renderTable(this.cachedDonations);
      this.renderDonorTrackingCards(this.cachedDonations);
    } catch (err) {
      App.showToast('Failed to load donations', 'error');
    }
  },

  renderTable(donations) {
    const tbody = document.getElementById('donations-table-body');
    if (!tbody) return;

    if (donations.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted p-4">No donation records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = donations.map(d => {
      const isRecent = App.recentDonationId && d.id === App.recentDonationId;
      const isSuccess = d.status === 'Payment Successful';
      const isGoods = d.type === 'In-Kind' || d.category !== 'Money';
      const task = d.volunteer_task;

      // Status badge and live volunteer status
      let statusHtml = '';
      if (isSuccess) {
        statusHtml = `<span class="badge" style="background:#e6f4ea;color:#137333;font-weight:700;border:1px solid #ceead6;padding:4px 10px;border-radius:12px;"><i class="fas fa-check-circle mr-1"></i> Payment Successful</span>`;
      } else if (isGoods) {
        const badgeClass = d.status === 'Received in Inventory' ? 'badge-success' : d.status === 'Pending Pickup' ? 'badge-warning' : 'badge-primary';
        statusHtml = `
          <div><span class="badge ${badgeClass}">${App.escapeHtml(d.status)}</span></div>
          ${task ? `
            <div class="text-xs text-muted mt-1">
              <i class="fas fa-user-check text-primary mr-1"></i>Vol: <strong>${App.escapeHtml(task.volunteer_name)}</strong>
              ${task.volunteer_phone ? `(<a href="tel:${App.escapeHtml(task.volunteer_phone)}">${App.escapeHtml(task.volunteer_phone)}</a>)` : ''}
            </div>
            ${task.location_sharing ? `
              <div class="mt-1">
                <span class="radar-live-badge"><span class="radar-dot"></span> Live GPS Active</span>
              </div>` : ''}
          ` : `<small class="text-muted d-block mt-1">Awaiting volunteer assignment</small>`}
        `;
      } else {
        statusHtml = `<span class="badge badge-success">${App.escapeHtml(d.status)}</span>`;
      }

      // Actions column
      const trackBtn = isGoods ? `
        <button class="btn btn-primary btn-sm" onclick="DonationsUI.openTrackPickupModal(${d.id})" title="Track Volunteer Pickup">
          <i class="fas fa-route mr-1"></i> Track
        </button>` : '';

      return `
      <tr style="${isRecent ? 'background-color: #f0fdf4; border-left: 4px solid #137333; transition: all 0.5s ease;' : ''}">
        <td><strong>#REC-${d.id.toString().padStart(6, '0')}</strong></td>
        <td>
          <div class="font-weight-bold">${App.escapeHtml(d.donor_name)}</div>
          ${d.donor_phone ? `<div class="text-xs text-muted"><i class="fas fa-phone-alt mr-1"></i>${App.escapeHtml(d.donor_phone)}</div>` : ''}
          ${isGoods && d.donor_address ? `<div class="text-xs text-muted" title="${App.escapeHtml(d.donor_address)}"><i class="fas fa-map-marker-alt text-danger mr-1"></i>${App.escapeHtml(d.donor_address.length > 30 ? d.donor_address.slice(0, 30) + '...' : d.donor_address)}</div>` : ''}
        </td>
        <td>
          <span class="badge badge-lavender">${App.escapeHtml(d.category)}</span>
          ${d.item_name ? `<div class="text-xs font-weight-bold text-dark mt-1">${App.escapeHtml(d.item_name)}</div>` : ''}
        </td>
        <td><strong class="${d.type === 'Monetary' ? 'text-success' : 'text-primary'}">${d.type === 'Monetary' ? '₹' + d.amount.toLocaleString('en-IN') : d.quantity + ' ' + d.unit}</strong></td>
        <td>${statusHtml}</td>
        <td>
          <div class="mb-1">
            <span class="badge ${d.evidence_status === 'Valid' ? 'badge-success' : d.evidence_status === 'Tampered' ? 'badge-danger' : 'badge-warning'}">${d.evidence_status || 'Pending Review'}</span>
          </div>
          ${d.product_photo ? `<a href="/static/${d.product_photo}" target="_blank"><i class="fas fa-image mr-1"></i>Photo</a>` : ''}
          ${d.payment_screenshot ? `<a href="/static/${d.payment_screenshot}" target="_blank"><i class="fas fa-receipt mr-1"></i>Payment proof</a>` : ''}
          ${Auth.currentUser && Auth.currentUser.role === 'admin' ? `
            <div class="mt-1">
              <button class="btn btn-outline btn-sm" onclick="DonationsUI.reviewEvidence(${d.id}, 'Valid')"><i class="fas fa-check"></i> Valid</button>
              <button class="btn btn-outline btn-sm" onclick="DonationsUI.reviewEvidence(${d.id}, 'Tampered')"><i class="fas fa-exclamation-triangle"></i> Tampered</button>
            </div>` : ''}
        </td>
        <td>
          <div class="d-flex gap-1 flex-wrap">
            ${trackBtn}
            <button class="btn btn-outline btn-sm" onclick="DonationsUI.showReceipt(${d.id})">
              <i class="fas fa-file-invoice"></i> Receipt
            </button>
          </div>
        </td>
      </tr>
    `}).join('');
  },

  renderDonorTrackingCards(donations) {
    const container = document.getElementById('donor-goods-tracking-section');
    if (!container) return;

    if (!Auth.currentUser || Auth.currentUser.role !== 'donor') {
      container.style.display = 'none';
      return;
    }

    const activeGoodsDonations = donations.filter(d => (d.type === 'In-Kind' || d.category !== 'Money'));
    if (!activeGoodsDonations.length) {
      container.style.display = 'none';
      return;
    }

    container.style.display = 'block';
    container.innerHTML = `
      <div class="goods-tracker-card" style="background: linear-gradient(180deg, #ffffff 0%, #faf8ff 100%); border-left: 5px solid var(--deep-accent);">
        <div class="goods-tracker-header">
          <div>
            <h3 class="mb-1" style="color:var(--deep-accent);font-size:1.2rem;">
              <i class="fas fa-route text-primary mr-2"></i> Real-Time Goods Pickup &amp; Volunteer Tracker
            </h3>
            <p class="text-xs text-muted mb-0">Track the live progress of your goods donation and the volunteer assigned to pick it up.</p>
          </div>
          <button class="btn btn-outline btn-sm" onclick="DonationsUI.loadDonations()">
            <i class="fas fa-sync-alt mr-1"></i> Refresh Tracker
          </button>
        </div>
        ${activeGoodsDonations.map(d => this.buildTrackingCardHtml(d)).join('')}
      </div>
    `;
  },

  buildTrackingCardHtml(d) {
    const task = d.volunteer_task;
    const currentStatus = task ? task.status : (d.status || 'Pending Pickup');

    // Milestones mapping
    // 1: Assigned, 2: Accepted, 3: At Donor's Location, 4: Picked Up, 5: Sent to Inventory
    const statusLevels = {
      'Pending Pickup': 0,
      'Assigned': 1,
      'Accepted': 2,
      'Pickup Accepted': 2,
      'On the Way': 2,
      'Volunteer On The Way': 2,
      "At Donor's Location": 3,
      'Volunteer At Donor Location': 3,
      'Picked Up': 4,
      'Goods Picked Up': 4,
      'Sent to Inventory': 5,
      'Returned': 5,
      'Received in Inventory': 5,
      'Completed': 5
    };
    const level = statusLevels[currentStatus] || (task ? 1 : 0);
    const progressPercent = Math.min(100, Math.max(5, (level / 5) * 100));

    const latestLoc = task && task.latest_location;
    const isLive = task && task.location_sharing && latestLoc;

    return `
      <div class="p-3 mb-3 bg-white rounded border" style="box-shadow:0 2px 8px rgba(0,0,0,0.04);">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
          <div>
            <strong style="font-size:1.05rem;color:var(--dark-text);">
              <i class="fas fa-box-open text-primary mr-1"></i> ${App.escapeHtml(d.item_name || d.category)}
            </strong>
            <span class="badge badge-lavender ml-2">${d.quantity} ${App.escapeHtml(d.unit)}</span>
            <span class="text-xs text-muted ml-2">#REC-${d.id.toString().padStart(6, '0')}</span>
          </div>
          <div>
            <span class="badge ${level >= 5 ? 'badge-success' : level > 0 ? 'badge-primary' : 'badge-warning'}" style="font-size:0.82rem;padding:6px 12px;">
              ${level >= 5 ? '<i class="fas fa-check-double mr-1"></i>' : '<i class="fas fa-clock mr-1"></i>'}
              ${App.escapeHtml(task ? task.status : d.status)}
            </span>
          </div>
        </div>

        <!-- 5-Step Visual Progress Stepper -->
        <div class="stepper-wrapper">
          <div class="stepper-progress-bar" style="width: ${progressPercent}%;"></div>
          <div class="step-node ${level >= 1 ? (level === 1 ? 'active' : 'completed') : ''}">
            <div class="step-circle">${level > 1 ? '<i class="fas fa-check"></i>' : '1'}</div>
            <div class="step-label">Volunteer Assigned</div>
          </div>
          <div class="step-node ${level >= 2 ? (level === 2 ? 'active' : 'completed') : ''}">
            <div class="step-circle">${level > 2 ? '<i class="fas fa-check"></i>' : '2'}</div>
            <div class="step-label">Task Accepted</div>
          </div>
          <div class="step-node ${level >= 3 ? (level === 3 ? 'active' : 'completed') : ''}">
            <div class="step-circle">${level > 3 ? '<i class="fas fa-check"></i>' : '3'}</div>
            <div class="step-label">At Donor's Location</div>
          </div>
          <div class="step-node ${level >= 4 ? (level === 4 ? 'active' : 'completed') : ''}">
            <div class="step-circle">${level > 4 ? '<i class="fas fa-check"></i>' : '4'}</div>
            <div class="step-label">Goods Picked Up</div>
          </div>
          <div class="step-node ${level >= 5 ? 'completed' : ''}">
            <div class="step-circle">${level >= 5 ? '<i class="fas fa-check"></i>' : '5'}</div>
            <div class="step-label">Sent to Inventory</div>
          </div>
        </div>

        <!-- Volunteer & Live Location Panel -->
        <div class="row mt-3 pt-2 border-top">
          <div class="col-md-6 mb-2">
            <small class="text-uppercase text-muted" style="font-size:0.72rem;letter-spacing:0.5px;">Assigned Volunteer Details</small>
            ${task ? `
              <div class="d-flex align-items-center mt-1">
                <div style="width:34px;height:34px;border-radius:50%;background:#e0e7ff;color:#4338ca;display:flex;align-items:center;justify-content:center;font-weight:700;margin-right:10px;">
                  ${App.escapeHtml((task.volunteer_name || 'V')[0])}
                </div>
                <div>
                  <div class="font-weight-bold" style="font-size:0.92rem;">${App.escapeHtml(task.volunteer_name)}</div>
                  ${task.volunteer_phone ? `
                    <div class="text-xs">
                      <a href="tel:${App.escapeHtml(task.volunteer_phone)}" class="text-primary font-weight-bold">
                        <i class="fas fa-phone-alt mr-1"></i>${App.escapeHtml(task.volunteer_phone)} (Call Volunteer)
                      </a>
                    </div>` : '<div class="text-xs text-muted">Phone not listed</div>'}
                </div>
              </div>` : `
              <div class="text-xs text-muted mt-1">
                <i class="fas fa-hourglass-half mr-1 text-warning"></i> NGO staff is assigning a volunteer for pickup.
              </div>`}
          </div>

          <div class="col-md-6 mb-2">
            <small class="text-uppercase text-muted" style="font-size:0.72rem;letter-spacing:0.5px;">Live GPS Tracking</small>
            ${isLive ? `
              <div class="mt-1">
                <div class="d-flex align-items-center gap-2 mb-1">
                  <span class="radar-live-badge"><span class="radar-dot"></span> Volunteer Location Live</span>
                  <small class="text-muted text-xs">Updated: ${latestLoc.captured_at}</small>
                </div>
                <a target="_blank" rel="noopener" href="https://maps.google.com/?q=${latestLoc.latitude},${latestLoc.longitude}" class="btn btn-sm btn-outline" style="border-radius:8px;">
                  <i class="fas fa-map-marked-alt text-danger mr-1"></i> Open Live Location on Google Maps
                </a>
              </div>` : (task ? `
              <div class="mt-1 text-xs text-muted">
                <i class="fas fa-satellite text-muted mr-1"></i> Volunteer has not activated live location yet. Coordinates will appear as soon as the volunteer shares them.
              </div>` : `
              <div class="mt-1 text-xs text-muted">
                Live location will be available once a volunteer accepts your task.
              </div>`)}
          </div>
        </div>

        ${d.donor_address ? `
          <div class="mt-2 pt-2 border-top text-xs text-muted">
            <i class="fas fa-home text-primary mr-1"></i><strong>Your Pickup Location:</strong> ${App.escapeHtml(d.donor_address)}
          </div>` : ''}
      </div>
    `;
  },

  openTrackPickupModal(donationId) {
    const d = this.cachedDonations.find(item => item.id === donationId);
    if (!d) {
      App.showToast('Donation details not found', 'error');
      return;
    }
    const body = document.getElementById('track-goods-modal-body');
    if (!body) return;
    body.innerHTML = this.buildTrackingCardHtml(d);
    App.openModal('track-goods-modal');
  },

  async reviewEvidence(id, evidenceStatus) {
    try {
      const res = await fetch(`/api/donations/${id}/evidence-status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evidence_status: evidenceStatus })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Evidence review failed');
      App.showToast(data.message, evidenceStatus === 'Valid' ? 'success' : 'error');
      this.loadDonations();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  async handleLogDonation(e) {
    e.preventDefault();
    const form = e.target;
    const payload = new FormData(form);
    if (form.donor_id && form.donor_id.value) payload.set('donor_id', form.donor_id.value);


    try {
      const res = await fetch('/api/donations', {
        method: 'POST',
        body: payload
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to record donation');

      App.showToast('Donation recorded & immutably sealed in blockchain ledger!', 'success');
      App.closeModal('add-donation-modal');
      form.reset();
      const donorSection = document.getElementById('log-donation-donor-section');
      const donorSelect = document.getElementById('log-donation-donor-select');
      if (donorSection && donorSelect && Auth.currentUser.role !== 'donor') {
        donorSection.style.display = 'block';
        donorSelect.required = true;
      }
      this.loadDonations();
      PublicLandingUI.loadPublicImpact();
      this.showReceipt(data.donation.id);
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  async showReceipt(id) {
    try {
      const res = await fetch(`/api/donations/${id}/receipt`);
      const data = await res.json();
      const r = data.receipt;

      const body = document.getElementById('receipt-modal-body');
      body.innerHTML = `
        <div class="receipt-box">
          <div class="receipt-watermark">NGO</div>
          <div class="d-flex justify-content-between align-items-center mb-3 border-bottom pb-3">
            <div>
              <h4 class="mb-0 text-lavender-dark"><i class="fas fa-heart text-danger mr-2"></i> NGO OFFICIAL RECEIPT</h4>
              <small class="text-muted">${r.issued_by}</small>
            </div>
            <div class="text-right">
              <span class="badge badge-success p-2">${r.receipt_number}</span>
              <div class="text-xs text-muted mt-1">${r.date}</div>
            </div>
          </div>

          <div class="row my-4">
            <div class="col-6">
              <small class="text-muted text-uppercase">Donor Information</small>
              <h5 class="mt-1 mb-0">${App.escapeHtml(r.donor_name)}</h5>
              <div class="text-sm text-muted">${App.escapeHtml(r.donor_email)}</div>
            </div>
            <div class="col-6 text-right">
              <small class="text-muted text-uppercase">Donation Summary</small>
              <h3 class="mt-1 text-success">${r.donation_type === 'Monetary' ? '₹' + parseFloat(r.amount).toLocaleString('en-IN') : r.amount + ' ' + r.unit}</h3>
              <span class="badge badge-lavender">${r.category} (${r.donation_type})</span>
            </div>
          </div>

          <div class="p-3 bg-light rounded text-xs border" style="background-color: var(--light-lavender) !important;">
            <div class="d-flex justify-content-between mb-1">
              <strong>BLOCKCHAIN LEDGER SEAL (SHA-256):</strong>
              <span class="text-success"><i class="fas fa-check-circle"></i> VERIFIED</span>
            </div>
            <div class="font-monospace text-break" style="word-break: break-all;">${r.block_hash}</div>
          </div>
          <div class="text-center mt-3 text-xs text-muted">
            <em>${r.verification_notice}</em>
          </div>
        </div>
        <div class="text-right mt-3">
          <button class="btn btn-outline btn-sm" onclick="window.print()"><i class="fas fa-print"></i> Print / Download PDF</button>
        </div>
      `;
      App.openModal('receipt-modal');
    } catch (err) {
      App.showToast('Could not load receipt', 'error');
    }
  }
};

// --- INVENTORY MODULE ---
const InventoryUI = {
  async loadInventory() {
    try {
      const res = await fetch('/api/inventory');
      const data = await res.json();
      this.renderTable(data.inventory || []);
    } catch (err) {
      App.showToast('Failed to load inventory stock', 'error');
    }
  },

  renderTable(items) {
    const tbody = document.getElementById('inventory-table-body');
    if (!tbody) return;

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted p-4">No inventory items found.</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map(i => `
      <tr>
        <td><span class="badge badge-lavender">${App.escapeHtml(i.category)}</span></td>
        <td><strong>${App.escapeHtml(i.name)}</strong></td>
        <td>
          <strong class="${i.is_low_stock ? 'text-danger' : 'text-dark'}">${i.quantity.toLocaleString()} ${i.unit}</strong>
        </td>
        <td>${i.low_stock_threshold} ${i.unit}</td>
        <td>
          ${i.is_low_stock ? 
            `<span class="badge badge-danger"><i class="fas fa-exclamation-triangle"></i> LOW STOCK</span>` : 
            `<span class="badge badge-success"><i class="fas fa-check"></i> IN STOCK</span>`
          }
        </td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="InventoryUI.showLogModal(${i.id})"><i class="fas fa-history"></i> Movement Log</button>
        </td>
      </tr>
    `).join('');
  },

  async handleAddStock(e) {
    e.preventDefault();
    const form = e.target;
    const payload = {
      name: form.name.value.trim(),
      category: form.category.value.trim(),
      quantity: parseFloat(form.quantity.value || 0),
      unit: form.unit.value.trim(),
      low_stock_threshold: parseFloat(form.low_stock_threshold.value || 10)
    };

    try {
      const res = await fetch('/api/inventory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to add inventory item');

      App.showToast('Inventory item added successfully', 'success');
      App.closeModal('add-inventory-modal');
      form.reset();
      this.loadInventory();
      PublicLandingUI.loadPublicImpact();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  async showLogModal(itemId) {
    try {
      const res = await fetch(`/api/inventory/movement-logs?item_id=${itemId}`);
      const data = await res.json();
      const logs = data.logs || [];

      const body = document.getElementById('inventory-logs-modal-body');
      body.innerHTML = `
        <div class="table-responsive">
          <table class="custom-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Type</th>
                <th>Item</th>
                <th>Quantity</th>
                <th>Reference</th>
              </tr>
            </thead>
            <tbody>
              ${logs.map(l => `
                <tr>
                  <td>${l.timestamp}</td>
                  <td><span class="badge ${l.movement_type === 'INBOUND' ? 'badge-success' : 'badge-warning'}">${l.movement_type}</span></td>
                  <td>${App.escapeHtml(l.item_name)}</td>
                  <td>${l.movement_type === 'OUTBOUND' ? '-' : '+'}${l.quantity}</td>
                  <td>${l.notes || l.reference_type}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
      App.openModal('inventory-logs-modal');
    } catch (err) {
      App.showToast('Could not load inventory movement logs', 'error');
    }
  }
};

// --- BENEFICIARIES MODULE ---
const BeneficiariesUI = {
  async loadBeneficiaries() {
    try {
      const selfService = document.getElementById('beneficiary-self-service');
      const staffView = document.getElementById('beneficiary-staff-view');
      const isBeneficiary = Auth.currentUser && Auth.currentUser.role === 'beneficiary';
      if (selfService) selfService.style.display = isBeneficiary ? '' : 'none';
      if (staffView) staffView.style.display = isBeneficiary ? 'none' : '';

      const res = await fetch('/api/beneficiaries');
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load beneficiaries');
      if (isBeneficiary) {
        const beneficiary = (data.beneficiaries || [])[0];
        if (!beneficiary) throw new Error('Your beneficiary profile has not been created. Contact NGO staff.');
        await this.renderSelfService(beneficiary);
        await this.loadAidRequests();
        return;
      }
      this.renderTable(data.beneficiaries || []);
      const reviewCard = document.getElementById('aid-request-review-card');
      const mayReview = Auth.hasRole('admin', 'staff');
      if (reviewCard) reviewCard.style.display = mayReview ? '' : 'none';
      if (mayReview) await this.loadAidRequests();
    } catch (err) {
      App.showToast(err.message || 'Failed to load beneficiaries', 'error');
    }
  },

  async renderSelfService(beneficiary) {
    const profile = document.getElementById('beneficiary-self-profile');
    const distributions = beneficiary.distributions || [];
    profile.innerHTML = `
      <div class="card-header"><h3 class="card-title">My Beneficiary Profile</h3></div>
      <div class="card-body">
        <h3>${App.escapeHtml(beneficiary.name)}</h3>
        <p><strong>Location:</strong> ${App.escapeHtml(beneficiary.location)}</p>
        <p><strong>Eligibility:</strong> ${App.escapeHtml(beneficiary.eligibility_category)}</p>
        <p><strong>Status:</strong> <span class="badge ${beneficiary.status === 'Active' ? 'badge-success' : 'badge-warning'}">${App.escapeHtml(beneficiary.status)}</span></p>
        <p><strong>Aid received:</strong> ${distributions.length} distribution(s)</p>
        <button class="btn btn-primary" onclick="document.getElementById('beneficiary-request-form').scrollIntoView({behavior:'smooth', block:'start'})">
          <i class="fas fa-hand-holding-heart mr-1"></i> Request Assistance
        </button>
        <h4 class="mt-3">Aid History</h4>
        ${distributions.length ? `
          <div class="table-responsive"><table class="custom-table">
            <thead><tr><th>Date</th><th>Location</th><th>Aid received</th><th>Status</th></tr></thead>
            <tbody>${distributions.map(distribution => `
              <tr>
                <td>${App.escapeHtml(distribution.date)}</td>
                <td>${App.escapeHtml(distribution.location)}</td>
                <td>${(distribution.items || []).map(item => `${item.quantity} ${App.escapeHtml(item.unit)} ${App.escapeHtml(item.item_name)}`).join(', ')}</td>
                <td>${App.escapeHtml(distribution.status)}</td>
              </tr>`).join('')}
            </tbody>
          </table></div>` : '<p class="text-muted">No aid distributions recorded yet.</p>'}
      </div>`;
  },

  async loadAidRequests() {
    const response = await fetch('/api/beneficiaries/requests');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not load assistance requests');
    const isBeneficiary = Auth.currentUser && Auth.currentUser.role === 'beneficiary';
    this.renderAidRequests(data.requests || [], isBeneficiary);
  },

  renderAidRequests(requests, isBeneficiary) {
    const container = document.getElementById(isBeneficiary ? 'beneficiary-my-requests' : 'beneficiary-request-queue');
    if (!container) return;
    if (!requests.length) {
      container.innerHTML = '<p class="text-muted">No assistance requests yet.</p>';
      return;
    }
    container.innerHTML = requests.map(aidRequest => `
      <article class="border-bottom py-3" style="${aidRequest.urgency === 'Urgent' ? 'background:#fff5f5;border-left:4px solid #e53935;padding-left:8px;' : aidRequest.urgency === 'High' ? 'background:#fffaf0;border-left:4px solid #fb8c00;padding-left:8px;' : ''}">
        <div class="d-flex justify-content-between align-items-center">
          <h4>${App.escapeHtml(aidRequest.category)}${isBeneficiary ? '' : ` from ${App.escapeHtml(aidRequest.beneficiary_name)}`}</h4>
          <span class="badge ${aidRequest.status === 'Fulfilled' ? 'badge-success' : 'badge-warning'}">${App.escapeHtml(aidRequest.status)}</span>
        </div>
        <p><strong>Urgency:</strong> ${App.escapeHtml(aidRequest.urgency)} | <strong>Submitted:</strong> ${App.escapeHtml(aidRequest.created_at)}</p>
        <p>${App.escapeHtml(aidRequest.description)}</p>
        ${aidRequest.staff_note ? `<p><strong>Staff update:</strong> ${App.escapeHtml(aidRequest.staff_note)}</p>` : ''}
        ${!isBeneficiary ? `
          <div class="d-flex gap-2 align-items-center flex-wrap">
            <select id="aid-request-status-${aidRequest.id}" class="form-control" style="width: auto;">
              ${['Under Review', 'Approved', 'Fulfilled', 'Declined'].map(status => `<option ${aidRequest.status === status ? 'selected' : ''}>${status}</option>`).join('')}
            </select>
            <input id="aid-request-note-${aidRequest.id}" class="form-control" style="flex:1;" maxlength="2000" placeholder="Response or staff note" value="${App.escapeHtml(aidRequest.staff_note)}">
            <button class="btn btn-primary btn-sm" onclick="BeneficiariesUI.updateAidRequest(${aidRequest.id})">Update</button>
            <button class="btn btn-outline btn-sm" onclick="BeneficiariesUI.dispatchForRequest(${aidRequest.beneficiary_id})"><i class="fas fa-truck-loading"></i> Assign Task</button>
          </div>` : ''}
      </article>`).join('');
  },

  dispatchForRequest(beneficiaryId) {
    App.navigateTo('volunteer-tasks');
    setTimeout(() => {
      const taskTypeSelect = document.querySelector('#volunteer-task-form [name="task_type"]');
      if (taskTypeSelect) {
        taskTypeSelect.value = 'delivery';
        VolunteerTasksUI.toggleTaskType('delivery');
      }
      const benSelect = document.getElementById('volunteer-beneficiary-select');
      if (benSelect) benSelect.value = beneficiaryId;
    }, 150);
  },

  async submitAidRequest(event) {
    event.preventDefault();
    const form = event.target;
    try {
      const response = await fetch('/api/beneficiaries/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: form.category.value,
          urgency: form.urgency.value,
          description: form.description.value.trim()
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not submit assistance request');
      App.showToast(data.message, 'success');
      form.reset();
      await this.loadAidRequests();
    } catch (error) {
      App.showToast(error.message, 'error');
    }
  },

  async updateAidRequest(requestId) {
    try {
      const response = await fetch(`/api/beneficiaries/requests/${requestId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: document.getElementById(`aid-request-status-${requestId}`).value,
          staff_note: document.getElementById(`aid-request-note-${requestId}`).value.trim()
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not update assistance request');
      App.showToast(data.message, 'success');
      await this.loadAidRequests();
    } catch (error) {
      App.showToast(error.message, 'error');
    }
  },

  renderTable(beneficiaries) {
    const tbody = document.getElementById('beneficiaries-table-body');
    if (!tbody) return;

    if (beneficiaries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted p-4">No beneficiary records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = beneficiaries.map(b => `
      <tr>
        <td><strong>${App.escapeHtml(b.name)}</strong></td>
        <td>${App.escapeHtml(b.location)}</td>
        <td><span class="badge badge-lavender">${App.escapeHtml(b.eligibility_category)}</span></td>
        <td><span class="badge badge-success">${b.status}</span></td>
        <td><span class="badge badge-info">${b.distributions_count} Received</span></td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="BeneficiariesUI.viewProfile(${b.id})"><i class="fas fa-user-check"></i> History</button>
        </td>
      </tr>
    `).join('');
  },

  async handleRegister(e) {
    e.preventDefault();
    const form = e.target;
    const payload = {
      name: form.name.value.trim(),
      contact: form.contact.value.trim(),
      email: form.email.value.trim(),
      location: form.location.value.trim(),
      eligibility_category: form.eligibility_category.value.trim(),
      notes: form.notes.value.trim()
    };

    try {
      const res = await fetch('/api/beneficiaries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Registration failed');

      App.showToast('Beneficiary registered successfully', 'success');
      App.closeModal('add-beneficiary-modal');
      form.reset();
      this.loadBeneficiaries();
      PublicLandingUI.loadPublicImpact();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  async viewProfile(id) {
    try {
      const res = await fetch(`/api/beneficiaries/${id}`);
      const data = await res.json();
      const b = data.beneficiary;

      const body = document.getElementById('beneficiary-profile-modal-body');
      body.innerHTML = `
        <h4>${App.escapeHtml(b.name)}</h4>
        <p class="text-muted">${App.escapeHtml(b.location)} | ${App.escapeHtml(b.contact || 'No phone')}</p>
        <span class="badge badge-lavender mb-3">${b.eligibility_category}</span>

        <h5 class="mt-4 mb-2">Aid Distribution History</h5>
        <div class="table-responsive">
          <table class="custom-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Donor</th>
                <th>Location</th>
                <th>Dispatched Items</th>
                <th>Amount</th>
                <th>Ledger Hash</th>
              </tr>
            </thead>
            <tbody>
              ${b.distributions.map(d => `
                <tr>
                  <td>${d.date}</td>
                   <td>${App.escapeHtml(d.donor_name || 'N/A')}</td>
                  <td>${App.escapeHtml(d.location)}</td>
                  <td>${d.items.map(i => `${i.quantity} ${i.unit} ${i.item_name}`).join(', ')}</td>
                   <td>${d.amount > 0 ? '₹' + Number(d.amount).toLocaleString('en-IN') : '-'}</td>
                  <td><span class="block-hash-pill" title="${d.block_hash}">${d.block_hash.substring(0, 12)}...</span></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
      App.openModal('beneficiary-profile-modal');
    } catch (err) {
      App.showToast('Could not load beneficiary profile', 'error');
    }
  }
};

// --- DISTRIBUTIONS MODULE ---
const DistributionsUI = {
  async loadDistributions() {
    try {
      const res = await fetch('/api/distributions');
      const data = await res.json();
      this.renderTable(data.distributions || []);
    } catch (err) {
      App.showToast('Failed to load distributions', 'error');
    }
  },

  renderTable(distributions) {
    const tbody = document.getElementById('distributions-table-body');
    if (!tbody) return;

    if (distributions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted p-4">No distribution events recorded.</td></tr>`;
      return;
    }

    tbody.innerHTML = distributions.map(d => `
      <tr>
        <td><strong>#DIST-${d.id.toString().padStart(6, '0')}</strong></td>
        <td>${App.escapeHtml(d.beneficiary_name)}</td>
        <td>${App.escapeHtml(d.location)}</td>
        <td>${d.items.map(i => `<span class="badge badge-lavender mr-1">${i.quantity} ${i.unit} ${i.item_name}</span>`).join('')}${d.amount > 0 ? `<span class="badge badge-success mr-1">₹${Number(d.amount).toLocaleString('en-IN')} cash</span>` : ''}</td>
        <td><span class="badge badge-success">${d.status}</span></td>
        <td>
          ${d.blockchain_transaction_hash
            ? `<span class="badge badge-success">Blockchain Recorded</span><br><span class="block-hash-pill" title="${d.blockchain_transaction_hash}">${d.blockchain_transaction_hash.substring(0, 12)}...</span>`
            : `<span class="badge badge-warning">Local Ledger Only</span><br><span class="block-hash-pill" title="${d.block_hash}">${d.block_hash.substring(0, 12)}...</span>`}
        </td>
      </tr>
    `).join('');
  },

  async openDispatchModal() {
    try {
      // Load beneficiaries dropdown and inventory dropdown
      const [benRes, invRes] = await Promise.all([
        fetch('/api/beneficiaries'),
        fetch('/api/inventory')
      ]);

      const benData = await benRes.json();
      const invData = await invRes.json();

      const benSelect = document.getElementById('dispatch-beneficiary-select');
      benSelect.innerHTML = (benData.beneficiaries || []).map(b => 
        `<option value="${b.id}">${App.escapeHtml(b.name)} (${App.escapeHtml(b.eligibility_category)} - ${App.escapeHtml(b.location)})</option>`
      ).join('');

      const invContainer = document.getElementById('dispatch-inventory-items-container');
      invContainer.innerHTML = (invData.inventory || []).map(i => `
        <div class="row align-items-center mb-2 p-2 border-bottom">
          <div class="col-7">
            <strong>${App.escapeHtml(i.name)}</strong>
            <div class="text-xs text-muted">Stock: ${i.quantity} ${i.unit} available</div>
          </div>
          <div class="col-5">
            <input type="number" step="any" min="0" max="${i.quantity}" class="form-control dispatch-item-qty" data-item-id="${i.id}" placeholder="Qty (max ${i.quantity})">
          </div>
        </div>
      `).join('');

      App.openModal('dispatch-modal');
    } catch (err) {
      App.showToast('Could not prepare dispatch form', 'error');
    }
  },

  async handleDispatchSubmit(e) {
    e.preventDefault();
    const benId = document.getElementById('dispatch-beneficiary-select').value;
    const location = document.getElementById('dispatch-location-input').value.trim();
    const notes = document.getElementById('dispatch-notes-input').value.trim();
    const amount = parseFloat(document.getElementById('dispatch-amount-input')?.value || 0) || 0;

    const itemInputs = document.querySelectorAll('.dispatch-item-qty');
    const items = [];
    itemInputs.forEach(input => {
      const qty = parseFloat(input.value || 0);
      if (qty > 0) {
        items.push({
          inventory_item_id: parseInt(input.getAttribute('data-item-id')),
          quantity: qty
        });
      }
    });

    if (items.length === 0 && amount <= 0) {
      App.showToast('Please specify a quantity for at least one item or a monetary amount.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/distributions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          beneficiary_id: parseInt(benId),
          location: location,
          notes: notes,
          items: items,
          amount: amount
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Dispatch failed');

      App.showToast('Distribution completed & immutably sealed in ledger!', 'success');
      if (data.blockchain_transaction_hash) {
        App.showToast(`Blockchain Recorded: ${data.blockchain_transaction_hash}`, 'success');
      }
      App.closeModal('dispatch-modal');
      this.loadDistributions();
      PublicLandingUI.loadPublicImpact();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  }
};

const VolunteerTasksUI = {
  locationWatches: {},
  locationStarted: {},
  lastLocationSentAt: {},
  pollTimer: null,

  async loadPendingGoodsDonations() {
    const card = document.getElementById('staff-pending-goods-card');
    const tbody = document.getElementById('staff-pending-goods-table-body');
    if (!card || !tbody) return;

    if (!Auth.hasRole('staff')) {
      card.style.display = 'none';
      return;
    }
    card.style.display = 'block';

    try {
      const [pendingRes, volRes] = await Promise.all([
        fetch('/api/volunteer-tasks/pending-donations'),
        fetch('/api/volunteer-tasks/volunteers')
      ]);
      const pendingData = await pendingRes.json();
      const volData = await volRes.json();

      const pending = pendingData.pending_goods_donations || [];
      const volunteers = volData.volunteers || [];

      if (!pending.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted p-4"><i class="fas fa-check-circle text-success mr-2"></i> All goods donations have been assigned to volunteers.</td></tr>`;
        return;
      }

      const volOptions = volunteers.map(v =>
        `<option value="${v.id}">${App.escapeHtml(v.name)} (${App.escapeHtml(v.email)})</option>`
      ).join('');

      tbody.innerHTML = pending.map(d => `
        <tr id="pending-goods-row-${d.id}">
          <td>
            <strong>${App.escapeHtml(d.donor_name || 'Anonymous Donor')}</strong>
            <div class="text-xs text-muted">Receipt #REC-${d.id.toString().padStart(6, '0')}</div>
          </td>
          <td>
            ${d.donor_phone ? `
              <a href="tel:${App.escapeHtml(d.donor_phone)}" class="text-primary font-weight-bold">
                <i class="fas fa-phone-alt mr-1"></i>${App.escapeHtml(d.donor_phone)}
              </a>` : '<span class="text-muted text-xs">No phone provided</span>'}
          </td>
          <td>
            ${d.donor_address ? `
              <div>
                <i class="fas fa-map-marker-alt text-danger mr-1"></i>${App.escapeHtml(d.donor_address)}
                <br>
                <a target="_blank" rel="noopener" href="https://maps.google.com/?q=${encodeURIComponent(d.donor_address)}" class="text-xs text-primary font-weight-bold">
                  Open Directions
                </a>
              </div>` : '<span class="text-muted text-xs">No address provided</span>'}
          </td>
          <td>
            <strong>${App.escapeHtml(d.item_name || d.category)}</strong>
            <div><span class="badge badge-lavender">${d.quantity} ${App.escapeHtml(d.unit)}</span></div>
          </td>
          <td>
            <small class="text-muted">${App.escapeHtml(d.notes || 'None')}</small>
          </td>
          <td>
            <div class="d-flex gap-2 align-items-center">
              <select id="assign-vol-select-${d.id}" class="form-control form-control-sm" style="max-width:180px;">
                ${volOptions ? volOptions : '<option value="">No volunteers</option>'}
              </select>
              <button class="btn btn-primary btn-sm" onclick="VolunteerTasksUI.assignDirectFromDonation(${d.id})">
                <i class="fas fa-user-plus mr-1"></i> Assign
              </button>
            </div>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger p-3">${App.escapeHtml(err.message || 'Failed to load pending donations')}</td></tr>`;
    }
  },

  async assignDirectFromDonation(donationId) {
    const select = document.getElementById(`assign-vol-select-${donationId}`);
    if (!select || !select.value) {
      App.showToast('Please select a volunteer to assign.', 'warning');
      return;
    }
    const volunteerId = Number(select.value);

    try {
      const res = await fetch('/api/volunteer-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'pickup',
          donation_id: donationId,
          volunteer_id: volunteerId
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Assignment failed');

      App.showToast(data.message || 'Volunteer assigned successfully!', 'success');
      this.loadPendingGoodsDonations();
      this.loadTasks();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  quickAssignFromDonation(donationId) {
    App.navigateTo('volunteer-tasks');
    setTimeout(() => {
      const row = document.getElementById(`pending-goods-row-${donationId}`);
      if (row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.style.backgroundColor = '#fbf7ff';
        setTimeout(() => row.style.backgroundColor = '', 2000);
      }
      const select = document.getElementById(`assign-vol-select-${donationId}`);
      if (select) select.focus();
    }, 400);
  },

  async loadAssignmentOptions() {
    const assignmentPanel = document.getElementById('volunteer-task-assignment');
    if (!assignmentPanel || !Auth.hasRole('staff')) return;
    assignmentPanel.style.display = '';

    try {
      const [volunteerResponse, donorResponse, beneficiaryResponse, inventoryResponse] = await Promise.all([
        fetch('/api/volunteer-tasks/volunteers'),
        fetch('/api/donors'),
        fetch('/api/beneficiaries'),
        fetch('/api/inventory')
      ]);
      const [volunteerData, donorData, beneficiaryData, inventoryData] = await Promise.all([
        volunteerResponse.json(), donorResponse.json(), beneficiaryResponse.json(), inventoryResponse.json()
      ]);
      if (!volunteerResponse.ok) throw new Error(volunteerData.error || 'Could not load volunteers');

      document.getElementById('volunteer-select').innerHTML = (volunteerData.volunteers || [])
        .map(volunteer => `<option value="${volunteer.id}">${App.escapeHtml(volunteer.name)} (${App.escapeHtml(volunteer.email)})</option>`).join('');
      document.getElementById('volunteer-donor-select').innerHTML = (donorData.donors || [])
        .map(donor => `<option value="${donor.id}">${App.escapeHtml(donor.name)}</option>`).join('');
      document.getElementById('volunteer-beneficiary-select').innerHTML = (beneficiaryData.beneficiaries || [])
        .map(beneficiary => `<option value="${beneficiary.id}">${App.escapeHtml(beneficiary.name)} (${App.escapeHtml(beneficiary.location)})</option>`).join('');
      document.getElementById('volunteer-inventory-select').innerHTML = (inventoryData.inventory || [])
        .map(item => `<option value="${item.id}" data-available="${item.quantity}">${App.escapeHtml(item.name)} (${item.quantity} ${App.escapeHtml(item.unit)})</option>`).join('');
    } catch (error) {
      App.showToast(error.message || 'Could not load task assignment options', 'error');
    }
  },

  toggleTaskType(taskType) {
    const isPickup = taskType === 'pickup';
    document.getElementById('volunteer-pickup-fields').style.display = isPickup ? '' : 'none';
    document.getElementById('volunteer-delivery-fields').style.display = isPickup ? 'none' : '';
    ['donor_id', 'item_name', 'category', 'expected_quantity', 'unit'].forEach(fieldName => {
      const field = document.querySelector(`#volunteer-task-form [name="${fieldName}"]`);
      if (field) {
        field.disabled = !isPickup;
        field.required = isPickup && fieldName !== 'unit';
      }
    });
    ['beneficiary_id', 'inventory_item_id', 'delivery_quantity'].forEach(fieldName => {
      const field = document.querySelector(`#volunteer-task-form [name="${fieldName}"]`);
      if (field) {
        field.disabled = isPickup;
        field.required = !isPickup;
      }
    });
  },

  async assignTask(event) {
    event.preventDefault();
    const form = event.target;
    const payload = {
      volunteer_id: Number(form.volunteer_id.value),
      task_type: form.task_type.value,
      notes: form.notes.value.trim()
    };
    if (payload.task_type === 'pickup') {
      payload.donor_id = Number(form.donor_id.value);
      payload.item_name = form.item_name.value.trim();
      payload.category = form.category.value.trim();
      payload.expected_quantity = Number(form.expected_quantity.value);
      payload.unit = form.unit.value.trim();
    } else {
      payload.beneficiary_id = Number(form.beneficiary_id.value);
      payload.inventory_item_id = Number(form.inventory_item_id.value);
      payload.expected_quantity = Number(form.delivery_quantity.value);
    }

    try {
      const response = await fetch('/api/volunteer-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Task assignment failed');
      App.showToast(data.message, 'success');
      form.reset();
      this.toggleTaskType('pickup');
      this.loadTasks();
      this.loadPendingGoodsDonations();
    } catch (error) {
      App.showToast(error.message, 'error');
    }
  },

  async loadTasks() {
    if (!this.pollTimer) {
      this.pollTimer = setInterval(() => {
        if (App.currentView === 'volunteer-tasks') {
          this.loadTasks();
          if (Auth.hasRole('staff')) this.loadPendingGoodsDonations();
        }
      }, 10000);
    }
    try {
      const response = await fetch('/api/volunteer-tasks');
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not load volunteer tasks');
      this.renderTasks(data.tasks || []);
    } catch (error) {
      App.showToast(error.message, 'error');
    }
  },

  renderTasks(tasks) {
    const container = document.getElementById('volunteer-tasks-list');
    if (!container) return;

    const isVolunteer = Auth.currentUser && Auth.currentUser.role === 'volunteer';

    if (!tasks.length) {
      container.innerHTML = isVolunteer
        ? `<div class="p-4 text-center text-muted">
             <i class="fas fa-clipboard-check fa-2x mb-2 text-primary"></i>
             <h5>No tasks currently assigned to you</h5>
             <p class="text-xs mb-0">When NGO staff assigns a goods pickup task to you, it will appear here with full donor details.</p>
           </div>`
        : '<p class="text-muted p-3">No active volunteer tasks found.</p>';
      return;
    }

    container.innerHTML = tasks.map(task => {
      const pickup = task.task_type === 'pickup';
      const isFinished = ['Completed', 'Returned', 'Sent to Inventory', 'Delivered', 'Received in Inventory'].includes(task.status);
      const displayStatus = task.status === 'Returned' || task.status === 'Sent to Inventory'
        ? 'Delivered to Inventory'
        : task.status === 'On the Way'
          ? (pickup ? 'On the Way to Donor' : 'On the Way to Beneficiary')
          : task.status;

      const nextSteps = {
        'Assigned': { status: 'Accepted', label: 'Accept Task', icon: 'fa-check' },
        'Accepted': pickup
          ? { status: "At Donor's Location", label: "At Donor's Location", icon: 'fa-map-marker-alt' }
          : { status: 'Out for Delivery', label: 'Start Delivery', icon: 'fa-truck' },
        'On the Way': pickup
          ? { status: "At Donor's Location", label: "At Donor's Location", icon: 'fa-map-marker-alt' }
          : { status: 'Delivered', label: 'Confirm Delivered', icon: 'fa-check-double', needsQuantity: true },
        "At Donor's Location": { status: 'Picked Up', label: 'Goods Picked Up', icon: 'fa-box-open' },
        'Picked Up': { status: 'Sent to Inventory', label: 'Sent to Inventory', icon: 'fa-warehouse', needsQuantity: true },
        'Out for Delivery': { status: 'Delivered', label: 'Confirm Delivered', icon: 'fa-check-double', needsQuantity: true }
      };

      const nextStep = nextSteps[task.status];
      const addressLabel = pickup ? 'Pickup Address' : 'Delivery Location';
      const address = pickup ? task.donor_address : task.beneficiary_location;

      const mapLink = task.latest_location
        ? `<a target="_blank" rel="noopener" href="https://maps.google.com/?q=${task.latest_location.latitude},${task.latest_location.longitude}" class="font-weight-bold text-primary">
             <i class="fas fa-map-marked-alt text-danger mr-1"></i> Latest GPS: ${task.latest_location.latitude.toFixed(4)}, ${task.latest_location.longitude.toFixed(4)} (${task.latest_location.captured_at})
           </a>`
        : '<span class="text-muted text-xs">GPS not shared yet</span>';

      const locationHistory = (task.location_history || []).map(point => `
        <li><a target="_blank" rel="noopener" href="https://maps.google.com/?q=${point.latitude},${point.longitude}">${point.captured_at} (${point.latitude.toFixed(4)}, ${point.longitude.toFixed(4)})</a></li>
      `).join('');

      const volunteerActions = isVolunteer && !isFinished ? `
        <div class="mt-3 pt-3 border-top d-flex gap-2 flex-wrap align-items-center">
          ${nextStep ? `
            <button class="btn btn-primary btn-sm" data-status="${nextStep.status}" data-qty="${task.expected_quantity}" onclick="VolunteerTasksUI.advanceTask(${task.id}, this.dataset.status, ${Boolean(nextStep.needsQuantity)}, this.dataset.qty)">
              <i class="fas ${nextStep.icon} mr-1"></i> ${nextStep.label}
            </button>` : ''}

          ${task.status !== 'Assigned' ? (
            task.location_sharing ? `
              <button class="btn btn-outline-danger btn-sm" onclick="VolunteerTasksUI.stopLocation(${task.id})">
                <i class="fas fa-stop-circle mr-1"></i> Stop Sharing Location
              </button>
              <button class="btn btn-outline-primary btn-sm" onclick="VolunteerTasksUI.simulateLocationUpdate(${task.id})">
                <i class="fas fa-satellite mr-1"></i> Ping GPS (Update Location)
              </button>` : `
              <button class="btn btn-outline-primary btn-sm" onclick="VolunteerTasksUI.startLocation(${task.id})">
                <i class="fas fa-location-arrow mr-1"></i> Share Live Location
              </button>
              <button class="btn btn-outline-primary btn-sm" onclick="VolunteerTasksUI.simulateLocationUpdate(${task.id})">
                <i class="fas fa-satellite mr-1"></i> Ping GPS (Simulate)
              </button>`
          ) : '<small class="text-muted"><i class="fas fa-info-circle mr-1"></i> Accept the task to share your live location with donor and staff.</small>'}
        </div>` : '';

      return `
        <article class="p-3 mb-3 rounded border ${isFinished ? 'border-success' : 'bg-white'}" style="box-shadow:0 2px 6px rgba(0,0,0,0.03); ${isFinished ? 'background-color:#e8f5e9 !important; border-color:#2e7d32 !important;' : ''}">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
            <div>
              <h4 class="mb-0" style="font-size:1.1rem;color:var(--deep-accent);">
                <i class="${pickup ? 'fas fa-box-open' : 'fas fa-truck'} text-primary mr-1"></i>
                ${pickup ? 'Goods Pickup Task' : 'Beneficiary Delivery'} #${task.id}
              </h4>
              <small class="text-muted">Task Type: ${task.task_type.toUpperCase()}</small>
            </div>
            <div>
              <span class="badge ${isFinished ? 'badge-success' : 'badge-warning'}" style="font-size:0.85rem;padding:6px 12px;">
                ${App.escapeHtml(displayStatus)}
              </span>
            </div>
          </div>

          <div class="p-2 mb-2 rounded" style="background:#faf8ff;border:1px solid #eae4f5;">
            <div class="row">
              <div class="col-sm-6">
                <strong><i class="fas fa-cube text-primary mr-1"></i> Item:</strong> ${App.escapeHtml(task.item_name || task.category)}
              </div>
              <div class="col-sm-6">
                <strong><i class="fas fa-balance-scale text-primary mr-1"></i> Quantity:</strong> <span class="badge badge-lavender">${task.expected_quantity} ${App.escapeHtml(task.unit)}</span>
              </div>
            </div>
          </div>

          ${pickup ? `
            <div class="p-3 my-2 rounded border" style="background:#fdfdff;border-left:4px solid var(--deep-accent) !important;">
              <h5 class="mb-2" style="color:var(--deep-accent);font-size:0.95rem;">
                <i class="fas fa-user-circle mr-1 text-primary"></i> Donor Contact &amp; Pickup Information
              </h5>
              <div class="row">
                <div class="col-md-6 mb-2">
                  <div class="text-xs text-muted">Donor Name</div>
                  <strong style="font-size:1rem;">${App.escapeHtml(task.donor_name || 'Anonymous')}</strong>
                </div>
                <div class="col-md-6 mb-2">
                  <div class="text-xs text-muted">Phone Number</div>
                  ${task.donor_phone ? `
                    <a href="tel:${App.escapeHtml(task.donor_phone)}" class="text-primary font-weight-bold" style="font-size:0.95rem;">
                      <i class="fas fa-phone-alt mr-1"></i>${App.escapeHtml(task.donor_phone)} (Call Donor)
                    </a>` : '<span class="text-muted">Not provided</span>'}
                </div>
                <div class="col-12 mb-1">
                  <div class="text-xs text-muted">Pickup Address</div>
                  ${task.donor_address ? `
                    <div class="d-flex align-items-center gap-2 flex-wrap mt-1">
                      <span class="font-weight-bold"><i class="fas fa-home text-danger mr-1"></i>${App.escapeHtml(task.donor_address)}</span>
                      <a target="_blank" rel="noopener" href="https://maps.google.com/?q=${encodeURIComponent(task.donor_address)}" class="btn btn-outline btn-sm py-0 px-2" style="border-radius:6px;font-size:0.75rem;">
                        <i class="fas fa-directions mr-1"></i> Directions
                      </a>
                    </div>` : '<span class="text-muted">Not provided</span>'}
                </div>
                ${task.notes ? `
                  <div class="col-12 mt-2 pt-2 border-top">
                    <div class="text-xs text-muted">Pickup Instructions / Notes</div>
                    <small class="text-dark font-italic">${App.escapeHtml(task.notes)}</small>
                  </div>` : ''}
              </div>
            </div>` : `
            <div class="p-2 mb-2 bg-light rounded border">
              <strong>Beneficiary:</strong> ${App.escapeHtml(task.beneficiary_name)}<br>
              <strong>Location:</strong> ${App.escapeHtml(address || 'Not provided')}
            </div>`}

          ${!isVolunteer ? `
            <div class="p-2 mb-2 rounded bg-light border">
              <strong><i class="fas fa-user mr-1 text-primary"></i> Assigned Volunteer:</strong>
              ${App.escapeHtml(task.volunteer_name || 'Unassigned')}
              ${task.volunteer_phone ? `(<a href="tel:${App.escapeHtml(task.volunteer_phone)}" class="text-primary">${App.escapeHtml(task.volunteer_phone)}</a>)` : ''}
            </div>` : ''}

          <div class="p-2 rounded my-2 border" style="background:#fbfaff;">
            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
              <div>
                <strong>GPS Sharing:</strong>
                ${task.location_sharing
                  ? '<span class="radar-live-badge ml-2"><span class="radar-dot"></span> Active (Sharing with Donor & Staff)</span>'
                  : '<span class="badge badge-secondary ml-2">Inactive</span>'}
              </div>
              <div>${mapLink}</div>
            </div>
          </div>

          ${locationHistory ? `<details class="mt-2"><summary class="text-xs text-muted" style="cursor:pointer;">Location history (${task.location_history.length} pings)</summary><ol class="text-xs mt-1 pl-3">${locationHistory}</ol></details>` : ''}

          ${volunteerActions}
        </article>`;
    }).join('');
  },

  async simulateLocationUpdate(taskId) {
    try {
      const baseLat = 13.0827;
      const baseLng = 80.2707;
      const lat = baseLat + (Math.random() - 0.5) * 0.02;
      const lng = baseLng + (Math.random() - 0.5) * 0.02;

      const res = await fetch(`/api/volunteer-tasks/${taskId}/location`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'start',
          latitude: parseFloat(lat.toFixed(6)),
          longitude: parseFloat(lng.toFixed(6)),
          accuracy_meters: 8.5
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to update GPS location');
      App.showToast('GPS Location updated and shared in real-time with Donor & Staff!', 'success');
      this.loadTasks();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  startLocation(taskId) {
    if (!navigator.geolocation) {
      App.showToast('This browser does not support browser geolocation. Use the Ping GPS button.', 'warning');
      this.simulateLocationUpdate(taskId);
      return;
    }
    if (this.locationWatches[taskId] !== undefined) return;

    this.locationStarted[taskId] = false;
    this.locationWatches[taskId] = navigator.geolocation.watchPosition(async position => {
      const now = Date.now();
      if (this.locationStarted[taskId] && now - (this.lastLocationSentAt[taskId] || 0) < 10000) return;
      const action = this.locationStarted[taskId] ? 'update' : 'start';
      try {
        const response = await fetch(`/api/volunteer-tasks/${taskId}/location`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy_meters: position.coords.accuracy
          })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Location update failed');
        this.locationStarted[taskId] = true;
        this.lastLocationSentAt[taskId] = now;
        this.renderTasks(data.tasks || (await this.fetchTasks()));
        if (action === 'start') App.showToast('Live location sharing started with Donor & Staff.', 'success');
      } catch (error) {
        this.stopWatching(taskId);
        App.showToast(error.message, 'error');
      }
    }, error => {
      this.stopWatching(taskId);
      App.showToast('Could not access device GPS. Switching to simulation mode.', 'info');
      this.simulateLocationUpdate(taskId);
    }, { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 });
  },

  stopWatching(taskId) {
    if (this.locationWatches[taskId] !== undefined) {
      navigator.geolocation.clearWatch(this.locationWatches[taskId]);
      delete this.locationWatches[taskId];
    }
    delete this.locationStarted[taskId];
  },

  async fetchTasks() {
    const response = await fetch('/api/volunteer-tasks');
    const data = await response.json();
    return data.tasks || [];
  },

  async stopLocation(taskId) {
    this.stopWatching(taskId);
    try {
      const response = await fetch(`/api/volunteer-tasks/${taskId}/location`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'stop' })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not stop location sharing');
      App.showToast(data.message, 'info');
      this.loadTasks();
    } catch (error) {
      App.showToast(error.message, 'error');
    }
  },

  async advanceTask(taskId, status, needsQuantity, expectedQuantity) {
    console.log('advanceTask called', taskId, status, needsQuantity, expectedQuantity);
    const payload = { status };
    if (needsQuantity) {
      let quantity = Number(expectedQuantity) || 1;
      try {
        const entered = prompt('Enter the actual quantity of goods collected / delivered to inventory:', String(quantity));
        if (entered !== null) {
          const parsed = Number(entered);
          if (Number.isFinite(parsed) && parsed > 0) quantity = parsed;
        }
      } catch (e) {
        // Fall back to expected quantity if prompt is unavailable
      }
      payload.quantity = quantity;
    }
    try {
      const response = await fetch(`/api/volunteer-tasks/${taskId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not update task status');
      if (needsQuantity) this.stopWatching(taskId);
      App.showToast(data.message, 'success');
      this.loadTasks();
      if (Auth.hasRole('staff')) this.loadPendingGoodsDonations();
       if (typeof DonationsUI !== 'undefined') DonationsUI.loadDonations();
       PublicLandingUI.loadPublicImpact();
      if (needsQuantity) {
        PublicLandingUI.loadPublicImpact();
        if (typeof InventoryUI !== 'undefined') InventoryUI.loadInventory();
        if (typeof DonationsUI !== 'undefined') DonationsUI.loadDonations();
      }
    } catch (error) {
      App.showToast(error.message, 'error');
    }
  }
};

window.addEventListener('pagehide', () => {
  Object.entries(VolunteerTasksUI.locationWatches).forEach(([taskId, watchId]) => {
    navigator.geolocation.clearWatch(watchId);
    navigator.sendBeacon(
      `/api/volunteer-tasks/${taskId}/location`,
      new Blob([JSON.stringify({ action: 'stop' })], { type: 'application/json' })
    );
  });
});
