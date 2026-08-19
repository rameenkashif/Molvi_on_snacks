gsap.registerPlugin(ScrollTrigger);

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
  .to('.hero-scroll-cue', { opacity: 1, duration: .5 }, '-=.2');

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
