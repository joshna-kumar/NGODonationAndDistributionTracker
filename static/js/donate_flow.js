/* ==========================================================================
   DonateFlowUI — GPay-style UPI donation flow
   Handles: type chooser → amount entry → PIN pad → success screen
   ========================================================================== */

const DonateFlowUI = {
  /* internal state */
  _donationType: 'Monetary',   // 'Monetary' | 'In-Kind'
  _category: 'Money',
  _amount: 0,
  _pin: '',
  _donorId: null,
  _lastDonationId: null,

  /* ---------------------------------------------------------- */
  /* PUBLIC API                                                   */
  /* ---------------------------------------------------------- */

  /** Open the donation modal, optionally pre-binding a donor */
  open(donorId = null) {
    if (typeof DonationsUI !== 'undefined') {
      DonationsUI.openDonationModal(donorId);
      return;
    }
    this._donorId = donorId;
    this._reset();
    App.openModal('donate-type-modal');
  },

  /** Called when user clicks one of the type cards */
  selectType(donationType, category) {
    this._donationType = donationType;
    this._category = category;
    App.closeModal('donate-type-modal');

    if (donationType === 'Monetary') {
      // Open GPay-style UPI flow
      this._resetUPI();
      App.openModal('upi-payment-modal');
    } else {
      // In-Kind donation → prefill the existing log donation modal
      this._openInKindModal(category);
    }
  },

  /* ---------------------------------------------------------- */
  /* UPI FLOW — Step 1: Amount                                   */
  /* ---------------------------------------------------------- */

  setAmount(val) {
    const input = document.getElementById('upi-amount-input');
    if (input) {
      input.value = val;
      input.focus();
    }
  },

  proceedToPin() {
    const amountInput = document.getElementById('upi-amount-input');
    const amount = parseFloat(amountInput ? amountInput.value : 0);
    if (!amount || amount <= 0) {
      App.showToast('Please enter a valid amount greater than ₹0.', 'warning');
      return;
    }
    this._amount = amount;

    // Update PIN screen header
    const pinDisplay = document.getElementById('upi-pin-amount-display');
    if (pinDisplay) pinDisplay.textContent = '₹' + amount.toLocaleString('en-IN');

    // Switch step
    document.getElementById('upi-step-amount').style.display = 'none';
    document.getElementById('upi-step-pin').style.display = '';
    this._pin = '';
    this._updatePinDots();
  },

  backToAmount() {
    document.getElementById('upi-step-pin').style.display = 'none';
    document.getElementById('upi-step-amount').style.display = '';
    document.getElementById('upi-pin-processing').style.display = 'none';
    this._pin = '';
    this._updatePinDots();
  },

  /* ---------------------------------------------------------- */
  /* UPI FLOW — Step 2: PIN Pad                                  */
  /* ---------------------------------------------------------- */

  pinDigit(d) {
    if (this._pin.length >= 6) return;
    this._pin += d;
    this._updatePinDots();
    if (this._pin.length === 6) {
      // Auto-submit when 6 digits entered
      setTimeout(() => this._submitPayment(), 200);
    }
  },

  pinBack() {
    this._pin = this._pin.slice(0, -1);
    this._updatePinDots();
  },

  /* ---------------------------------------------------------- */
  /* PAYMENT SUBMISSION                                           */
  /* ---------------------------------------------------------- */

  async _submitPayment() {
    // Show processing spinner, hide numpad
    document.getElementById('upi-pin-processing').style.display = '';
    document.querySelector('.upi-numpad').style.opacity = '0.3';
    document.querySelector('.upi-numpad').style.pointerEvents = 'none';

    // Simulate brief network delay (1.8s) then record donation
    await new Promise(r => setTimeout(r, 1800));

    try {
      const note = (document.getElementById('upi-note-input') || {}).value || '';

      // Resolve donor id for the API call
      let donorId = this._donorId;
      if (!donorId && Auth.currentUser && Auth.currentUser.role === 'donor') {
        donorId = await this._resolveSelfDonorId();
      }

      const formData = new FormData();
      if (donorId) formData.set('donor_id', donorId);
      formData.set('type', 'Monetary');
      formData.set('category', this._category);
      formData.set('amount', this._amount);
      formData.set('notes', note || 'UPI payment via GPay flow');

      const res = await fetch('/api/donations', { method: 'POST', body: formData });
      const data = await res.json();

      if (!res.ok) throw new Error(data.error || 'Payment failed');

      this._lastDonationId = data.donation ? data.donation.id : null;
      App.closeModal('upi-payment-modal');
      this._showSuccess(data.donation);

    } catch (err) {
      App.closeModal('upi-payment-modal');
      App.showToast(err.message || 'Payment could not be processed.', 'error');
    }
  },

  /* ---------------------------------------------------------- */
  /* SUCCESS SCREEN                                               */
  /* ---------------------------------------------------------- */

  _showSuccess(donation) {
    // Fill success details
    const fmt = new Intl.NumberFormat('en-IN');
    const amtEl = document.getElementById('pay-success-amount');
    if (amtEl) amtEl.textContent = '₹' + fmt.format(this._amount);

    const catEl = document.getElementById('pay-success-category');
    if (catEl) catEl.textContent = this._category;

    const dateEl = document.getElementById('pay-success-date');
    if (dateEl) {
      const now = new Date();
      dateEl.textContent = now.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' })
        + ' ' + now.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });
    }

    const refEl = document.getElementById('pay-success-ref');
    if (refEl) {
      const refNum = 'UPI' + Date.now().toString().slice(-10);
      refEl.textContent = 'Ref: ' + refNum;
    }

    // Force SVG animation replay by cloning the element
    const ring = document.querySelector('.success-ring-outer');
    if (ring) {
      const clone = ring.cloneNode(true);
      ring.parentNode.replaceChild(clone, ring);
    }

    App.openModal('payment-success-modal');

    // Refresh donor data in the background
    if (typeof DonationsUI !== 'undefined') {
      DonationsUI.loadDonations().catch(() => {});
    }
    if (typeof DonorsUI !== 'undefined') {
      DonorsUI.loadDonors().catch(() => {});
    }
    if (typeof PublicLandingUI !== 'undefined') {
      PublicLandingUI.loadPublicImpact().catch(() => {});
    }
  },

  goToDonorProfile() {
    App.closeModal('payment-success-modal');
    // Navigate to donations view so user sees the updated record with Successful status
    App.navigateTo('donations');
    if (this._lastDonationId) {
      setTimeout(() => {
        if (typeof DonationsUI !== 'undefined') {
          DonationsUI.showReceipt(this._lastDonationId);
        }
      }, 400);
    }
  },

  donateAgain() {
    App.closeModal('payment-success-modal');
    this._reset();
    this.open(this._donorId);
  },

  /* ---------------------------------------------------------- */
  /* IN-KIND DONATION HELPER                                      */
  /* ---------------------------------------------------------- */

  _openInKindModal(category) {
    const typeSelect = document.querySelector('#add-donation-modal [name="type"]');
    const catSelect  = document.querySelector('#add-donation-modal [name="category"]');

    if (typeSelect) {
      typeSelect.value = 'In-Kind';
      if (typeof DonationsUI !== 'undefined') DonationsUI.toggleDonationType('In-Kind');
    }
    if (catSelect) {
      // Try to match by value; fall back gracefully
      const opts = Array.from(catSelect.options);
      const match = opts.find(o => o.value === category || o.text === category);
      if (match) catSelect.value = match.value;
    }

    // Prefill donor if known
    if (this._donorId) {
      const donorSel = document.getElementById('log-donation-donor-select');
      if (donorSel) donorSel.value = this._donorId;
    }

    App.openModal('add-donation-modal');
  },

  /* ---------------------------------------------------------- */
  /* INTERNAL HELPERS                                             */
  /* ---------------------------------------------------------- */

  _reset() {
    this._donationType = 'Monetary';
    this._category = 'Money';
    this._amount = 0;
    this._pin = '';
    this._lastDonationId = null;
  },

  _resetUPI() {
    const amtInput = document.getElementById('upi-amount-input');
    if (amtInput) amtInput.value = '';
    const noteInput = document.getElementById('upi-note-input');
    if (noteInput) noteInput.value = '';
    document.getElementById('upi-step-amount').style.display = '';
    document.getElementById('upi-step-pin').style.display = 'none';
    document.getElementById('upi-pin-processing').style.display = 'none';
    const numpad = document.querySelector('.upi-numpad');
    if (numpad) { numpad.style.opacity = ''; numpad.style.pointerEvents = ''; }
    this._pin = '';
    this._updatePinDots();
  },

  _updatePinDots() {
    const dots = document.querySelectorAll('#upi-pin-dots .upi-pin-dot');
    dots.forEach((dot, i) => {
      dot.classList.toggle('filled', i < this._pin.length);
    });
  },

  async _resolveSelfDonorId() {
    try {
      const res = await fetch('/api/donors?search=' + encodeURIComponent(Auth.currentUser.email));
      const data = await res.json();
      const donors = data.donors || [];
      if (donors.length) return donors[0].id;
    } catch (_) {}
    return null;
  }
};
