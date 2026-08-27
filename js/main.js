gsap.registerPlugin(ScrollTrigger);

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* =========================================================
   Hero intro sequence
   Both mountain layers are on screen from frame one — nothing
   fades in. The front layer settles from a slight zoom, and the
   wordmark rises up through it, as if climbing from behind the
   front mountains and out in front of the full background.
   ========================================================= */
const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });

heroTl
  .to('.hero-bg-front img', { scale: 1, duration: 1.6, ease: 'power2.out' }, 0)
  .to('.hero-wordmark', { opacity: 1, duration: .3 }, .15)
  .to('.hero-wordmark', { y: 0, duration: 1.4, ease: 'power4.out' }, '<')
  // wood block rises from below until it settles at the hero's bottom edge
  .to('.hero-wood', { y: '0%', duration: 1, ease: 'power3.out' }, '-=.5')
  // orea & pista pop in first, then strawberry pops in front. The opacity
  // snaps on quickly so the overshoot on the scale reads as a pop rather
  // than a fade.
  .to(['.hero-bucket--orea', '.hero-bucket--pista'], {
    opacity: 1, duration: .15, stagger: .16,
  }, '-=.35')
  .to(['.hero-bucket--orea', '.hero-bucket--pista'], {
    scale: 1, duration: .7, ease: 'back.out(2.4)', stagger: .16,
  }, '<')
  .to('.hero-bucket--strawberry', { opacity: 1, duration: .15 }, '-=.3')
  .to('.hero-bucket--strawberry', {
    scale: 1, duration: .75, ease: 'back.out(2.6)',
  }, '<')
  // once everything else has landed, the closing wave rises in last
  .to('.hero-wave', { y: '0%', duration: .9, ease: 'power3.out' }, '-=.15');

if (!reduceMotion){
  gsap.to('.hero-bg-full img', {
    scale: 1.12,
    duration: 12,
    ease: 'none',
    delay: 1,
  });
}

/* =========================================================
   Hero — once the intro sequence finishes and the hero has held
   static for a beat, it becomes a slow, continuous carousel: the
   whole hero slide pushes off to the left as a promo poster arrives
   from the right, dwells there, then hands off to the next poster
   the same way, before sliding the hero itself back in from the
   right to loop the cycle. Skipped entirely under reduced motion,
   so the hero just stays put.
   ========================================================= */
if (!reduceMotion){
  const slider = document.getElementById('hero-slider');
  const slides = Array.from(slider.children);
  const DWELL_MS = 5000;
  const TRANSITION_DURATION = 1;
  let current = 0;
  let dwellId = null;

  gsap.set(slides.slice(1), { xPercent: 100, visibility: 'visible' });

  const scheduleNext = () => {
    clearTimeout(dwellId);
    dwellId = setTimeout(advance, DWELL_MS);
  };

  function advance(){
    const next = (current + 1) % slides.length;
    const outgoing = slides[current];
    const incoming = slides[next];
    gsap.set(incoming, { xPercent: 100 });
    gsap.timeline({
      defaults: { duration: TRANSITION_DURATION, ease: 'power3.inOut' },
      onComplete: () => {
        // park the slide we just left back on the right, ready to
        // re-enter from there whenever its turn comes round again
        gsap.set(outgoing, { xPercent: 100 });
        current = next;
        scheduleNext();
      },
    })
      .to(outgoing, { xPercent: -100 }, 0)
      .to(incoming, { xPercent: 0 }, 0);
  }

  heroTl.eventCallback('onComplete', scheduleNext);
}

