// Infinite scroll pe luni: sentinelul poartă cursorul «YYYY-MM» al lunii
// următoare (mai vechi); când devine vizibil, cerem partialul lunii.
(function () {
  const sentinel = document.getElementById('sentinel');
  if (!sentinel) return;

  const timeline = document.getElementById('timeline');
  const loadingText = sentinel.querySelector('.loading-text');
  let loading = false;

  async function loadNext() {
    const next = sentinel.dataset.next;
    if (!next || loading) return;
    loading = true;
    loadingText.hidden = false;
    try {
      const resp = await fetch(sentinel.dataset.url + '?month=' + encodeURIComponent(next));
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      timeline.insertAdjacentHTML('beforeend', data.html);
      if (data.next) {
        sentinel.dataset.next = data.next;
      } else {
        delete sentinel.dataset.next;
        observer.disconnect();
      }
    } catch (err) {
      console.error('Eroare la încărcarea lunii:', err);
    } finally {
      loading = false;
      loadingText.hidden = true;
      // Dacă sentinelul e încă vizibil (pagina nu s-a umplut), continuă.
      if (sentinel.dataset.next && isVisible(sentinel)) loadNext();
    }
  }

  function isVisible(el) {
    const r = el.getBoundingClientRect();
    return r.top < window.innerHeight + 200;
  }

  const observer = new IntersectionObserver(
    entries => { if (entries.some(e => e.isIntersecting)) loadNext(); },
    { rootMargin: '200px' }
  );
  observer.observe(sentinel);
})();
