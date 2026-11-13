// day3_mic: マイクで話しかける(押している間だけ録音し、離したら文字にして入力欄に入れる)。
// 録音はブラウザの中で 16kHz・モノラルの WAV に変換してから /api/transcribe に送る。
(() => {
  const RATE = 16000; // Gemma 4 の音声は 16kHz・モノラル
  const micButton = document.getElementById("mic-button");
  const micLabel = document.getElementById("mic-label");
  const autoSend = document.getElementById("mic-auto-send");
  const input = document.getElementById("message-input");
  const composer = document.getElementById("composer");

  let recorder = null;
  let chunks = [];
  let pressed = false;

  function setMicState(stateName, label) {
    micButton.dataset.state = stateName;
    micLabel.textContent = label;
  }

  function reportError(message) {
    if (typeof showError === "function") {
      showError(message); // app.js のエラー表示を使う
    } else {
      alert(message);
    }
  }

  async function toWav16k(blob) {
    const context = new AudioContext();
    const source = await context.decodeAudioData(await blob.arrayBuffer());
    context.close();
    const offline = new OfflineAudioContext(1, Math.ceil(source.duration * RATE), RATE);
    const node = offline.createBufferSource();
    node.buffer = source;
    node.connect(offline.destination);
    node.start();
    const pcm = (await offline.startRendering()).getChannelData(0);
    const view = new DataView(new ArrayBuffer(44 + pcm.length * 2));
    const writeText = (offset, text) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
    writeText(0, "RIFF"); view.setUint32(4, 36 + pcm.length * 2, true); writeText(8, "WAVE"); writeText(12, "fmt ");
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, RATE, true); view.setUint32(28, RATE * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    writeText(36, "data"); view.setUint32(40, pcm.length * 2, true);
    for (let i = 0; i < pcm.length; i += 1) {
      view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, pcm[i])) * 0x7fff, true);
    }
    return { wav: new Blob([view], { type: "audio/wav" }), duration: source.duration };
  }

  async function transcribe(blob) {
    setMicState("busy", "文字にしています…");
    try {
      const { wav, duration } = await toWav16k(blob);
      if (duration < 0.3) {
        return; // 短すぎる(ボタンを押してすぐ離した)
      }
      const response = await fetch("/api/transcribe", { method: "POST", body: wav, headers: { "Content-Type": "audio/wav" } });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "文字起こしに失敗しました。");
      }
      const text = (payload.text || "").trim();
      if (!text) {
        return;
      }
      input.value = input.value.trim() ? `${input.value.trim()} ${text}` : text;
      input.focus();
      if (autoSend.checked && !input.disabled) {
        composer.requestSubmit(); // app.js の送信処理(sendMessage)が動く
      }
    } catch (error) {
      reportError(error.message || "文字起こしに失敗しました。");
    } finally {
      setMicState("idle", "押して話す");
    }
  }

  async function startRecording() {
    pressed = true;
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      reportError(`マイクが使えません: ${error.message}`);
      return;
    }
    if (!pressed) {
      // 許可の確認をしているあいだにボタンを離した
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    chunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (event) => chunks.push(event.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      const blob = new Blob(chunks, { type: chunks[0]?.type || "audio/webm" });
      recorder = null;
      transcribe(blob);
    };
    recorder.start();
    setMicState("recording", "話しています…(離すと送る)");
  }

  function stopRecording() {
    pressed = false;
    if (recorder && recorder.state === "recording") {
      recorder.stop();
    }
  }

  micButton.addEventListener("pointerdown", (event) => {
    if (micButton.dataset.state === "busy" || input.disabled) {
      return;
    }
    event.preventDefault();
    micButton.setPointerCapture(event.pointerId);
    startRecording();
  });
  micButton.addEventListener("pointerup", stopRecording);
  micButton.addEventListener("pointercancel", stopRecording);

  // llama-server が音声を受け取れないときは、最初に知らせる
  fetch("/api/voice/status")
    .then((response) => response.json())
    .then((status) => {
      if (status.audio_input === false) {
        micButton.disabled = true;
        micButton.title = "llama-server が音声を扱えません。--no-mmproj を付けずに起動し直してください。";
        setMicState("off", "マイクは使えません");
      }
    })
    .catch(() => {});

  // 送信中(入力欄が止まっているあいだ)はマイクも止める
  new MutationObserver(() => {
    if (micButton.dataset.state !== "off") {
      micButton.disabled = input.disabled;
    }
  }).observe(input, { attributes: true, attributeFilter: ["disabled"] });

})();