/* =========================================================
   Icecream promo pop-up — the Khallis Vanilla poster, shown once
   (ever, per browser — tracked in localStorage) the first time a
   visitor scrolls into the icecream section.
   ========================================================= */
{
  const PROMO_SEEN_KEY = 'molvi-icecream-promo-seen';
  const popup = document.getElementById('promo-popup');
  let alreadySeen = true;
  try { alreadySeen = !!localStorage.getItem(PROMO_SEEN_KEY); } catch (e) { alreadySeen = false; }

  if (popup && !alreadySeen){
    const openPromo = () => {
      popup.classList.add('is-open');
      popup.setAttribute('aria-hidden', 'false');
      document.body.classList.add('menu-modal-lock');
      try { localStorage.setItem(PROMO_SEEN_KEY, '1'); } catch (e) { /* storage blocked */ }
    };
    const closePromo = () => {
      popup.classList.remove('is-open');
      popup.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('menu-modal-lock');
    };

    ScrollTrigger.create({
      trigger: '#next-page',
      start: 'top 70%',
      once: true,
      onEnter: openPromo,
    });

    popup.querySelectorAll('[data-promo-close]').forEach((el) => {
      el.addEventListener('click', closePromo);
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && popup.classList.contains('is-open')) closePromo();
    });
  }
}

/* =========================================================
   Scroll parallax — hero layers drift at different rates as the
   page scrolls into the next (empty, cream) section. The wave
   itself is left out of this: it stays pinned flush to the
   hero's bottom edge the whole time, so it never pulls away from
   the seam with .next-page and exposes a gap underneath it.
   ========================================================= */
gsap.timeline({
  scrollTrigger: {
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: .6,
  }
})
.to('.hero-buckets', { y: '-12%', ease: 'none' }, 0)
.to('.hero-wood', { y: '-6%', ease: 'none' }, 0)
.to('.hero-bg-front', { y: '-4%', ease: 'none' }, 0)
.to('.hero-bg-full img', { y: '3%', ease: 'none' }, 0);

/* =========================================================
   Flavour cards — once the wave has fully risen and the page
   reads as solid cream/yellow, the "icecreams" heading fades and
   zooms in above the row, then each card's colour block fades in,
   then its cup pops on top, echoing the hero buckets' beat.
   Strawberry sits centred and lands last, slightly larger.
   ========================================================= */
gsap.timeline({
  defaults: { ease: 'power3.out' },
  scrollTrigger: {
    trigger: '.next-page',
    start: 'top 65%',
    toggleActions: 'play none none reverse',
  }
})
  .to('.cups-heading', { opacity: 1, scale: 1, duration: .7, ease: 'back.out(1.7)' })
  .to('.cup-card-label', { opacity: 1, y: 0, duration: .5, stagger: .1 }, '-=.25')
  .to('.cup-card-img', { opacity: 1, scale: 1, duration: .7, ease: 'back.out(2.2)', stagger: .1 }, '-=.4')
  .to('.cups-cta', { opacity: 1, y: 0, duration: .6 }, '-=.2');

/* =========================================================
   Site nav — hidden off-screen through the hero, then slides down
   from the top once the visitor scrolls to the icecreams section
   (and slides back up if they scroll back into the hero).
   ========================================================= */
gsap.set('.site-nav', { yPercent: -100 });

ScrollTrigger.create({
  trigger: '.next-page',
  start: 'top top+=50',
  onEnter: () => gsap.to('.site-nav', { yPercent: 0, duration: .5, ease: 'power3.out' }),
  onLeaveBack: () => gsap.to('.site-nav', { yPercent: -100, duration: .4, ease: 'power3.in' }),
});

/* =========================================================
   Site nav — section links zoom to their destination. Clicking
   icecreams/samosas/shakes smooth-scrolls there as usual, but the
   destination section also pops in with a quick scale+fade, so the
   jump reads as the screen zooming onto that section rather than a
   plain scroll.
   ========================================================= */
if (!reduceMotion){
  document.querySelectorAll('.site-nav-links a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (e) => {
      const target = document.querySelector(link.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      gsap.fromTo(target,
        { scale: .92, opacity: .55 },
        { scale: 1, opacity: 1, duration: .7, ease: 'power3.out', delay: .2, transformOrigin: '50% 50%' }
      );
    });
  });
}

