'use strict';
const root = document.documentElement;
const header = document.querySelector('.bar');
const progress = document.querySelector('.prog');
const motion = matchMedia('(prefers-reduced-motion: reduce)');
const navigation = document.querySelector('.bar nav');
const tailLinks = [...(navigation?.querySelectorAll('a:not(.cv)') || [])];
let tail, tailDrawing, hoveredLink, lastTailLink;
if (tailLinks.length) {
  tail = document.createElement('i');
  tail.className = 'nav-tail';
  tail.setAttribute('aria-hidden', 'true');
  tailDrawing = document.createElement('i');
  tail.append(tailDrawing);
  navigation.append(tail);
  document.body.classList.add('nav-motion');
  for (const link of tailLinks) {
    link.addEventListener('pointerenter', () => { hoveredLink = link; moveTail(); });
    link.addEventListener('focus', moveTail);
    link.addEventListener('blur', () => requestAnimationFrame(moveTail));
  }
  navigation.addEventListener('pointerleave', () => { hoveredLink = null; moveTail(); });
  motion.addEventListener('change', () => {
    if (motion.matches) tailDrawing.getAnimations().forEach(animation => animation.cancel());
    moveTail();
  });
}
function moveTail() {
  if (!tail) return;
  const focused = tailLinks.find(link => link.matches(':focus'));
  const target = focused || hoveredLink || tailLinks.find(link => link.hasAttribute('aria-current'));
  if (!target) {
    tail.style.opacity = '0';
    return;
  }
  tail.style.opacity = '1';
  const parent = navigation.getBoundingClientRect();
  const box = target.getBoundingClientRect();
  const width = Math.min(58, Math.max(0, box.width - 8));
  const destination = box.left - parent.left + (box.width - width) / 2;
  const distance = destination - (tail.getBoundingClientRect().left - parent.left);
  tail.style.setProperty('--tail-x', `${destination}px`);
  tail.style.setProperty('--tail-width', `${width}px`);
  const scale = width / 58;
  tail.style.setProperty('--tail-scale', scale);
  if (lastTailLink && lastTailLink !== target && !motion.matches) {
    const start = getComputedStyle(tailDrawing).transform;
    const tilt = Math.sign(distance) * Math.min(9, 4 + Math.abs(distance) / 40);
    tailDrawing.getAnimations().forEach(animation => animation.cancel());
    tailDrawing.animate([
      {transform:start === 'none' ? `scaleX(${scale})` : start},
      {transform:`rotate(${tilt}deg) scaleX(${scale})`, offset:.3},
      {transform:`rotate(${-tilt * .3}deg) scaleX(${scale})`, offset:.76},
      {transform:`rotate(0deg) scaleX(${scale})`}
    ], {duration:520, easing:'cubic-bezier(.16,1,.3,1)'});
  }
  lastTailLink = target;
}
const sections = [...document.querySelectorAll('nav a[href^="#"]')]
  .map(link => ({link, section:document.querySelector(link.hash)}))
  .filter(item => item.section);
let queued = false;
function updateScroll() {
  queued = false;
  const distance = root.scrollHeight - innerHeight;
  const fraction = distance > 0 ? Math.max(0, Math.min(1, scrollY / distance)) : 0;
  if (progress) progress.style.transform = `scaleX(${fraction})`;
  if (header) header.classList.toggle('is-scrolled', scrollY > 8);
  let active = sections[0];
  const readingLine = (header?.getBoundingClientRect().bottom || 52) + 72;
  for (const item of sections) {
    if (item.section.getBoundingClientRect().top <= readingLine) active = item;
  }
  for (const item of sections) {
    if (item === active) item.link.setAttribute('aria-current', 'location');
    else item.link.removeAttribute('aria-current');
  }
  moveTail();
}
function scheduleScroll() {
  if (!queued) {
    queued = true;
    requestAnimationFrame(updateScroll);
  }
}
addEventListener('scroll', scheduleScroll, {passive:true});
addEventListener('resize', scheduleScroll);
addEventListener('load', scheduleScroll);
document.fonts?.ready.then(scheduleScroll);
document.querySelector('.mk[href="#top"]')?.addEventListener('click', event => {
  event.preventDefault();
  history.replaceState(null, '', '#top');
  scrollTo({top:0, behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
});
updateScroll();

// Read actual scroll displacement before scheduling the spring's first frame.
// Reset immediately if the visitor changes their motion preference.
(() => {
  let lastY = scrollY, tilt = 0, frame = 0;
  const step = () => {
    if (motion.matches) return reset();
    const velocity = scrollY - lastY;
    lastY = scrollY;
    const target = -Math.max(-12, Math.min(12, velocity * .5));
    tilt += (target - tilt) * .16;
    root.style.setProperty('--tail-tilt', `${tilt.toFixed(2)}deg`);
    if (Math.abs(tilt) > .05 || velocity !== 0) frame = requestAnimationFrame(step);
    else reset();
  };
  function reset() {
    cancelAnimationFrame(frame);
    frame = 0; tilt = 0; lastY = scrollY;
    root.style.setProperty('--tail-tilt', '0deg');
  }
  addEventListener('scroll', () => {
    if (motion.matches) return reset();
    if (!frame) frame = requestAnimationFrame(step);
  }, {passive:true});
  motion.addEventListener('change', reset);
})();

(() => {
  const reveal = (selector, className, options) => {
    const items = document.querySelectorAll(selector);
    if (!items.length) return;
    if (!('IntersectionObserver' in window)) {
      items.forEach(element => element.classList.add(className));
      return;
    }
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add(className);
        observer.unobserve(entry.target);
      }
    }), options);
    items.forEach(element => observer.observe(element));
  };
  reveal('h2', 'in', {threshold:.6});
  reveal('.exp', 'on', {rootMargin:'0px 0px -38% 0px',threshold:0});
  reveal('footer .ledge', 'up', {threshold:.35});
})();
