// RollCallFace — thin wrapper around face-api.js for two flows:
//   1. Enrollment: capture one good descriptor and save it to the account.
//   2. Check-in: continuously look for a face, then submit descriptor +
//      location to the server, which does the actual matching/geofencing.
//
// Models are loaded client-side from a public CDN — nothing to download
// into this project, and no descriptor data ever needs to be computed
// server-side.

const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model';

const RollCallFace = (() => {
  async function loadModels(statusEl) {
    if (statusEl) statusEl.textContent = 'Loading face model…';
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
      faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
      faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
    ]);
  }

  async function startVideo(videoEl) {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 420, height: 315, facingMode: 'user' },
    });
    videoEl.srcObject = stream;
    return new Promise((resolve) => {
      videoEl.onloadedmetadata = () => resolve();
    });
  }

  async function detectDescriptor(videoEl) {
    const result = await faceapi
      .detectSingleFace(videoEl, new faceapi.TinyFaceDetectorOptions({ inputSize: 224 }))
      .withFaceLandmarks()
      .withFaceDescriptor();
    return result || null;
  }

  // ------------------------------------------------------------------
  // Enrollment page
  // ------------------------------------------------------------------
  async function initEnrollPage({ videoId, ringId, statusId, buttonId, saveUrl, onSaved }) {
    const video = document.getElementById(videoId);
    const ring = document.getElementById(ringId);
    const status = document.getElementById(statusId);
    const button = document.getElementById(buttonId);

    try {
      await loadModels(status);
      await startVideo(video);
    } catch (e) {
      status.textContent = 'Could not access the camera: ' + e.message;
      return;
    }

    status.textContent = 'Centre your face in the frame.';
    ring.classList.add('scanning');
    button.disabled = false;

    let lastDetection = null;
    setInterval(async () => {
      const d = await detectDescriptor(video);
      lastDetection = d;
      if (d) {
        ring.classList.remove('scanning');
        ring.classList.add('match');
        status.textContent = 'Face detected — ready to capture.';
      } else {
        ring.classList.remove('match');
        ring.classList.add('scanning');
        status.textContent = 'No face detected — centre your face in the frame.';
      }
    }, 500);

    button.addEventListener('click', async () => {
      button.disabled = true;
      status.textContent = 'Capturing…';
      const d = lastDetection || (await detectDescriptor(video));
      if (!d) {
        status.textContent = 'No face detected — try again.';
        button.disabled = false;
        return;
      }
      const descriptor = Array.from(d.descriptor);
      const res = await fetch(saveUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ descriptor }),
      });
      const data = await res.json();
      if (data.ok) {
        status.textContent = 'Face saved.';
        onSaved && onSaved();
      } else {
        status.textContent = 'Could not save face — try again.';
        button.disabled = false;
      }
    });
  }

  // ------------------------------------------------------------------
  // Check-in page
  // ------------------------------------------------------------------
  async function initCheckInPage({
    videoId, ringId, statusId, resultId, geoChipId, anywhereMode, pollId, submitUrl, onSuccess,
  }) {
    const video = document.getElementById(videoId);
    const ring = document.getElementById(ringId);
    const status = document.getElementById(statusId);
    const resultBox = document.getElementById(resultId);
    const geoChip = geoChipId ? document.getElementById(geoChipId) : null;

    let coords = { latitude: null, longitude: null };

    if (!anywhereMode) {
      try {
        const pos = await getCurrentPosition();
        coords.latitude = pos.coords.latitude;
        coords.longitude = pos.coords.longitude;
        if (geoChip) geoChip.textContent = `📍 location locked (±${Math.round(pos.coords.accuracy)} m)`;
      } catch (e) {
        if (geoChip) geoChip.textContent = '📍 location access denied — cannot check in';
        status.textContent = 'Location access is required for this poll.';
        return;
      }
    }

    try {
      await loadModels(status);
      await startVideo(video);
    } catch (e) {
      status.textContent = 'Could not access the camera: ' + e.message;
      return;
    }

    status.textContent = 'Centre your face in the frame.';
    ring.classList.add('scanning');

    let busy = false;
    let done = false;

    const loop = setInterval(async () => {
      if (busy || done) return;
      const d = await detectDescriptor(video);
      if (!d) {
        ring.className = 'cam-ring scanning';
        status.textContent = 'No face detected — centre your face in the frame.';
        return;
      }
      busy = true;
      ring.className = 'cam-ring match';
      status.textContent = 'Verifying…';

      const descriptor = Array.from(d.descriptor);
      try {
        const res = await fetch(submitUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            poll_id: pollId,
            descriptor,
            latitude: coords.latitude,
            longitude: coords.longitude,
          }),
        });
        const data = await res.json();
        if (data.ok) {
          done = true;
          clearInterval(loop);
          ring.className = 'cam-ring match';
          status.textContent = 'Verified — attendance marked.';
          resultBox.innerHTML = '<div class="ok-banner">You are marked present.</div>';
          onSuccess && onSuccess();
        } else {
          ring.className = 'cam-ring nomatch';
          status.textContent = data.error || 'Could not verify — try again.';
          resultBox.innerHTML = `<div class="error-banner">${data.error || 'Verification failed.'}</div>`;
        }
      } catch (e) {
        status.textContent = 'Network error — retrying…';
      }
      busy = false;
    }, 1200);
  }

  return { initEnrollPage, initCheckInPage };
})();