/* =========================================================
   Flavour cards — a continuous 6-up coverflow carousel, the same
   system as the samosa carousel below. All six flavours are always
   on screen; whichever is centred is called out (bigger, glowing)
   while the rest recede by distance either side, and the page
   background (plus the hero wave above it and the drip edge below)
   retints to that flavour's colour via --active-bg. Auto-advances on
   a timer; clicking any card recentres the whole set on it directly.
   ========================================================= */
{
  const flavourColors = {
    'choco-bliss': '#d8bfa3',
    orea: '#ecd9b3',
    strawberry: '#f6c2ce',
    pista: '#bcc684',
    'mango-masti': '#f6d98a',
    lotus: '#e6c48f',
  };
  const root = document.documentElement;
  const carousel = document.getElementById('cups-carousel');
  const cupCards = Array.from(document.querySelectorAll('.cup-card'));
  const count = cupCards.length;
  const half = Math.floor(count / 2);
  let current = cupCards.findIndex((c) => c.dataset.flavor === 'strawberry');
  if (current < 0) current = half;
  let autoplayId = null;
  let resumeId = null;

  const OFFSET_STYLE = {
    0: { tx: '0px', scale: '1.15', op: '1', z: '5' },
    1: { tx: 'clamp(90px, 16vw, 210px)', scale: '.82', op: '.55', z: '3' },
    2: { tx: 'clamp(170px, 28vw, 340px)', scale: '.6', op: '.28', z: '2' },
    3: { tx: 'clamp(230px, 38vw, 420px)', scale: '.42', op: '.12', z: '1' },
  };

  const render = () => {
    cupCards.forEach((card, i) => {
      let raw = i - current;
      if (raw > half) raw -= count;
      if (raw < -half) raw += count;
      const abs = Math.abs(raw);
      const style = OFFSET_STYLE[abs] || OFFSET_STYLE[3];
      const sign = raw < 0 ? -1 : 1;
      card.style.setProperty('--tx', abs === 0 ? '0px' : `calc(${sign} * ${style.tx})`);
      card.style.setProperty('--scale', style.scale);
      card.style.setProperty('--op', style.op);
      card.style.setProperty('--z', style.z);
      card.classList.toggle('is-center', raw === 0);
      card.setAttribute('aria-pressed', raw === 0 ? 'true' : 'false');
    });
    root.style.setProperty('--active-bg', flavourColors[cupCards[current].dataset.flavor]);
  };

  const goTo = (index) => {
    current = ((index % count) + count) % count;
    render();
  };

  const stopAutoplay = () => {
    if (autoplayId) clearInterval(autoplayId);
    autoplayId = null;
  };
  const startAutoplay = () => {
    stopAutoplay();
    if (reduceMotion) return;
    autoplayId = setInterval(() => goTo(current + 1), 2800);
  };
  const pauseThenResume = () => {
    stopAutoplay();
    clearTimeout(resumeId);
    resumeId = setTimeout(startAutoplay, 4500);
  };

  cupCards.forEach((card, i) => {
    card.addEventListener('click', () => { goTo(i); pauseThenResume(); });
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' '){
        e.preventDefault();
        goTo(i);
        pauseThenResume();
      }
    });
  });

  carousel.addEventListener('mouseenter', stopAutoplay);
  carousel.addEventListener('mouseleave', startAutoplay);

  render();
  startAutoplay();
}

/* =========================================================
   Samosas — heading and the five-up carousel fade/pop in once the
   section scrolls into view, echoing the icecream cards' beat. The
   logo and "official snack tester" stickers are static (no
   animation, no scroll trigger) so they aren't part of this timeline.
   ========================================================= */
gsap.timeline({
  defaults: { ease: 'power3.out' },
  scrollTrigger: {
    trigger: '.samosa-page',
    start: 'top 70%',
    toggleActions: 'play none none reverse',
  }
})
  .to('.samosa-heading', { opacity: 1, scale: 1, duration: .7, ease: 'back.out(1.7)' })
  .to('.samosa-card-label', { opacity: 1, y: 0, duration: .5, stagger: .1 }, '-=.25')
  .to('.samosa-card-img', { opacity: 1, scale: 1, duration: .7, ease: 'back.out(2.2)', stagger: .1 }, '-=.4')
  .to('.samosa-cta', { opacity: 1, y: 0, duration: .6 }, '-=.2');

