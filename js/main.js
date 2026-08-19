gsap.registerPlugin(ScrollTrigger);

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* =========================================================
   Nav — reveal after the hero intro, highlight active section
   ========================================================= */
const nav = document.getElementById('site-nav');
const navLinks = document.querySelectorAll('.nav-links a');

function setActiveLink(id){
  navLinks.forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#${id}`));
}

document.querySelectorAll('section[id]').forEach(section => {
  ScrollTrigger.create({
    trigger: section,
    start: 'top 55%',
    end: 'bottom 55%',
    onEnter: () => setActiveLink(section.id),
    onEnterBack: () => setActiveLink(section.id),
  });
});

const burger = document.querySelector('.nav-burger');
const navLinksWrap = document.querySelector('.nav-links');
burger?.addEventListener('click', () => {
  const open = navLinksWrap.classList.toggle('is-open');
  burger.setAttribute('aria-expanded', String(open));
});

/* =========================================================
   Hero intro sequence
   "full bg appears, then wordmark rises from front of bg(full)
   and behind bg(front), then wooden floor arrives, then the
   icecream tubs arrive in succession (orea, pista, then
   strawberry lead), background zooms in slowly, then on scroll
   the cream wave rises with a parallax effect."
   ========================================================= */
const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });

heroTl
  .to('.hero-bg-full', { opacity: 1, duration: 1.1 })
  .to('.hero-wordmark', { opacity: 1, y: 0, duration: .9 }, '-=.5')
  .to('.hero-tagline', { opacity: 1, duration: .7 }, '-=.4')
  .to('.hero-bg-front', { opacity: 1, y: 0, duration: .9 }, '-=.5')
  .to('.hero-floor', { y: '0%', duration: .8, ease: 'power2.out' }, '-=.35')
  .to('.hero-tub[data-tub="orea"]', { opacity: 1, y: 0, scale: 1, duration: .65, ease: 'back.out(1.6)' }, '-=.25')
  .to('.hero-tub[data-tub="pista"]', { opacity: 1, y: 0, scale: 1, duration: .65, ease: 'back.out(1.6)' }, '-=.5')
  .to('.hero-tub[data-tub="strawberry"]', { opacity: 1, y: 0, scale: 1, duration: .7, ease: 'back.out(1.7)' }, '-=.35')
  .to('.hero-scroll-cue', { opacity: 1, duration: .5 }, '-=.2')
  .to(nav, { onStart: () => nav.classList.add('is-visible') }, '-=.2');

if (!reduceMotion){
  gsap.to('.hero-bg-full img', {
    scale: 1.12,
    duration: 10,
    ease: 'none',
    delay: 1,
  });
}

/* wave + parallax reveal on scroll out of the hero */
gsap.timeline({
  scrollTrigger: {
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: .6,
  }
})
.to('.hero-wave', { y: '0%', ease: 'none' }, 0)
.to('.hero-bg-front', { y: '-6%', ease: 'none' }, 0)
.to('.hero-bg-full img', { y: '4%', ease: 'none' }, 0)
.to('.hero-tubs', { y: '-8%', ease: 'none' }, 0);

/* =========================================================
   Icecreams section — entrance reveal
   ========================================================= */
gsap.timeline({
  scrollTrigger: { trigger: '.icecreams', start: 'top 75%' }
})
.to('.icecreams-drip', { y: '0%', duration: .7, ease: 'power2.out' })
.to('.section-eyebrow, .section-title, .section-sub', { opacity: 1, y: 0, duration: .6, stagger: .08 }, '-=.3')
.to('.flavor-card', { opacity: 1, y: 0, duration: .7, ease: 'back.out(1.5)', stagger: .12 }, '-=.3')
.to('.btn-pill', { opacity: 1, y: 0, duration: .5 }, '-=.2');

/* =========================================================
   Flavour picking — tint the whole section, dim the rest,
   lift + glow the chosen cup.
   ========================================================= */
const flavorSection = document.getElementById('icecreams');
const flavorCards = document.querySelectorAll('.flavor-card');

flavorCards.forEach(card => {
  const btn = card.querySelector('.flavor-card-btn');
  const tint = card.style.getPropertyValue('--flavor-tint');

  btn.addEventListener('click', () => {
    const alreadyActive = card.classList.contains('is-active');

    flavorCards.forEach(c => c.classList.remove('is-active', 'is-dimmed'));
    btn.setAttribute('aria-pressed', 'false');
    flavorSection.querySelectorAll('.flavor-card-btn').forEach(b => b.setAttribute('aria-pressed', 'false'));

    if (alreadyActive){
      flavorSection.style.setProperty('--tint', '#F1B9C4');
      flavorSection.dataset.flavor = '';
      return;
    }

    card.classList.add('is-active');
    btn.setAttribute('aria-pressed', 'true');
    flavorCards.forEach(c => { if (c !== card) c.classList.add('is-dimmed'); });

    flavorSection.style.setProperty('--tint', tint);
    flavorSection.dataset.flavor = card.dataset.flavor;

    if (!reduceMotion){
      gsap.fromTo('.icecreams-drip', { y: '-100%' }, { y: '0%', duration: .5, ease: 'power2.out' });
    }
  });
});
