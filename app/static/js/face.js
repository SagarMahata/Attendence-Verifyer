const MODEL_URL =
  "https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model";

const RollCallFace = (() => {

  // ------------------------------------------------------------
  // Load face-api models
  // ------------------------------------------------------------
  async function loadModels(statusEl) {
    try {
      if (statusEl) {
        statusEl.textContent = "Loading face model...";
      }

      console.log("Loading face models from:", MODEL_URL);

      await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
      console.log("TinyFaceDetector loaded");

      await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);
      console.log("FaceLandmark68Net loaded");

      await faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL);
      console.log("FaceRecognitionNet loaded");

      console.log("ALL FACE MODELS LOADED");

    } catch (error) {
      console.error("FACE MODEL ERROR:", error);

      if (statusEl) {
        statusEl.textContent =
          "Could not load face model: " + error.message;
      }

      throw error;
    }
  }


  // ------------------------------------------------------------
  // Start camera
  // ------------------------------------------------------------
  async function startVideo(videoEl) {

    if (!navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia) {

      throw new Error(
        "Camera access is not supported by this browser."
      );
    }

    console.log("Requesting camera permission...");

    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 420 },
        height: { ideal: 315 },
        facingMode: "user"
      },
      audio: false
    });

    console.log("Camera permission granted");

    videoEl.srcObject = stream;

    await new Promise((resolve) => {

      if (videoEl.readyState >= 1) {
        resolve();
        return;
      }

      videoEl.onloadedmetadata = () => {
        resolve();
      };
    });

    try {
      await videoEl.play();
    } catch (error) {
      console.warn("Video autoplay warning:", error);
    }

    return stream;
  }


  // ------------------------------------------------------------
  // Stop camera
  // ------------------------------------------------------------
  function stopVideo(videoEl) {

    if (!videoEl || !videoEl.srcObject) {
      return;
    }

    const tracks = videoEl.srcObject.getTracks();

    tracks.forEach((track) => {
      track.stop();
    });

    videoEl.srcObject = null;
  }


  // ------------------------------------------------------------
  // Detect face + descriptor
  // ------------------------------------------------------------
  async function detectDescriptor(videoEl) {

    if (!videoEl ||
        !videoEl.videoWidth ||
        !videoEl.videoHeight) {
      return null;
    }

    try {

      const result = await faceapi
        .detectSingleFace(
          videoEl,
          new faceapi.TinyFaceDetectorOptions({
            inputSize: 224,
            scoreThreshold: 0.5
          })
        )
        .withFaceLandmarks()
        .withFaceDescriptor();

      return result || null;

    } catch (error) {

      console.error("Face detection error:", error);

      return null;
    }
  }


  // ============================================================
  // ENROLLMENT PAGE
  // ============================================================

  async function initEnrollPage({
    videoId,
    ringId,
    statusId,
    buttonId,
    saveUrl,
    onSaved
  }) {

    const video = document.getElementById(videoId);
    const ring = document.getElementById(ringId);
    const status = document.getElementById(statusId);
    const button = document.getElementById(buttonId);

    if (!video || !status || !button) {
      console.error("Enrollment elements not found");
      return;
    }

    try {

      // IMPORTANT:
      // Camera is requested BEFORE model loading.
      status.textContent = "Starting camera...";

      await startVideo(video);

      status.textContent = "Loading face model...";

      await loadModels(status);

    } catch (error) {

      console.error("Enrollment initialization error:", error);

      status.textContent =
        "Could not start camera/model: " +
        error.message;

      return;
    }

    status.textContent =
      "Centre your face in the frame.";

    if (ring) {
      ring.classList.add("scanning");
    }

    button.disabled = false;

    let lastDetection = null;

    const detectionLoop = setInterval(async () => {

      if (video.readyState < 2) {
        return;
      }

      const detection = await detectDescriptor(video);

      lastDetection = detection;

      if (detection) {

        if (ring) {
          ring.classList.remove("scanning");
          ring.classList.add("match");
        }

        status.textContent =
          "Face detected — ready to capture.";

      } else {

        if (ring) {
          ring.classList.remove("match");
          ring.classList.add("scanning");
        }

        status.textContent =
          "No face detected — centre your face in the frame.";
      }

    }, 500);


    button.addEventListener("click", async () => {

      button.disabled = true;

      status.textContent = "Capturing...";

      try {

        const detection =
          lastDetection ||
          await detectDescriptor(video);

        if (!detection) {

          status.textContent =
            "No face detected — try again.";

          button.disabled = false;

          return;
        }

        const descriptor =
          Array.from(detection.descriptor);

        console.log("Sending face descriptor...");

        const response = await fetch(saveUrl, {

          method: "POST",

          headers: {
            "Content-Type": "application/json"
          },

          body: JSON.stringify({
            descriptor: descriptor
          })
        });

        if (!response.ok) {
          throw new Error(
            `Server returned ${response.status}`
          );
        }

        const data = await response.json();

        if (data.ok) {

          clearInterval(detectionLoop);

          status.textContent =
            "Face saved successfully.";

          if (onSaved) {
            onSaved();
          }

        } else {

          status.textContent =
            "Could not save face — try again.";

          button.disabled = false;
        }

      } catch (error) {

        console.error("Face enrollment error:", error);

        status.textContent =
          "Error saving face: " +
          error.message;

        button.disabled = false;
      }
    });
  }


  // ============================================================
  // CHECK-IN PAGE
  // ============================================================

  async function initCheckInPage({
    videoId,
    ringId,
    statusId,
    resultId,
    geoChipId,
    anywhereMode,
    pollId,
    submitUrl,
    onSuccess
  }) {

    const video = document.getElementById(videoId);
    const ring = document.getElementById(ringId);
    const status = document.getElementById(statusId);
    const resultBox = document.getElementById(resultId);

    const geoChip =
      geoChipId
        ? document.getElementById(geoChipId)
        : null;

    if (!video || !status) {
      console.error("Check-in elements not found");
      return;
    }

    let coords = {
      latitude: null,
      longitude: null
    };


    // ----------------------------------------------------------
    // LOCATION
    // ----------------------------------------------------------

    if (!anywhereMode) {

      try {

        if (geoChip) {
          geoChip.textContent =
            "📍 requesting location...";
        }

        status.textContent =
          "Requesting your location...";

        console.log("Requesting location permission...");

        const pos =
          await getCurrentPosition();

        coords.latitude =
          pos.coords.latitude;

        coords.longitude =
          pos.coords.longitude;

        console.log(
          "Location received:",
          coords.latitude,
          coords.longitude
        );

        if (geoChip) {

          geoChip.textContent =
            `📍 location locked (±${Math.round(
              pos.coords.accuracy
            )} m)`;
        }

      } catch (error) {

        console.error(
          "Location error:",
          error
        );

        if (geoChip) {
          geoChip.textContent =
            "📍 location access denied";
        }

        status.textContent =
          "Location access is required for this poll.";

        return;
      }
    }


    // ----------------------------------------------------------
    // CAMERA + MODEL
    // ----------------------------------------------------------

    try {

      status.textContent =
        "Starting camera...";

      await startVideo(video);

      status.textContent =
        "Loading face model...";

      await loadModels(status);

    } catch (error) {

      console.error(
        "Camera/model initialization error:",
        error
      );

      status.textContent =
        "Could not access camera/model: " +
        error.message;

      return;
    }


    // ----------------------------------------------------------
    // FACE DETECTION
    // ----------------------------------------------------------

    status.textContent =
      "Centre your face in the frame.";

    if (ring) {
      ring.classList.add("scanning");
    }

    let busy = false;
    let done = false;

    const loop = setInterval(async () => {

      if (busy || done) {
        return;
      }

      if (video.readyState < 2) {
        return;
      }

      const detection =
        await detectDescriptor(video);

      if (!detection) {

        if (ring) {
          ring.className =
            "cam-ring scanning";
        }

        status.textContent =
          "No face detected — centre your face in the frame.";

        return;
      }


      busy = true;

      if (ring) {
        ring.className =
          "cam-ring match";
      }

      status.textContent =
        "Verifying...";


      const descriptor =
        Array.from(detection.descriptor);


      try {

        const response =
          await fetch(submitUrl, {

            method: "POST",

            headers: {
              "Content-Type": "application/json"
            },

            body: JSON.stringify({

              poll_id: pollId,

              descriptor: descriptor,

              latitude: coords.latitude,

              longitude: coords.longitude

            })
          });


        if (!response.ok) {

          throw new Error(
            `Server returned ${response.status}`
          );
        }


        const data =
          await response.json();


        if (data.ok) {

          done = true;

          clearInterval(loop);

          if (ring) {
            ring.className =
              "cam-ring match";
          }

          status.textContent =
            "Verified — attendance marked.";

          if (resultBox) {

            resultBox.innerHTML =
              '<div class="ok-banner">' +
              'You are marked present.' +
              '</div>';
          }

          if (onSuccess) {
            onSuccess();
          }


        } else {

          if (ring) {
            ring.className =
              "cam-ring nomatch";
          }

          status.textContent =
            data.error ||
            "Could not verify — try again.";


          if (resultBox) {

            resultBox.innerHTML =
              `<div class="error-banner">${
                data.error ||
                "Verification failed."
              }</div>`;
          }
        }


      } catch (error) {

        console.error(
          "Attendance verification error:",
          error
        );

        status.textContent =
          "Network error — retrying...";
      }


      busy = false;

    }, 1200);
  }


  // ------------------------------------------------------------
  // Public functions
  // ------------------------------------------------------------

  return {
    initEnrollPage,
    initCheckInPage,
    loadModels,
    startVideo,
    stopVideo,
    detectDescriptor
  };

})();