/* =========================================================
   Samosas — a continuous 5-up coverflow carousel. All five flavours
   are always on screen; whichever one is centred is called out
   (bigger, glowing) while the rest recede by distance either side.
   It auto-advances on a timer, and clicking any card (even one two
   spots away) recentres the whole set on it directly — same
   transition either way, so it just reads as the carousel spinning
   forward or back to bring that flavour round to the middle.
   ========================================================= */
{
  const carousel = document.getElementById('samosa-carousel');
  const samosaCards = Array.from(document.querySelectorAll('.samosa-card'));
  const count = samosaCards.length;
  const half = Math.floor(count / 2);
  let current = samosaCards.findIndex((c) => c.dataset.flavor === 'pizza');
  if (current < 0) current = half;
  let autoplayId = null;
  let resumeId = null;

  const OFFSET_STYLE = {
    0: { tx: '0px', scale: '1.15', op: '1', z: '5' },
    1: { tx: 'clamp(90px, 16vw, 210px)', scale: '.82', op: '.55', z: '3' },
    2: { tx: 'clamp(170px, 28vw, 340px)', scale: '.6', op: '.25', z: '1' },
  };

  const render = () => {
    samosaCards.forEach((card, i) => {
      let raw = i - current;
      if (raw > half) raw -= count;
      if (raw < -half) raw += count;
      const abs = Math.abs(raw);
      const style = OFFSET_STYLE[abs] || OFFSET_STYLE[2];
      const sign = raw < 0 ? -1 : 1;
      card.style.setProperty('--tx', abs === 0 ? '0px' : `calc(${sign} * ${style.tx})`);
      card.style.setProperty('--scale', style.scale);
      card.style.setProperty('--op', style.op);
      card.style.setProperty('--z', style.z);
      card.classList.toggle('is-center', raw === 0);
      card.setAttribute('aria-pressed', raw === 0 ? 'true' : 'false');
    });
  };

  const goTo = (index) => {
    current = ((index % count) + count) % count;
    render();
  };

  const stopAutoplay = () => {
    if (autoplayId) clearInterval(autoplayId);
    autoplayId = null;
  };
  const startAutoplay = () => {
    stopAutoplay();
    if (reduceMotion) return;
    autoplayId = setInterval(() => goTo(current + 1), 2800);
  };
  const pauseThenResume = () => {
    stopAutoplay();
    clearTimeout(resumeId);
    resumeId = setTimeout(startAutoplay, 4500);
  };

  samosaCards.forEach((card, i) => {
    card.addEventListener('click', () => { goTo(i); pauseThenResume(); });
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' '){
        e.preventDefault();
        goTo(i);
        pauseThenResume();
      }
    });
  });

  carousel.addEventListener('mouseenter', stopAutoplay);
  carousel.addEventListener('mouseleave', startAutoplay);

  render();
  startAutoplay();
}

/* =========================================================
   Shakes — heading and the three-up selector fade/pop in once the
   section scrolls into view, the same beat as the icecream cups and
   samosas.
   ========================================================= */
gsap.timeline({
  defaults: { ease: 'power3.out' },
  scrollTrigger: {
    trigger: '.shakes-page',
    start: 'top 70%',
    toggleActions: 'play none none reverse',
  }
})
  .to('.shakes-heading', { opacity: 1, scale: 1, duration: .7, ease: 'back.out(1.7)' })
  .to('.shake-card-label', { opacity: 1, y: 0, duration: .5, stagger: .15 }, '-=.25')
  .to('.shake-card-img', { opacity: 1, scale: 1, duration: .7, ease: 'back.out(2.2)', stagger: .16 }, '-=.4')
  .to('.shakes-cta', { opacity: 1, y: 0, duration: .6 }, '-=.2');

