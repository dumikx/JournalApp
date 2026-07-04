// Lightbox pentru galeria unei intrări: săgeți, swipe pe mobil, ESC, download.
(function () {
  const items = Array.from(document.querySelectorAll('.gallery-item'));
  const lightbox = document.getElementById('lightbox');
  if (!items.length || !lightbox) return;

  const img = document.getElementById('lightbox-img');
  const download = document.getElementById('lightbox-download');
  let current = 0;

  function show(index) {
    current = (index + items.length) % items.length;
    const item = items[current];
    img.src = item.dataset.display;
    download.href = item.dataset.original;
    lightbox.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function close() {
    lightbox.hidden = true;
    img.src = '';
    document.body.style.overflow = '';
  }

  items.forEach(item => {
    item.addEventListener('click', () => show(parseInt(item.dataset.index, 10)));
  });

  lightbox.querySelector('.lightbox-close').addEventListener('click', close);
  lightbox.querySelector('.lightbox-prev').addEventListener('click', e => {
    e.stopPropagation(); show(current - 1);
  });
  lightbox.querySelector('.lightbox-next').addEventListener('click', e => {
    e.stopPropagation(); show(current + 1);
  });
  lightbox.addEventListener('click', e => {
    if (e.target === lightbox) close();
  });

  document.addEventListener('keydown', e => {
    if (lightbox.hidden) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft') show(current - 1);
    else if (e.key === 'ArrowRight') show(current + 1);
  });

  // Swipe pe mobil.
  let touchX = null;
  lightbox.addEventListener('touchstart', e => {
    touchX = e.changedTouches[0].clientX;
  }, { passive: true });
  lightbox.addEventListener('touchend', e => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    touchX = null;
    if (Math.abs(dx) > 50) show(current + (dx < 0 ? 1 : -1));
  }, { passive: true });
})();
