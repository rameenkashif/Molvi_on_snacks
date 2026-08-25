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
  .to('.site-nav', { opacity: 1, y: 0, duration: .8 }, 0)
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
  .to('.cup-card-bg', { opacity: 1, y: 0, duration: .6, stagger: .15 }, '-=.25')
  .to('.cup-card-label', { opacity: 1, y: 0, duration: .5, stagger: .15 }, '-=.4')
  .to(['.cup-card--orea .cup-card-img', '.cup-card--pista .cup-card-img'], {
    opacity: 1, duration: .15, stagger: .16,
  }, '-=.15')
  .to(['.cup-card--orea .cup-card-img', '.cup-card--pista .cup-card-img'], {
    scale: 1, duration: .7, ease: 'back.out(2.4)', stagger: .16,
  }, '<')
  .to('.cup-card--strawberry .cup-card-img', { opacity: 1, duration: .15 }, '-=.3')
  .to('.cup-card--strawberry .cup-card-img', {
    scale: 1, duration: .75, ease: 'back.out(2.6)',
  }, '<')
  .to('.cups-cta', { opacity: 1, y: 0, duration: .6 }, '-=.2');

/* =========================================================
   Flavour cards — hover tilt. Each cup leans slightly away from
   its own base on hover, outer cups tilting outward and the
   centred strawberry cup tilting toward the strawberry side.
   ========================================================= */
if (!reduceMotion){
  const tiltByFlavour = { orea: -8, pista: 8, strawberry: -6 };
  document.querySelectorAll('.cup-card').forEach((card) => {
    const img = card.querySelector('.cup-card-img');
    const flavour = Object.keys(tiltByFlavour).find((f) => card.classList.contains(`cup-card--${f}`));
    const tilt = tiltByFlavour[flavour] || 0;
    card.addEventListener('mouseenter', () => {
      gsap.to(img, { rotation: tilt, duration: .4, ease: 'power2.out' });
    });
    card.addEventListener('mouseleave', () => {
      gsap.to(img, { rotation: 0, duration: .5, ease: 'power2.out' });
    });
  });
}

/* =========================================================
   Site nav — always visible, on the hero included. It carries real
   ordering controls now (delivery/pick-up, delivery-area picker),
   not just section links, so hiding it until the visitor scrolls
   past the hero (the previous behaviour) meant those controls were
   unreachable on first load — the same as the nav being broken.
   ========================================================= */

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
   Flavour cards — click to select. Picking a cup sets --active-bg on
   the document root, so the section background, the hero wave above
   it, and the drip edge below it all retint together to that
   flavour's colour; the cup itself is called out (scaled up, glowing)
   while the other two recede. Clicking the selected cup again clears
   the selection everywhere.
   ========================================================= */
{
  const flavourColors = { orea: '#ecd9b3', strawberry: '#f6c2ce', pista: '#bcc684' };
  const root = document.documentElement;
  const nextPage = document.querySelector('.next-page');
  const cupCards = document.querySelectorAll('.cup-card');

  const selectCard = (card) => {
    const alreadySelected = card.classList.contains('is-selected');
    cupCards.forEach((c) => {
      c.classList.remove('is-selected');
      c.setAttribute('aria-pressed', 'false');
      // the scroll-reveal timeline left an inline opacity:1 on this via
      // GSAP, which a plain CSS rule can't outrank — reset it here too.
      gsap.to(c.querySelector('.cup-card-bg'), { opacity: 1, duration: .3 });
    });

    if (alreadySelected){
      nextPage.classList.remove('has-selection');
      root.style.removeProperty('--active-bg');
      return;
    }

    const flavour = Object.keys(flavourColors).find((f) => card.classList.contains(`cup-card--${f}`));
    card.classList.add('is-selected');
    card.setAttribute('aria-pressed', 'true');
    nextPage.classList.add('has-selection');
    root.style.setProperty('--active-bg', flavourColors[flavour]);
    gsap.to(card.querySelector('.cup-card-bg'), { opacity: 0, duration: .3 });
  };

  cupCards.forEach((card) => {
    card.addEventListener('click', () => selectCard(card));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' '){
        e.preventDefault();
        selectCard(card);
      }
    });
  });
}

