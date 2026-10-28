/* ==========================================================================
   Main SPA Controller, Router & Toast Notification Manager
   ========================================================================== */

const App = {
  currentView: 'dashboard',

  recentDonationId: null,

  async init() {
    await Auth.init();
    this.setupEventListeners();
    const handledPayment = this.handlePaymentReturn();

    // Keep dashboard metrics (verified funds, etc.) fresh
    setInterval(() => {
      if (this.currentView === 'dashboard') {
        if (typeof PublicLandingUI !== 'undefined') PublicLandingUI.loadPublicImpact();
        if (typeof ChartManager !== 'undefined') ChartManager.loadAnalytics();
      }
    }, 5000);

    if (!handledPayment) {
      if (Auth.currentUser) {
        this.navigateTo(this.getDefaultViewForRole(Auth.currentUser.role));
      } else {
        this.navigateTo('dashboard');
      }
    }
  },

  handlePaymentReturn() {
    const params = new URLSearchParams(window.location.search);
    const paymentStatus = params.get('payment');
    const donationId = params.get('donation_id');
    const amount = params.get('amount');

    if (paymentStatus === 'success') {
      this.recentDonationId = donationId ? parseInt(donationId) : null;

      // Clean the URL
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);

      // Navigate to donations view
      const targetView = (Auth.currentUser && Auth.currentUser.role === 'donor') ? 'donations' : 'donations';
      this.navigateTo(targetView);

      const formattedAmount = amount ? '₹' + Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '';
      this.showToast(`🎉 Payment Successful! ${formattedAmount} received via GPay. Status updated to Payment Successful!`, 'success');

      if (typeof DonationsUI !== 'undefined') {
        DonationsUI.loadDonations();
        if (this.recentDonationId) {
          setTimeout(() => {
            DonationsUI.showReceipt(this.recentDonationId);
          }, 600);
        }
      }
      if (typeof DonorsUI !== 'undefined') {
        DonorsUI.loadDonors();
      }
      return true;
    }
    return false;
  },

  getDefaultViewForRole(role) {
    switch (role) {
      case 'donor':
        return 'donations';
      case 'beneficiary':
        return 'beneficiaries';
      case 'volunteer':
        return 'volunteer-tasks';
      case 'auditor':
        return 'ledger';
      case 'staff':
      case 'admin':
        return 'dashboard';
      default:
        return 'dashboard';
    }
  },

  canAccessView(viewId) {
    if (!Auth.currentUser) return false;

    const allowedRoles = {
      dashboard: ['admin', 'staff', 'auditor'],
      donors: ['admin', 'staff', 'auditor'],
      donations: ['admin', 'staff', 'donor', 'auditor'],
      inventory: ['admin', 'staff', 'auditor'],
      beneficiaries: ['admin', 'staff', 'beneficiary', 'auditor'],
      distributions: ['admin', 'staff', 'beneficiary', 'auditor', 'donor'],
      ledger: ['admin', 'staff', 'auditor'],
      reports: ['admin', 'staff', 'auditor'],
      audit: ['admin', 'auditor'],
      'volunteer-tasks': ['admin', 'staff', 'volunteer']
    };

    return (allowedRoles[viewId] || []).includes(Auth.currentUser.role);
  },

  setupEventListeners() {
    // Navigation items click events
    document.querySelectorAll('[data-view]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        const targetView = el.getAttribute('data-view');
        this.navigateTo(targetView);
      });
    });

    // Global Search Input
    const searchInput = document.getElementById('global-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.handleGlobalSearch(e.target.value.toLowerCase().trim());
      });
    }
  },

  navigateTo(viewId) {
    if (!this.canAccessView(viewId)) {
      if (Auth.currentUser) {
        const message = Auth.currentUser.role === 'donor'
          ? 'You can only view your own donation information.'
          : 'You do not have permission to access this page.';
        App.showToast(message, 'error');
        viewId = this.getDefaultViewForRole(Auth.currentUser.role);
      } else {
        viewId = 'login';
      }
    }

    this.currentView = viewId;

    // Hide all view sections
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));

    // Highlight active sidebar item
    document.querySelectorAll('.sidebar-menu .menu-item').forEach(item => {
      if (item.getAttribute('data-view') === viewId) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    // Show target section
    const targetSection = document.getElementById(`view-${viewId}`);
    if (targetSection) {
      targetSection.classList.add('active');
    }

    // Update Top Header Title
    const titleElem = document.getElementById('current-page-title');
    if (titleElem) {
      const titles = {
        'login': 'Sign In Required',
        'dashboard': 'Executive Overview & Analytics',
        'donors': 'Donor Management & Records',
        'donations': 'Donation Ledger & Receipts',
        'inventory': 'Real-Time Inventory Stock',
        'beneficiaries': 'Beneficiary Directory & Need Categories',
        'distributions': 'Aid Distribution Log',
        'ledger': 'SHA-256 Immutable Blockchain Ledger',
        'reports': 'Reports & Analytics Export',
        'audit': 'Administrative Audit Logs',
        'volunteer-tasks': 'Volunteer Tasks & Location'
      };
      titleElem.textContent = titles[viewId] || 'NGO Operations';
    }

    if (this.currentView === 'login') {
      this.openModal('login-modal');
      return;
    }

    // Trigger View Data Loading
    this.refreshCurrentView();
  },

  refreshCurrentView() {
    switch (this.currentView) {
      case 'dashboard':
        PublicLandingUI.loadPublicImpact();
        ChartManager.loadAnalytics();
        break;
      case 'donors':
        DonorsUI.loadDonors();
        break;
      case 'donations':
        DonationsUI.loadDonations();
        this.populateDonorDropdowns();
        break;
      case 'inventory':
        InventoryUI.loadInventory();
        break;
      case 'beneficiaries':
        BeneficiariesUI.loadBeneficiaries();
        break;
      case 'distributions':
        DistributionsUI.loadDistributions();
        break;
      case 'ledger':
        LedgerUI.loadLedger();
        LedgerUI.verifyIntegrity();
        break;
      case 'reports':
        ChartManager.loadAnalytics();
        break;
      case 'audit':
        this.loadAuditLogs();
        break;
      case 'volunteer-tasks':
        VolunteerTasksUI.loadTasks();
        if (Auth.hasRole('staff')) {
          VolunteerTasksUI.loadAssignmentOptions();
          VolunteerTasksUI.loadPendingGoodsDonations();
        }
        break;
    }
  },

  async populateDonorDropdowns() {
    const donorSection = document.getElementById('log-donation-donor-section');
    const donorNote = document.getElementById('donor-self-note');
    const select = document.getElementById('log-donation-donor-select');

    if (Auth.currentUser && Auth.currentUser.role === 'donor') {
      if (donorSection) {
        donorSection.style.display = 'none';
      }
      if (donorNote) {
        donorNote.style.display = 'block';
      }
      if (select) {
        select.innerHTML = `<option value="">${this.escapeHtml(Auth.currentUser.name)} (Your account)</option>`;
        select.required = false;
      }
      return;
    }

    if (donorSection) {
      donorSection.style.display = 'block';
    }
    if (donorNote) {
      donorNote.style.display = 'none';
    }
    if (select) {
      select.required = true;
    }

    try {
      const res = await fetch('/api/donors');
      const data = await res.json();
      if (select) {
        select.innerHTML = (data.donors || []).map(d => `<option value="${d.id}">${this.escapeHtml(d.name)} (${d.email})</option>`).join('');
      }
    } catch (err) {
      console.error('Failed to populate donor list', err);
    }
  },

  async loadAuditLogs() {
    try {
      const res = await fetch('/api/audit');
      const data = await res.json();
      const tbody = document.getElementById('audit-table-body');
      if (!tbody) return;

      tbody.innerHTML = (data.logs || []).map(l => `
        <tr>
          <td>${l.timestamp}</td>
          <td><strong>${this.escapeHtml(l.user_name)}</strong> <small class="text-muted">(${l.user_role})</small></td>
          <td><span class="badge badge-lavender">${l.action}</span></td>
          <td>${l.entity} #${l.entity_id || ''}</td>
          <td>${this.escapeHtml(l.details)}</td>
        </tr>
      `).join('');
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    }
  },

  handleGlobalSearch(query) {
    if (this.currentView === 'donors' && Auth.hasRole('admin', 'staff', 'auditor')) {
      DonorsUI.loadDonors(query);
      return;
    }

    if (!query) {
      document.querySelectorAll('.custom-table tbody tr').forEach(row => row.style.display = '');
      return;
    }

    document.querySelectorAll('.custom-table tbody tr').forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(query) ? '' : 'none';
    });
  },

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
  },

  async startCashfreeCheckout() {
    const form = document.querySelector('#add-donation-modal form');
    const amountInput = form ? form.querySelector('[name="amount"]') : null;
    const donorSelect = form ? form.querySelector('[name="donor_id"]') : null;
    const phoneInput = form ? form.querySelector('[name="customer_phone"]') : null;
    const rawAmount = Number(amountInput && amountInput.value ? amountInput.value : 0);
    const amount = Number.isFinite(rawAmount) && rawAmount > 0 ? Number(rawAmount) : null;

    if (!amount) {
      this.showToast('Please enter a valid donation amount before paying.', 'error');
      return;
    }

    if (!phoneInput || !phoneInput.value.trim()) {
      this.showToast('Enter the donor phone number to continue with Cashfree.', 'error');
      return;
    }

    try {
      const configRes = await fetch('/api/donations/cashfree/config');
      const configData = await configRes.json();

      if (!configData.enabled) {
        this.showToast('Cashfree is not configured. Set the Cashfree credentials in the hosting environment.', 'error');
        return;
      }

      const orderRes = await fetch('/api/donations/cashfree/create-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount,
          donor_id: donorSelect && donorSelect.value ? donorSelect.value : null,
          customer_phone: phoneInput.value.trim(),
          category: form.querySelector('[name="category"]').value,
          notes: form.querySelector('[name="notes"]').value
        })
      });

      const orderData = await orderRes.json();
      if (!orderRes.ok) {
        throw new Error(orderData.error || 'Unable to create Cashfree order');
      }

      const cashfree = Cashfree({ mode: configData.environment });
      await cashfree.checkout({
        paymentSessionId: orderData.payment_session_id,
        redirectTarget: '_self'
      });
    } catch (err) {
      console.error('Cashfree checkout failed:', err);
      this.showToast(err.message || 'Cashfree checkout failed. Please try again.', 'error');
    }
  },

  async confirmCashfreeReturn() {
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get('cashfree_order_id');
    if (!orderId || !Auth.currentUser) return;

    params.delete('cashfree_order_id');
    const cleanUrl = `${window.location.pathname}${params.size ? `?${params}` : ''}${window.location.hash}`;
    window.history.replaceState({}, document.title, cleanUrl);

    try {
      const response = await fetch('/api/donations/cashfree/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Payment confirmation failed');

      this.showToast(data.message, 'success');
      DonationsUI.loadDonations();
      PublicLandingUI.loadPublicImpact();
      if (data.donation) DonationsUI.showReceipt(data.donation.id);
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <i class="fas ${type === 'success' ? 'fa-check-circle text-success' : type === 'error' ? 'fa-exclamation-circle text-danger' : 'fa-info-circle text-info'}"></i>
      <span>${this.escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  escapeHtml(str) {
    return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
};

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
