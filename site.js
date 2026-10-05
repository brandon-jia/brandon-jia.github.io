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
  const focused = tailLinks.find(link => link.matches(':focus-visible'));
  const target = focused || hoveredLink || tailLinks.find(link => link.hasAttribute('aria-current')) || tailLinks[0];
  const parent = navigation.getBoundingClientRect();
  const box = target.getBoundingClientRect();
  const width = Math.min(58, Math.max(0, box.width - 8));
  const destination = box.left - parent.left + (box.width - width) / 2;
  const distance = destination - (tail.getBoundingClientRect().left - parent.left);
  tail.style.setProperty('--tail-x', `${destination}px`);
  tail.style.setProperty('--tail-width', `${width}px`);
  if (lastTailLink && lastTailLink !== target && !motion.matches) {
    const start = getComputedStyle(tailDrawing).transform;
    const tilt = Math.sign(distance) * Math.min(9, 4 + Math.abs(distance) / 40);
    tailDrawing.getAnimations().forEach(animation => animation.cancel());
    tailDrawing.animate([
      {transform:start === 'none' ? 'rotate(0deg)' : start},
      {transform:`rotate(${tilt}deg)`, offset:.3},
      {transform:`rotate(${-tilt * .3}deg)`, offset:.76},
      {transform:'rotate(0deg)'}
    ], {duration:520, easing:'cubic-bezier(.4,0,.2,1)'});
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