/* =========================================================
   Shakes — a continuous 3-up coverflow carousel, the same system as
   the samosa and icecream carousels above. All three flavours are
   always on screen; whichever one is centred is called out (bigger,
   glowing) while the other two recede either side. It auto-advances
   on a timer, and clicking any card recentres the whole set on it.
   ========================================================= */
{
  const carousel = document.getElementById('shakes-carousel');
  const shakeCards = Array.from(document.querySelectorAll('.shake-card'));
  const count = shakeCards.length;
  const half = Math.floor(count / 2);
  let current = shakeCards.findIndex((c) => c.dataset.flavor === 'chocolate');
  if (current < 0) current = half;
  let autoplayId = null;
  let resumeId = null;

  const OFFSET_STYLE = {
    0: { tx: '0px', scale: '1.15', op: '1', z: '5' },
    1: { tx: 'clamp(120px, 22vw, 260px)', scale: '.78', op: '.5', z: '3' },
  };

  const render = () => {
    shakeCards.forEach((card, i) => {
      let raw = i - current;
      if (raw > half) raw -= count;
      if (raw < -half) raw += count;
      const abs = Math.abs(raw);
      const style = OFFSET_STYLE[abs] || OFFSET_STYLE[1];
      const sign = raw < 0 ? -1 : 1;
      card.style.setProperty('--tx', abs === 0 ? '0px' : `calc(${sign} * ${style.tx})`);
      card.style.setProperty('--scale', style.scale);
      card.style.setProperty('--op', style.op);
      card.style.setProperty('--z', style.z);
      card.classList.toggle('is-center', raw === 0);
      card.setAttribute('aria-pressed', raw === 0 ? 'true' : 'false');
    });
  };

  const goTo = (index) => {
    current = ((index % count) + count) % count;
    render();
  };

  const stopAutoplay = () => {
    if (autoplayId) clearInterval(autoplayId);
    autoplayId = null;
  };
  const startAutoplay = () => {
    stopAutoplay();
    if (reduceMotion) return;
    autoplayId = setInterval(() => goTo(current + 1), 2800);
  };
  const pauseThenResume = () => {
    stopAutoplay();
    clearTimeout(resumeId);
    resumeId = setTimeout(startAutoplay, 4500);
  };

  shakeCards.forEach((card, i) => {
    card.addEventListener('click', () => { goTo(i); pauseThenResume(); });
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' '){
        e.preventDefault();
        goTo(i);
        pauseThenResume();
      }
    });
  });

  carousel.addEventListener('mouseenter', stopAutoplay);
  carousel.addEventListener('mouseleave', startAutoplay);

  render();
  startAutoplay();
}

