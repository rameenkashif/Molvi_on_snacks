/* =========================================================
   Cart store — shared by every page. A small localStorage-backed
   store that the menu modal (index.html) writes to, and that the
   nav badge, the floating "View Cart" button, the cart page and
   the checkout page all read from.
   ========================================================= */
const CART_STORAGE_KEY = 'molvi-cart';
const DELIVERY_FEE = 80;

function readCart(){
  try {
    return JSON.parse(localStorage.getItem(CART_STORAGE_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function writeCart(cart){
  try {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
  } catch (e) {
    /* storage blocked (private mode, sandboxed preview, etc.) —
       still update the UI for this page load even though it won't
       persist across a reload */
  }
  updateCartBadge();
  updateViewCartFab();
  if (typeof renderCartPage === 'function') renderCartPage();
}

function addToCart(section, item, qty){
  const cart = readCart();
  const existing = cart.find((c) => c.section === section && c.id === item.id);
  if (existing){
    existing.qty += qty;
  } else {
    cart.push({ section, id: item.id, name: item.name, price: item.price, img: item.img, qty });
  }
  writeCart(cart);
}

function cartCount(){
  return readCart().reduce((sum, item) => sum + item.qty, 0);
}

function updateCartBadge(){
  const badge = document.getElementById('cart-badge');
  if (!badge) return;
  const count = cartCount();
  badge.textContent = count;
  badge.hidden = count === 0;
}

/* Floating "View Cart" button — pops in at the bottom right the
   moment the cart goes from empty to non-empty, on any page that
   includes it (currently just index.html, where people are adding
   items and may be scrolled far from the nav). */
function updateViewCartFab(){
  const fab = document.getElementById('view-cart-fab');
  if (!fab) return;
  const count = cartCount();
  const countEl = fab.querySelector('.view-cart-fab-count');
  if (countEl) countEl.textContent = count;
  fab.classList.toggle('is-visible', count > 0);
}

updateCartBadge();
updateViewCartFab();

/* =========================================================
   Account store — shared by every page, localStorage-backed like
   the cart above. Holds the signed-in user's profile, saved
   addresses and order history; there's no backend, so "signing in"
   just means an account object exists in this browser's storage.
   ========================================================= */
const ACCOUNT_STORAGE_KEY = 'molvi-account';

function readAccount(){
  try {
    return JSON.parse(localStorage.getItem(ACCOUNT_STORAGE_KEY));
  } catch (e) {
    return null;
  }
}

function writeAccount(account){
  try {
    localStorage.setItem(ACCOUNT_STORAGE_KEY, JSON.stringify(account));
  } catch (e) {
    /* storage blocked — still update the UI for this page load */
  }
  renderAccountNav();
}

function clearAccount(){
  try {
    localStorage.removeItem(ACCOUNT_STORAGE_KEY);
  } catch (e) { /* ignore */ }
  renderAccountNav();
}

function defaultAddress(account){
  if (!account || !account.addresses || !account.addresses.length) return null;
  return account.addresses.find((a) => a.isDefault) || account.addresses[0];
}

const ACCOUNT_RANKS = [
  { min: 6, label: 'VIP Snacker' },
  { min: 3, label: 'Snack Star' },
  { min: 1, label: 'Rising Snacker' },
  { min: 0, label: 'New Snacker' },
];
function rankFor(ordersCount){
  return ACCOUNT_RANKS.find((r) => ordersCount >= r.min).label;
}

/* Called by checkout.html once an order is placed, so it lands in
   "My Orders" and can move the account's rank up. No-ops when
   signed out — a guest checkout just isn't attached to an account. */
function recordOrder(order){
  const account = readAccount();
  if (!account) return;
  account.orders = account.orders || [];
  account.orders.unshift(order);
  writeAccount(account);
}

/* Keeps the nav's mascot state and the location button's label in
   sync with the account store — called after every login/logout/
   address change, plus once on page load. */
function renderAccountNav(){
  const account = readAccount();
  const accountWrap = document.getElementById('site-nav-account');
  if (accountWrap) accountWrap.classList.toggle('is-logged-in', !!account);

  const label = document.getElementById('site-nav-location-label');
  if (label){
    if (account){
      const addr = defaultAddress(account);
      label.textContent = addr ? `${addr.label} – ${addr.city}` : 'Add delivery address';
    } else {
      label.textContent = 'Select delivery area';
    }
  }

  const guestPanel = document.getElementById('site-nav-location-guest');
  const addressPanel = document.getElementById('site-nav-address-panel');
  if (guestPanel && addressPanel){
    guestPanel.hidden = !!account;
    addressPanel.hidden = !account;
    if (account && typeof renderAddressList === 'function') renderAddressList();
  }
}

renderAccountNav();

/* =========================================================
   Nav — Delivery/Pick-up toggle and the delivery-area picker.
   Shared chrome, so this lives here (not main.js) and runs on
   every page. The "map" is a decorative grid with a pin, not a
   live map — there's no map-provider key wired into this static
   site, so the pin's position is just looked up per area.
   ========================================================= */
{
  const toggleBtns = document.querySelectorAll('.site-nav-toggle-btn');
  toggleBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      toggleBtns.forEach((b) => b.classList.remove('is-active'));
      btn.classList.add('is-active');
    });
  });

  const ISLAMABAD_AREAS = [
    { name: 'E-7', top: 12, left: 50 },
    { name: 'E-11', top: 16, left: 78 },
    { name: 'F-6', top: 30, left: 42 },
    { name: 'F-7', top: 30, left: 50 },
    { name: 'F-8', top: 32, left: 58 },
    { name: 'F-10', top: 34, left: 68 },
    { name: 'F-11', top: 36, left: 78 },
    { name: 'Blue Area', top: 44, left: 50 },
    { name: 'G-6', top: 52, left: 42 },
    { name: 'G-7', top: 52, left: 50 },
    { name: 'G-8', top: 54, left: 58 },
    { name: 'G-9', top: 56, left: 64 },
    { name: 'G-10', top: 56, left: 72 },
    { name: 'G-11', top: 58, left: 80 },
    { name: 'Bahria Town', top: 60, left: 92 },
    { name: 'I-8', top: 76, left: 58 },
    { name: 'I-9', top: 78, left: 64 },
    { name: 'I-10', top: 80, left: 72 },
    { name: 'DHA Islamabad', top: 90, left: 66 },
  ];

  const locationWrap = document.getElementById('site-nav-location');
  const locationBtn = document.getElementById('site-nav-location-btn');
  const locationPanel = document.getElementById('site-nav-location-panel');
  const locationClose = document.getElementById('site-nav-location-close');
  const locationLabel = document.getElementById('site-nav-location-label');
  const locationSearch = document.getElementById('site-nav-location-search');
  const locationList = document.getElementById('site-nav-location-list');
  const locationPin = document.getElementById('site-nav-location-pin');

  if (locationWrap && locationBtn && locationPanel){
    let selectedArea = null;

    const renderAreaList = (filter) => {
      const q = (filter || '').trim().toLowerCase();
      const matches = ISLAMABAD_AREAS.filter((a) => a.name.toLowerCase().includes(q));
      locationList.innerHTML = '';
      if (matches.length === 0){
        const li = document.createElement('li');
        li.className = 'site-nav-location-empty';
        li.textContent = 'No matching area found';
        locationList.appendChild(li);
        return;
      }
      matches.forEach((area) => {
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = area.name;
        if (selectedArea && selectedArea.name === area.name) btn.classList.add('is-selected');
        btn.addEventListener('click', () => selectArea(area));
        li.appendChild(btn);
        locationList.appendChild(li);
      });
    };

    const closeLocationPanel = () => {
      locationPanel.hidden = true;
      locationWrap.classList.remove('is-open');
      locationBtn.setAttribute('aria-expanded', 'false');
    };

    function selectArea(area){
      selectedArea = area;
      locationLabel.textContent = area.name;
      locationPin.hidden = false;
      locationPin.style.top = area.top + '%';
      locationPin.style.left = area.left + '%';
      renderAreaList(locationSearch.value);
      closeLocationPanel();
    }

    const openLocationPanel = () => {
      locationPanel.hidden = false;
      locationWrap.classList.add('is-open');
      locationBtn.setAttribute('aria-expanded', 'true');
      renderAreaList(locationSearch.value);
      locationSearch.focus();
    };

    locationBtn.addEventListener('click', () => {
      if (locationPanel.hidden) openLocationPanel(); else closeLocationPanel();
    });
    if (locationClose) locationClose.addEventListener('click', closeLocationPanel);
    locationSearch.addEventListener('input', () => renderAreaList(locationSearch.value));

    // Close on an outside click — checked by containment rather than
    // stopPropagation tricks, so it can never end up eating clicks
    // meant for other nav elements (links, cart icon, toggle).
    document.addEventListener('click', (e) => {
      if (!locationPanel.hidden && !locationWrap.contains(e.target)) closeLocationPanel();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeLocationPanel();
    });

    renderAreaList('');
  }
}

