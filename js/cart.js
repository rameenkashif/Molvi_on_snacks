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
