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
  .to(['.cup-card--orea .cup-card-img', '.cup-card--pista .cup-card-img'], {
    opacity: 1, duration: .15, stagger: .16,
  }, '-=.15')
  .to(['.cup-card--orea .cup-card-img', '.cup-card--pista .cup-card-img'], {
    scale: 1, duration: .7, ease: 'back.out(2.4)', stagger: .16,
  }, '<')
  .to('.cup-card--strawberry .cup-card-img', { opacity: 1, duration: .15 }, '-=.3')
  .to('.cup-card--strawberry .cup-card-img', {
    scale: 1, duration: .75, ease: 'back.out(2.6)',
  }, '<');

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
   Site nav — slides down from off-screen once the hero (and its
   closing wave) has scrolled fully out of frame, i.e. once
   .next-page's top edge reaches the top of the viewport.
   ========================================================= */
gsap.set('.site-nav', { xPercent: -50, yPercent: -100 });

ScrollTrigger.create({
  trigger: '.next-page',
  start: 'top top+=50',
  onEnter: () => gsap.to('.site-nav', { yPercent: 0, duration: .5, ease: 'power3.out' }),
  onLeaveBack: () => gsap.to('.site-nav', { yPercent: -100, duration: .4, ease: 'power3.in' }),
});

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
