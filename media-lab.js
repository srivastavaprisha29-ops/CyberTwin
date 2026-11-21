const byId = id => document.getElementById(id);
const reference = byId('media-reference');
const candidate = byId('media-candidate');
const compare = byId('media-compare');
const comparison = byId('media-result');

async function digest(file) {
  const buffer = await file.arrayBuffer();
  const hash = await crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
}

compare.addEventListener('click', async () => {
  const files = [reference.files[0], candidate.files[0]];
  if (files.some(file => !file)) {
    comparison.textContent = 'Choose both files first.';
    return;
  }
  if (files.some(file => file.size > 25 * 1024 * 1024)) {
    comparison.textContent = 'Choose files of 25 MB or smaller.';
    return;
  }
  compare.disabled = reference.disabled = candidate.disabled = true;
  comparison.textContent = 'Comparing SHA-256 fingerprints…';
  try {
    const [first, second] = await Promise.all(files.map(digest));
    comparison.textContent = first === second
      ? 'Fingerprints match. Both files have the same bytes.'
      : 'Fingerprints differ. Editing, metadata changes, or re-encoding can change a fingerprint.';
  } catch {
    comparison.textContent = 'Could not read or hash the files. Try again over HTTPS or localhost.';
  } finally {
    compare.disabled = reference.disabled = candidate.disabled = false;
  }
});
for (const input of [reference, candidate]) {
  input.addEventListener('change', () => { comparison.textContent = ''; });
}

const compress = byId('media-compress');
const quality = byId('media-quality');
const compression = byId('media-compression');

compress.addEventListener('click', async () => {
  compress.disabled = quality.disabled = true;
  try {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 96;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    const original = context.createImageData(96, 96);
    for (let offset = 0; offset < original.data.length; offset += 4) {
      const column = (offset / 4) % 96;
      const row = Math.floor(offset / 384);
      original.data[offset] = (column * 37 + row * 13) % 256;
      original.data[offset + 1] = (column * 11 + row * 17) % 256;
      original.data[offset + 2] = (column * 23 + row * 7) % 256;
      original.data[offset + 3] = 255;
    }
    context.putImageData(original, 0, 0);
    const image = new Image();
    image.src = canvas.toDataURL('image/jpeg', Number(quality.value));
    await image.decode();
    context.drawImage(image, 0, 0);
    const decoded = context.getImageData(0, 0, 96, 96).data;
    let difference = 0;
    for (let offset = 0; offset < decoded.length; offset += 4) {
      for (let channel = 0; channel < 3; channel++) {
        difference += Math.abs(decoded[offset + channel] - original.data[offset + channel]);
      }
    }
    compression.textContent = 'Mean RGB channel change: ' + (difference / (96 * 96 * 3)).toFixed(2) + ' / 255.';
  } catch {
    compression.textContent = 'This browser could not run the JPEG experiment.';
  } finally {
    compress.disabled = quality.disabled = false;
  }
});
quality.addEventListener('change', () => { compression.textContent = ''; });