/* =========================================================
   Samosas — heading and the three-up selector fade/pop in once the
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
  .to('.samosa-card-label', { opacity: 1, y: 0, duration: .5, stagger: .15 }, '-=.25')
  .to('.samosa-card-img', { opacity: 1, scale: 1, duration: .7, ease: 'back.out(2.2)', stagger: .16 }, '-=.4')
  .to('.samosa-cta', { opacity: 1, y: 0, duration: .6 }, '-=.2');

/* =========================================================
   Samosas — click to select, hover to tilt: the exact same
   interaction as the icecream cups. Selecting one calls it out
   (scaled up, glowing) while the other two recede; clicking the
   selected one again clears the selection. Each samosa tilts
   slightly away from its own base on hover.
   ========================================================= */
{
  const samosaRow = document.querySelector('.samosa-row');
  const samosaCards = document.querySelectorAll('.samosa-card');

  const selectSamosa = (card) => {
    const alreadySelected = card.classList.contains('is-selected');
    samosaCards.forEach((c) => {
      c.classList.remove('is-selected');
      c.setAttribute('aria-pressed', 'false');
    });

    if (alreadySelected){
      samosaRow.classList.remove('has-selection');
      return;
    }

    card.classList.add('is-selected');
    card.setAttribute('aria-pressed', 'true');
    samosaRow.classList.add('has-selection');
  };

  samosaCards.forEach((card) => {
    card.addEventListener('click', () => selectSamosa(card));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' '){
        e.preventDefault();
        selectSamosa(card);
      }
    });
  });

  if (!reduceMotion){
    const tiltBySamosa = { pizza: -8, peri: 8, fajita: -6 };
    samosaCards.forEach((card) => {
      const img = card.querySelector('.samosa-card-img');
      const flavour = Object.keys(tiltBySamosa).find((f) => card.classList.contains(`samosa-card--${f}`));
      const tilt = tiltBySamosa[flavour] || 0;
      card.addEventListener('mouseenter', () => {
        gsap.to(img, { rotation: tilt, duration: .4, ease: 'power2.out' });
      });
      card.addEventListener('mouseleave', () => {
        gsap.to(img, { rotation: 0, duration: .5, ease: 'power2.out' });
      });
    });
  }
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
   Shakes — click to select, hover to tilt: the exact same
   interaction as the icecream cups and samosas. Selecting one calls
   it out (scaled up, glowing) while the other two recede; clicking
   the selected one again clears the selection.
   ========================================================= */
{
  const shakesRow = document.querySelector('.shakes-row');
  const shakeCards = document.querySelectorAll('.shake-card');

  const selectShake = (card) => {
    const alreadySelected = card.classList.contains('is-selected');
    shakeCards.forEach((c) => {
      c.classList.remove('is-selected');
      c.setAttribute('aria-pressed', 'false');
    });

    if (alreadySelected){
      shakesRow.classList.remove('has-selection');
      return;
    }

    card.classList.add('is-selected');
    card.setAttribute('aria-pressed', 'true');
    shakesRow.classList.add('has-selection');
  };

  shakeCards.forEach((card) => {
    card.addEventListener('click', () => selectShake(card));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' '){
        e.preventDefault();
        selectShake(card);
      }
    });
  });

  if (!reduceMotion){
    const tiltByShake = { chocolate: -8, vanilla: 8, strawberry: -6 };
    shakeCards.forEach((card) => {
      const img = card.querySelector('.shake-card-img');
      const flavour = Object.keys(tiltByShake).find((f) => card.classList.contains(`shake-card--${f}`));
      const tilt = tiltByShake[flavour] || 0;
      card.addEventListener('mouseenter', () => {
        gsap.to(img, { rotation: tilt, duration: .4, ease: 'power2.out' });
      });
      card.addEventListener('mouseleave', () => {
        gsap.to(img, { rotation: 0, duration: .5, ease: 'power2.out' });
      });
    });
  }
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
  const menuData = {
    icecreams: {
      title: 'Ice-Creams',
      items: [
        { id: 'orea', name: 'Orea Barkat', price: 150, desc: 'Oreo chunks in creamy vanilla', img: 'assets/images/cup-orea-card.png' },
        { id: 'strawberry', name: 'Ishq e Strawberry', price: 210, desc: 'Creamy strawberry ice-cream', img: 'assets/images/cup-strawberry-card.png' },
        { id: 'pista', name: 'Shifa e Pista', price: 210, desc: 'Pista ice-cream with a royal touch', img: 'assets/images/cup-pista-card.png' },
      ],
    },
    samosas: {
      title: 'Samosas',
      items: [
        { id: 'pizza', name: 'Pizza Samosa', price: 140, desc: 'Cheesy pizza filling in a crispy samosa', img: 'assets/images/samosa-pizza.png' },
        { id: 'peri', name: 'Peri Peri Samosa', price: 100, desc: 'Spicy peri peri chicken filling', img: 'assets/images/samosa-peri-peri.png' },
        { id: 'fajita', name: 'Fajita Samosa', price: 120, desc: 'Zesty chicken fajita filling in a crispy shell', img: 'assets/images/samosa-fajita.png' },
      ],
    },
    shakes: {
      title: 'Shakes',
      items: [
        { id: 'chocolate', name: 'Chocolate Shake', price: 250, desc: 'Rich chocolate blended thick shake', img: 'assets/images/shake-chocolate.png' },
        { id: 'vanilla', name: 'Vanilla Shake', price: 230, desc: 'Classic vanilla bean shake', img: 'assets/images/shake-vanilla.png' },
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

  const renderTotal = () => {
    const section = menuData[currentSection];
    const total = section.items.reduce((sum, item) => sum + item.price * (qtyState[item.id] || 0), 0);
    totalEl.textContent = `Rs. ${total}`;
  };

  const renderList = () => {
    const section = menuData[currentSection];
    listEl.innerHTML = '';
    section.items.forEach((item) => {
      const qty = qtyState[item.id] || 0;
      const li = document.createElement('li');
      li.className = 'menu-modal-item';
      li.innerHTML = `
        <img class="menu-modal-item-img" src="${item.img}" alt="">
        <div class="menu-modal-item-info">
          <p class="menu-modal-item-name">${item.name}</p>
          <p class="menu-modal-item-desc">${item.desc}</p>
        </div>
        <div class="menu-modal-item-meta">
          <span class="menu-modal-item-price">Rs. ${item.price}</span>
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
      listEl.appendChild(li);
    });
  };

  const openMenu = (sectionKey, preselectId) => {
    currentSection = sectionKey;
    const section = menuData[sectionKey];
    qtyState = {};
    section.items.forEach((item) => { qtyState[item.id] = item.id === preselectId ? 1 : 0; });

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
      if (qty > 0) addToCart(currentSection, item, qty);
    });
    addBtn.classList.add('is-added');
    addLabel.textContent = 'Added!';
    setTimeout(closeMenu, 900);
  });

  const selectedFlavour = (cards, prefix) => {
    let found = null;
    cards.forEach((card) => {
      if (card.classList.contains('is-selected')){
        found = [...card.classList].find((cls) => cls.startsWith(prefix))?.slice(prefix.length);
      }
    });
    return found;
  };

  document.querySelector('.cups-cta').addEventListener('click', () => {
    const cards = document.querySelectorAll('.cup-card');
    openMenu('icecreams', selectedFlavour(cards, 'cup-card--') || 'orea');
  });
  document.querySelector('.samosa-cta').addEventListener('click', () => {
    const cards = document.querySelectorAll('.samosa-card');
    openMenu('samosas', selectedFlavour(cards, 'samosa-card--') || 'pizza');
  });
  document.querySelector('.shakes-cta').addEventListener('click', () => {
    const cards = document.querySelectorAll('.shake-card');
    openMenu('shakes', selectedFlavour(cards, 'shake-card--') || 'chocolate');
  });
}
