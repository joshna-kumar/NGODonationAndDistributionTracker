/* ==========================================================================
   Auth State & RBAC Capabilities Manager
   ========================================================================== */

const Auth = {
  currentUser: null,

  async init() {
    await this.checkSession();
  },

  async checkSession() {
    try {
      const res = await fetch('/api/auth/me');
      const data = await res.json();
      if (data.authenticated && data.user) {
        this.currentUser = data.user;
        this.renderUserUI();
      } else {
        this.currentUser = null;
        this.renderGuestUI();
      }
    } catch (err) {
      console.error('Session check failed:', err);
      this.currentUser = null;
      this.renderGuestUI();
    }
  },

  async login(email, password, role = '') {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Login failed');

      this.currentUser = data.user;
      this.renderUserUI();
      App.showToast(`Welcome back, ${data.user.name}!`, 'success');
      App.closeModal('login-modal');
      document.querySelectorAll('#login-modal form').forEach(form => { try { form.reset(); } catch (e) {} });
      document.querySelectorAll('#login-modal input').forEach(input => { input.value = ''; });
      App.navigateTo(App.getDefaultViewForRole(data.user.role));
      return true;
    } catch (err) {
      App.showToast(err.message, 'error');
      return false;
    }
  },

  async register(formData) {
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Registration failed');

      this.currentUser = data.user;
      this.renderUserUI();
      App.showToast('Account created successfully!', 'success');
      App.closeModal('register-modal');
      App.navigateTo(App.getDefaultViewForRole(data.user.role));
      return true;
    } catch (err) {
      App.showToast(err.message, 'error');
      return false;
    }
  },

  toggleRegistrationRole(role) {
    const fields = document.getElementById('beneficiary-registration-fields');
    if (fields) fields.style.display = role === 'beneficiary' ? '' : 'none';
    const location = document.querySelector('#register-modal [name="location"]');
    const eligibility = document.querySelector('#register-modal [name="eligibility_category"]');
    if (location) location.required = role === 'beneficiary';
    if (eligibility) eligibility.required = role === 'beneficiary';
  },

  async logout() {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      this.currentUser = null;
      this.renderGuestUI();
      // Clear any entered credentials from login/register forms
      document.querySelectorAll('#login-modal form, #register-modal form').forEach(form => {
        try { form.reset(); } catch (e) {}
      });
      document.querySelectorAll('#login-modal input, #register-modal input').forEach(input => {
        input.value = '';
      });
      App.showToast('Logged out successfully', 'info');
      App.navigateTo('dashboard');
    } catch (err) {
      console.error('Logout error:', err);
    }
  },

  async demoSwitch(role) {
    try {
      const res = await fetch('/api/auth/demo-switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Demo switch failed');

      this.currentUser = data.user;
      this.renderUserUI();
      App.showToast(`Switched active demo persona to ${role.toUpperCase()}`, 'success');
      App.navigateTo(App.getDefaultViewForRole(role));
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  renderUserUI() {
    const user = this.currentUser;
    if (!user) return;

    // Update Sidebar User Badge
    document.getElementById('user-display-name').textContent = user.name;
    document.getElementById('user-display-role').textContent = user.role.toUpperCase();
    document.getElementById('user-avatar-initial').textContent = user.name.charAt(0).toUpperCase();

    // Show/Hide Role-Specific Sidebar Items
    document.querySelectorAll('.role-nav').forEach(el => {
      const roles = el.getAttribute('data-roles').split(',');
      if (roles.includes('all') || roles.includes(user.role)) {
        el.style.display = 'flex';
      } else {
        el.style.display = 'none';
      }
    });

    // Update active state in demo banner
    document.querySelectorAll('.role-btn-group .role-btn').forEach(btn => {
      if (btn.getAttribute('data-role') === user.role) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    document.getElementById('auth-buttons-guest').style.display = 'none';
    document.getElementById('auth-buttons-user').style.display = 'flex';
    document.querySelectorAll('.donor-donation-action').forEach(el => {
      el.style.display = user.role === 'donor' ? '' : 'none';
    });
    document.querySelectorAll('.staff-donation-action').forEach(el => {
      el.style.display = this.hasRole('staff') ? '' : 'none';
    });
  },

  renderGuestUI() {
    document.getElementById('user-display-name').textContent = 'Guest Visitor';
    document.getElementById('user-display-role').textContent = 'Public Access';
    document.getElementById('user-avatar-initial').textContent = 'G';

    // Show only public menu items
    document.querySelectorAll('.role-nav').forEach(el => {
      const roles = el.getAttribute('data-roles').split(',');
      if (roles.includes('public')) {
        el.style.display = 'flex';
      } else {
        el.style.display = 'none';
      }
    });

    document.getElementById('auth-buttons-guest').style.display = 'flex';
    document.getElementById('auth-buttons-user').style.display = 'none';
    document.querySelectorAll('.donor-donation-action').forEach(el => {
      el.style.display = 'none';
    });
    document.querySelectorAll('.staff-donation-action').forEach(el => {
      el.style.display = 'none';
    });

    document.querySelectorAll('.role-btn-group .role-btn').forEach(btn => btn.classList.remove('active'));
  },

  hasRole(...allowedRoles) {
    if (!this.currentUser) return false;
    if (this.currentUser.role === 'admin') return true;
    return allowedRoles.includes(this.currentUser.role);
  }
};