/* =========================================================
   Menu modal — shared "view all" popup for icecreams, samosas and
   shakes. Same panel markup for all three, themed per section via
   modal[data-theme]; the flavour selected on the home page (if any)
   opens pre-added at qty 1, everything else starts at 0. Users can
   add multiple flavours, adjust quantities, leave instructions, then
   add the whole order to the cart in one go.
   ========================================================= */
{
  const SAMOSA_SIZES = [
    { id: 'half', label: 'Half Dozen', mult: 6 },
    { id: 'full', label: 'Full Dozen', mult: 12 },
  ];

  const ICECREAM_SIZES = [
    { id: 'small', label: '250 ml', mult: 1 },
    { id: 'large', label: '500 ml', mult: 2 },
  ];

  const menuData = {
    icecreams: {
      title: 'Ice-Creams',
      /* mango masti, choco bliss and lotus are newly added flavours —
         reusing the orea/strawberry/pista photos as placeholders
         until their own product shots are ready. */
      items: [
        { id: 'choco-bliss', name: 'Choco Bliss', price: 160, desc: 'Rich chocolate fudge ice-cream', img: 'assets/images/cup-strawberry-card.png', sizes: ICECREAM_SIZES },
        { id: 'orea', name: 'Orea Barkat', price: 150, desc: 'Oreo chunks in creamy vanilla', img: 'assets/images/cup-orea-card.png', sizes: ICECREAM_SIZES },
        { id: 'strawberry', name: 'Ishq e Strawberry', price: 210, desc: 'Creamy strawberry ice-cream', img: 'assets/images/cup-strawberry-card.png', sizes: ICECREAM_SIZES },
        { id: 'pista', name: 'Shifa e Pista', price: 210, desc: 'Pista ice-cream with a royal touch', img: 'assets/images/cup-pista-card.png', sizes: ICECREAM_SIZES },
        { id: 'mango-masti', name: 'Mango Masti', price: 170, desc: 'Tropical mango swirl ice-cream', img: 'assets/images/cup-orea-card.png', sizes: ICECREAM_SIZES },
        { id: 'lotus', name: 'Lotus', price: 190, desc: 'Creamy lotus biscoff swirl', img: 'assets/images/cup-pista-card.png', sizes: ICECREAM_SIZES },
      ],
    },
    samosas: {
      title: 'Samosas',
      /* sold by the dozen, not by the piece — `price` is per samosa,
         and `sizes` (half/full dozen multipliers) turns the plain
         qty stepper into the pack-size + qty picker from the
         reference: pick a pack, then how many of that pack. */
      items: [
        { id: 'cheesy-tikka', name: 'Cheesy Tikka Samosa', price: 110, desc: 'Cheesy tikka with a spicy twist', img: 'assets/images/samosa-cheesy-tikka.png', sizes: SAMOSA_SIZES },
        { id: 'malai-boti', name: 'Malai Boti Samosa', price: 100, desc: 'Creamy, smoky tikka inside a buttery, flaky crust.', img: 'assets/images/samosa-malai-boti.png', sizes: SAMOSA_SIZES },
        { id: 'pizza', name: 'Pizza Samosa', price: 140, desc: 'Cheesy pizza filling in a crispy samosa', img: 'assets/images/samosa-pizza.png', sizes: SAMOSA_SIZES },
        { id: 'peri-peri', name: 'Peri Peri Samosa', price: 100, desc: 'Spicy peri peri chicken filling', img: 'assets/images/samosa-peri-peri.png', sizes: SAMOSA_SIZES },
        { id: 'chilli-cheese', name: 'Chilli Cheese Samosa', price: 110, desc: 'Loaded with chilli & melted cheese', img: 'assets/images/samosa-chilli-cheese.png', sizes: SAMOSA_SIZES },
      ],
    },
    shakes: {
      title: 'Shakes',
      items: [
        { id: 'chocolate', name: 'Choco Bliss Shake', price: 250, desc: 'Rich chocolate blended thick shake', img: 'assets/images/shake-chocolate.png' },
        { id: 'vanilla', name: 'Khallis Vanilla', price: 230, desc: 'Classic vanilla bean shake', img: 'assets/images/shake-vanilla.png' },
        { id: 'strawberry', name: 'Strawberry Shake', price: 240, desc: 'Fresh strawberry blended shake', img: 'assets/images/shake-strawberry.png' },
      ],
    },
  };

  const modal = document.getElementById('menu-modal');
  const listEl = document.getElementById('menu-modal-list');
  const titleEl = document.getElementById('menu-modal-title');
  const totalEl = document.getElementById('menu-modal-total-value');
  const addBtn = document.getElementById('menu-modal-add');
  const addLabel = addBtn.querySelector('.menu-modal-add-label');
  const notesEl = document.getElementById('menu-modal-notes');

  let currentSection = null;
  let qtyState = {};
  let sizeState = {};

  const unitPrice = (item) => {
    if (!item.sizes) return item.price;
    const size = item.sizes.find((s) => s.id === sizeState[item.id]) || item.sizes[0];
    return item.price * size.mult;
  };

  const renderTotal = () => {
    const section = menuData[currentSection];
    const total = section.items.reduce((sum, item) => sum + unitPrice(item) * (qtyState[item.id] || 0), 0);
    totalEl.textContent = `Rs. ${total}`;
  };

  const renderList = () => {
    const section = menuData[currentSection];
    listEl.innerHTML = '';
    section.items.forEach((item) => {
      const qty = qtyState[item.id] || 0;
      const li = document.createElement('li');
      li.className = 'menu-modal-item';
      const sizeToggleHtml = item.sizes ? `
          <div class="menu-modal-size-toggle">
            ${item.sizes.map((s) => `<button type="button" class="menu-modal-size-btn${s.id === sizeState[item.id] ? ' is-active' : ''}" data-size="${s.id}">${s.label}</button>`).join('')}
          </div>` : '';
      li.innerHTML = `
        <img class="menu-modal-item-img" src="${item.img}" alt="">
        <div class="menu-modal-item-info">
          <p class="menu-modal-item-name">${item.name}</p>
          <p class="menu-modal-item-desc">${item.desc}</p>
          ${sizeToggleHtml}
        </div>
        <div class="menu-modal-item-meta">
          <span class="menu-modal-item-price">Rs. ${unitPrice(item)}</span>
          <div class="menu-modal-stepper">
            <button type="button" class="menu-modal-step menu-modal-step--minus" aria-label="Decrease ${item.name} quantity" ${qty === 0 ? 'disabled' : ''}>&minus;</button>
            <span class="menu-modal-qty">${qty}</span>
            <button type="button" class="menu-modal-step menu-modal-step--plus" aria-label="Increase ${item.name} quantity">+</button>
          </div>
        </div>
      `;
      li.querySelector('.menu-modal-step--minus').addEventListener('click', () => {
        qtyState[item.id] = Math.max(0, (qtyState[item.id] || 0) - 1);
        renderList();
        renderTotal();
      });
      li.querySelector('.menu-modal-step--plus').addEventListener('click', () => {
        qtyState[item.id] = (qtyState[item.id] || 0) + 1;
        renderList();
        renderTotal();
      });
      li.querySelectorAll('.menu-modal-size-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          sizeState[item.id] = btn.dataset.size;
          renderList();
          renderTotal();
        });
      });
      listEl.appendChild(li);
    });
  };

  const openMenu = (sectionKey, preselectId) => {
    currentSection = sectionKey;
    const section = menuData[sectionKey];
    qtyState = {};
    sizeState = {};
    section.items.forEach((item) => {
      qtyState[item.id] = item.id === preselectId ? 1 : 0;
      if (item.sizes) sizeState[item.id] = item.sizes[0].id;
    });

    modal.setAttribute('data-theme', sectionKey);
    titleEl.textContent = section.title;
    notesEl.value = '';
    addBtn.classList.remove('is-added');
    addLabel.textContent = 'Add to Cart';
    renderList();
    renderTotal();

    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('menu-modal-lock');
  };

  const closeMenu = () => {
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('menu-modal-lock');
  };

  modal.querySelectorAll('[data-menu-close]').forEach((el) => el.addEventListener('click', closeMenu));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('is-open')) closeMenu();
  });

  addBtn.addEventListener('click', () => {
    const section = menuData[currentSection];
    section.items.forEach((item) => {
      const qty = qtyState[item.id] || 0;
      if (qty === 0) return;
      if (item.sizes){
        const size = item.sizes.find((s) => s.id === sizeState[item.id]) || item.sizes[0];
        addToCart(currentSection, {
          id: `${item.id}-${size.id}`,
          name: `${item.name} (${size.label})`,
          price: item.price * size.mult,
          img: item.img,
        }, qty);
      } else {
        addToCart(currentSection, item, qty);
      }
    });
    addBtn.classList.add('is-added');
    addLabel.textContent = 'Added!';
    setTimeout(closeMenu, 900);
  });

  document.querySelector('.cups-cta').addEventListener('click', () => {
    const centered = document.querySelector('.cup-card.is-center');
    openMenu('icecreams', (centered && centered.dataset.flavor) || 'strawberry');
  });
  document.querySelector('.samosa-cta').addEventListener('click', () => {
    const centered = document.querySelector('.samosa-card.is-center');
    openMenu('samosas', (centered && centered.dataset.flavor) || 'pizza');
  });
  document.querySelector('.shakes-cta').addEventListener('click', () => {
    const centered = document.querySelector('.shake-card.is-center');
    openMenu('shakes', (centered && centered.dataset.flavor) || 'chocolate');
  });
}
