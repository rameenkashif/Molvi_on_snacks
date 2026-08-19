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
  // once it's finished rising, bring it in front of the mountains for
  // good — guarantees the full logo reads at rest on every screen size,
  // regardless of exactly where the ridge line falls
  .set('.hero-wordmark', { zIndex: 4 });

if (!reduceMotion){
  gsap.to('.hero-bg-full img', {
    scale: 1.12,
    duration: 12,
    ease: 'none',
    delay: 1,
  });
}