/* =========================================================
   Account — mascot login/menu, saved addresses, profile and
   orders. All the modals share the .menu-modal chrome (styling
   only; their open/close logic is independent of main.js's own
   #menu-modal controller, keyed off separate ids).
   ========================================================= */
{
  const openModal = (modal) => {
    if (!modal) return;
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('menu-modal-lock');
  };
  const closeModal = (modal) => {
    if (!modal) return;
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    if (!document.querySelector('.menu-modal.is-open')) document.body.classList.remove('menu-modal-lock');
  };

  document.addEventListener('click', (e) => {
    const closer = e.target.closest('[data-modal-close]');
    if (closer) closeModal(closer.closest('.menu-modal'));
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') document.querySelectorAll('.menu-modal.is-open').forEach(closeModal);
  });

  /* ---- mascot button: login modal when signed out, dropdown menu
     when signed in ---- */
  const accountWrap = document.getElementById('site-nav-account');
  const accountBtn = document.getElementById('site-nav-account-btn');
  const accountMenu = document.getElementById('site-nav-account-menu');
  const loginModal = document.getElementById('login-modal');

  const closeAccountMenu = () => {
    if (!accountMenu) return;
    accountMenu.hidden = true;
    accountWrap.classList.remove('is-open');
    accountBtn.setAttribute('aria-expanded', 'false');
  };
  const openAccountMenu = () => {
    accountMenu.hidden = false;
    accountWrap.classList.add('is-open');
    accountBtn.setAttribute('aria-expanded', 'true');
  };

  if (accountBtn){
    accountBtn.addEventListener('click', () => {
      if (!readAccount()){
        openModal(loginModal);
        return;
      }
      if (accountMenu.hidden) openAccountMenu(); else closeAccountMenu();
    });
  }
  document.addEventListener('click', (e) => {
    if (accountWrap && !accountMenu.hidden && !accountWrap.contains(e.target)) closeAccountMenu();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAccountMenu();
  });

  document.querySelectorAll('[data-account-action]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      // stops this click from also bubbling to the location panel's
      // own outside-click listener, which would otherwise see it
      // (target outside .site-nav-location) and immediately close
      // the panel this button just opened
      e.stopPropagation();
      const action = btn.dataset.accountAction;
      closeAccountMenu();
      if (action === 'orders'){
        renderOrdersModal();
        openModal(document.getElementById('account-orders-modal'));
      } else if (action === 'addresses'){
        const locationBtn = document.getElementById('site-nav-location-btn');
        const locationPanel = document.getElementById('site-nav-location-panel');
        if (locationBtn && locationPanel && locationPanel.hidden) locationBtn.click();
      } else if (action === 'profile'){
        renderProfileModal();
        openModal(document.getElementById('account-profile-modal'));
      } else if (action === 'logout'){
        clearAccount();
        document.querySelectorAll('.menu-modal.is-open').forEach(closeModal);
      }
    });
  });

  /* ---- login / sign up form ---- */
  const loginForm = document.getElementById('login-form');
  if (loginForm){
    loginForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!e.target.reportValidity()) return;
      writeAccount({
        name: document.getElementById('login-name').value.trim(),
        email: document.getElementById('login-email').value.trim(),
        phone: document.getElementById('login-phone').value.trim(),
        addresses: [],
        orders: [],
      });
      loginForm.reset();
      closeModal(loginModal);
    });
  }

  /* ---- saved addresses: list + add-new form, inside the nav's
     location dropdown ---- */
  const addressListEl = document.getElementById('site-nav-address-list');
  const addressAddBtn = document.getElementById('site-nav-address-add-btn');
  const addressFormWrap = document.getElementById('site-nav-address-form-wrap');
  const addressFormLabel = document.getElementById('address-form-label');
  const addressFormLine = document.getElementById('address-form-line');
  const addressFormCity = document.getElementById('address-form-city');

  window.renderAddressList = function renderAddressList(){
    if (!addressListEl) return;
    const account = readAccount();
    addressListEl.innerHTML = '';
    const addresses = (account && account.addresses) || [];
    if (addresses.length === 0){
      const li = document.createElement('li');
      li.className = 'site-nav-address-empty';
      li.textContent = 'No saved addresses yet';
      addressListEl.appendChild(li);
      return;
    }
    addresses.forEach((addr) => {
      const li = document.createElement('li');
      li.className = 'site-nav-address-item' + (addr.isDefault ? ' is-default' : '');
      li.innerHTML = `
        <button type="button" class="site-nav-address-select" data-id="${addr.id}">
          <span class="site-nav-address-label">${addr.label}${addr.isDefault ? '<em>Default</em>' : ''}</span>
          <span class="site-nav-address-line">${addr.line}, ${addr.city}</span>
        </button>
        <button type="button" class="site-nav-address-remove" data-id="${addr.id}" aria-label="Remove address">&times;</button>
      `;
      addressListEl.appendChild(li);
    });

    addressListEl.querySelectorAll('.site-nav-address-select').forEach((btn) => {
      btn.addEventListener('click', () => {
        const acc = readAccount();
        if (!acc) return;
        acc.addresses.forEach((a) => { a.isDefault = a.id === btn.dataset.id; });
        writeAccount(acc);
      });
    });
    addressListEl.querySelectorAll('.site-nav-address-remove').forEach((btn) => {
      btn.addEventListener('click', () => {
        const acc = readAccount();
        if (!acc) return;
        const wasDefault = acc.addresses.find((a) => a.id === btn.dataset.id)?.isDefault;
        acc.addresses = acc.addresses.filter((a) => a.id !== btn.dataset.id);
        if (wasDefault && acc.addresses.length) acc.addresses[0].isDefault = true;
        writeAccount(acc);
      });
    });
  };

  if (addressAddBtn && addressFormWrap){
    addressAddBtn.addEventListener('click', () => {
      addressFormWrap.hidden = false;
      addressAddBtn.hidden = true;
      addressFormLabel.focus();
    });
    document.getElementById('address-form-cancel').addEventListener('click', () => {
      addressFormWrap.hidden = true;
      addressAddBtn.hidden = false;
      addressFormLabel.value = '';
      addressFormLine.value = '';
      addressFormCity.value = 'Islamabad';
    });
    document.getElementById('address-form-save').addEventListener('click', () => {
      const label = addressFormLabel.value.trim();
      const line = addressFormLine.value.trim();
      const city = addressFormCity.value.trim();
      if (!label || !line || !city) return;
      const account = readAccount();
      if (!account) return;
      account.addresses = account.addresses || [];
      account.addresses.push({
        id: Date.now().toString(36),
        label, line, city,
        isDefault: account.addresses.length === 0,
      });
      writeAccount(account);
      addressFormWrap.hidden = true;
      addressAddBtn.hidden = false;
      addressFormLabel.value = '';
      addressFormLine.value = '';
      addressFormCity.value = 'Islamabad';
    });
  }

  /* ---- profile: view + inline edit ---- */
  window.renderProfileModal = function renderProfileModal(){
    const account = readAccount();
    if (!account) return;
    document.getElementById('profile-name').textContent = account.name || '—';
    document.getElementById('profile-email').textContent = account.email || '—';
    document.getElementById('profile-phone').textContent = account.phone || '—';
    const addr = defaultAddress(account);
    document.getElementById('profile-address').textContent = addr ? `${addr.line}, ${addr.city}` : 'No address saved';
    document.getElementById('profile-rank').textContent = rankFor((account.orders || []).length);
  };

  const profileView = document.getElementById('profile-view');
  const profileEditForm = document.getElementById('profile-edit-form');
  const profileEditBtn = document.getElementById('profile-edit-btn');
  if (profileEditBtn){
    profileEditBtn.addEventListener('click', () => {
      const account = readAccount();
      if (!account) return;
      document.getElementById('profile-edit-name').value = account.name || '';
      document.getElementById('profile-edit-email').value = account.email || '';
      document.getElementById('profile-edit-phone').value = account.phone || '';
      profileView.hidden = true;
      profileEditForm.hidden = false;
    });
    document.getElementById('profile-edit-cancel').addEventListener('click', () => {
      profileEditForm.hidden = true;
      profileView.hidden = false;
    });
    profileEditForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!e.target.reportValidity()) return;
      const account = readAccount();
      if (!account) return;
      account.name = document.getElementById('profile-edit-name').value.trim();
      account.email = document.getElementById('profile-edit-email').value.trim();
      account.phone = document.getElementById('profile-edit-phone').value.trim();
      writeAccount(account);
      renderProfileModal();
      profileEditForm.hidden = true;
      profileView.hidden = false;
    });
  }

  /* ---- orders: read-only history, populated by recordOrder() from
     checkout.html when an order is placed while signed in ---- */
  window.renderOrdersModal = function renderOrdersModal(){
    const account = readAccount();
    const listEl = document.getElementById('account-orders-list');
    const emptyEl = document.getElementById('account-orders-empty');
    if (!listEl || !emptyEl) return;
    const orders = (account && account.orders) || [];
    listEl.innerHTML = '';
    emptyEl.hidden = orders.length !== 0;
    orders.forEach((order) => {
      const li = document.createElement('li');
      li.className = 'account-order-item';
      li.innerHTML = `
        <div class="account-order-item-head">
          <span class="account-order-item-date">${order.date}</span>
          <span class="account-order-item-total">Rs. ${order.total}</span>
        </div>
        <p class="account-order-item-items">${order.items.map((i) => `${i.name} &times;${i.qty}`).join(', ')}</p>
      `;
      listEl.appendChild(li);
    });
  };
}
