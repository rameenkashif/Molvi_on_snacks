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
   page scrolls into the next (empty, cream) section, so the wave's
   rise reads as continuous with that page welling up.
   ========================================================= */
gsap.timeline({
  scrollTrigger: {
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: .6,
  }
})
.to('.hero-wave', { y: '-45%', ease: 'none' }, 0)
.to('.hero-buckets', { y: '-12%', ease: 'none' }, 0)
.to('.hero-wood', { y: '-6%', ease: 'none' }, 0)
.to('.hero-bg-front', { y: '-4%', ease: 'none' }, 0)
.to('.hero-bg-full img', { y: '3%', ease: 'none' }, 0);
