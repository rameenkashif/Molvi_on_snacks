gsap.registerPlugin(ScrollTrigger);

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* =========================================================
   Hero intro sequence
   1. full background appears
   2. front background (mountains) settles in, sandwiching the
      wordmark between the two layers
   3. the wordmark rises up, as if climbing from behind the front
      mountains and out in front of the full background
   ========================================================= */
document.querySelector('.hero').classList.add('is-loaded');

const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });

heroTl
  .to('.hero-bg-full', { opacity: 1, duration: 1.2 })
  .to('.hero-bg-front', { opacity: 1, duration: 1, ease: 'power2.out' }, '-=.5')
  .to('.hero-wordmark', { opacity: 1, duration: .3 }, '-=.3')
  .to('.hero-wordmark', { y: 0, duration: 1.4, ease: 'power4.out' }, '<');

if (!reduceMotion){
  gsap.to('.hero-bg-full img', {
    scale: 1.12,
    duration: 12,
    ease: 'none',
    delay: 1,
  });
}
