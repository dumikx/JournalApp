// Upload poze: redimensionare client-side → presigned PUT direct în R2
// (original + display) → confirmare la backend. Progress + retry per poză.
(function () {
  const manager = document.getElementById('photo-manager');
  if (!manager) return;

  const entryId = manager.dataset.entryId;
  const MAX_PHOTOS = parseInt(manager.dataset.maxPhotos, 10);
  const MAX_SIZE = parseInt(manager.dataset.maxSize, 10);
  const MAX_SIDE = 2560;
  const JPEG_QUALITY = 0.85;

  const input = document.getElementById('photo-input');
  const queue = document.getElementById('upload-queue');
  const photoList = document.getElementById('photo-list');
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  function api(url, options = {}) {
    options.headers = Object.assign(
      { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      options.headers || {}
    );
    return fetch(url, options);
  }

  function photoCount() {
    return photoList.querySelectorAll('.photo-item').length;
  }

  // ---------- redimensionare ----------
  async function makeDisplayBlob(file) {
    const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const scale = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bmp.width * scale));
    canvas.height = Math.max(1, Math.round(bmp.height * scale));
    canvas.getContext('2d').drawImage(bmp, 0, 0, canvas.width, canvas.height);
    bmp.close();
    return new Promise((resolve, reject) => {
      canvas.toBlob(
        blob => (blob ? resolve(blob) : reject(new Error('toBlob a eșuat'))),
        'image/jpeg',
        JPEG_QUALITY
      );
    });
  }

  // ---------- PUT cu progres ----------
  function putWithProgress(url, blob, contentType, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('PUT', url);
      xhr.setRequestHeader('Content-Type', contentType);
      xhr.upload.addEventListener('progress', e => {
        if (e.lengthComputable) onProgress(e.loaded, e.total);
      });
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve();
        else reject(new Error('R2 a răspuns cu ' + xhr.status));
      });
      xhr.addEventListener('error', () => reject(new Error('Eroare de rețea')));
      xhr.send(blob);
    });
  }

  // ---------- UI pentru coada de upload ----------
  function makeQueueItem(name) {
    const li = document.createElement('li');
    li.className = 'upload-item';
    li.innerHTML =
      '<span class="upload-name"></span>' +
      '<progress max="100" value="0"></progress>' +
      '<span class="upload-status"></span>' +
      '<button type="button" class="btn-icon upload-retry" hidden title="Reîncearcă">↻</button>';
    li.querySelector('.upload-name').textContent = name;
    queue.appendChild(li);
    return li;
  }

  // ---------- fluxul per poză ----------
  async function uploadOne(file, li) {
    const progress = li.querySelector('progress');
    const status = li.querySelector('.upload-status');
    const retryBtn = li.querySelector('.upload-retry');
    retryBtn.hidden = true;
    status.textContent = 'se pregătește…';

    try {
      const displayBlob = await makeDisplayBlob(file);

      const presignResp = await api(`/api/entries/${entryId}/photos/presign`, {
        method: 'POST',
        body: JSON.stringify({
          photos: [{ content_type: file.type || 'image/jpeg', size: file.size }],
        }),
      });
      if (!presignResp.ok) {
        const err = await presignResp.json().catch(() => ({}));
        throw new Error(err.error || 'Presign a eșuat');
      }
      const { photos: [ticket] } = await presignResp.json();

      // Progres combinat: originalul + versiunea display.
      const totals = { orig: file.size, disp: displayBlob.size };
      const loaded = { orig: 0, disp: 0 };
      const update = () => {
        const pct =
          ((loaded.orig + loaded.disp) / (totals.orig + totals.disp)) * 100;
        progress.value = Math.round(pct);
      };

      status.textContent = 'se încarcă…';
      await Promise.all([
        putWithProgress(ticket.original.url, file, ticket.original.content_type,
          (l) => { loaded.orig = l; update(); }),
        putWithProgress(ticket.display.url, displayBlob, 'image/jpeg',
          (l) => { loaded.disp = l; update(); }),
      ]);

      status.textContent = 'se confirmă…';
      const confirmResp = await api(`/api/entries/${entryId}/photos/confirm`, {
        method: 'POST',
        body: JSON.stringify({
          photos: [{
            key_original: ticket.original.key,
            key_display: ticket.display.key,
          }],
        }),
      });
      if (!confirmResp.ok) {
        const err = await confirmResp.json().catch(() => ({}));
        throw new Error(err.error || 'Confirmarea a eșuat');
      }
      const { photos: [created] } = await confirmResp.json();

      addPhotoItem(created.id, created.display_url);
      li.remove();
    } catch (err) {
      status.textContent = 'eroare: ' + err.message;
      retryBtn.hidden = false;
      retryBtn.onclick = () => uploadOne(file, li);
    }
  }

  input.addEventListener('change', async () => {
    const files = Array.from(input.files);
    input.value = '';
    if (!files.length) return;

    const remaining = MAX_PHOTOS - photoCount() - queue.children.length;
    if (files.length > remaining) {
      alert(`Poți adăuga cel mult ${Math.max(0, remaining)} poze (limita e ${MAX_PHOTOS} per intrare).`);
      return;
    }

    for (const file of files) {
      if (!file.type.startsWith('image/')) {
        alert(`«${file.name}» nu e imagine — a fost sărit.`);
        continue;
      }
      if (file.size > MAX_SIZE) {
        alert(`«${file.name}» depășește 25MB — a fost sărit.`);
        continue;
      }
      const li = makeQueueItem(file.name);
      // Secvențial, ca să nu deschidem zeci de conexiuni pe mobil.
      await uploadOne(file, li);
    }
  });

  // ---------- management poze existente ----------
  function addPhotoItem(id, displayUrl) {
    const li = document.createElement('li');
    li.className = 'photo-item';
    li.dataset.photoId = id;
    li.innerHTML =
      '<img alt="">' +
      '<div class="photo-item-actions">' +
      '<button type="button" class="btn-icon photo-up" title="Mută sus">↑</button>' +
      '<button type="button" class="btn-icon photo-down" title="Mută jos">↓</button>' +
      '<button type="button" class="btn-icon photo-delete" title="Șterge">✕</button>' +
      '</div>';
    li.querySelector('img').src = displayUrl;
    photoList.appendChild(li);
  }

  async function saveOrder() {
    const order = Array.from(photoList.querySelectorAll('.photo-item')).map(li =>
      parseInt(li.dataset.photoId, 10)
    );
    const resp = await api(`/api/entries/${entryId}/photos/reorder`, {
      method: 'POST',
      body: JSON.stringify({ order }),
    });
    if (!resp.ok) alert('Reordonarea nu a putut fi salvată.');
  }

  photoList.addEventListener('click', async e => {
    const li = e.target.closest('.photo-item');
    if (!li) return;

    if (e.target.classList.contains('photo-delete')) {
      if (!confirm('Ștergi această poză?')) return;
      const resp = await api(`/api/photos/${li.dataset.photoId}`, { method: 'DELETE' });
      if (resp.ok) li.remove();
      else alert('Poza nu a putut fi ștearsă.');
    } else if (e.target.classList.contains('photo-up')) {
      const prev = li.previousElementSibling;
      if (prev) { photoList.insertBefore(li, prev); await saveOrder(); }
    } else if (e.target.classList.contains('photo-down')) {
      const next = li.nextElementSibling;
      if (next) { photoList.insertBefore(next, li); await saveOrder(); }
    }
  });
})();
