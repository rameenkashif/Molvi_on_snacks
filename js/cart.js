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
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
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
