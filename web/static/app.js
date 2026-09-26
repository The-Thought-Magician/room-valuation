// Shared helpers: photo pickers with thumbnails, a voice recorder, uploads with progress.

function photoPicker(inputs, box) {
  const files = [];
  const render = () => {
    box.innerHTML = "";
    files.forEach((f, i) => {
      const d = document.createElement("div"), img = document.createElement("img"), x = document.createElement("b");
      img.src = URL.createObjectURL(f);
      x.textContent = "×";
      x.onclick = () => { files.splice(i, 1); render(); };
      d.append(img, x);
      box.append(d);
    });
  };
  inputs.forEach(inp => inp.addEventListener("change", e => { files.push(...e.target.files); inp.value = ""; render(); }));
  return files;
}

function recorder(button, timeLabel, player, errBox) {
  const state = { blob: null, name: null };
  let rec = null, chunks = [], t0 = 0, timer = null;
  button.onclick = async () => {
    if (rec && rec.state === "recording") { rec.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const type = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      rec = new MediaRecorder(stream, type ? { mimeType: type } : {});
      chunks = [];
      rec.ondataavailable = e => e.data.size && chunks.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        clearInterval(timer);
        state.blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        state.name = "voice." + ((rec.mimeType || "").includes("mp4") ? "m4a" : "webm");
        player.src = URL.createObjectURL(state.blob);
        player.hidden = false;
        button.textContent = "Record again";
        button.classList.remove("rec");
        timeLabel.textContent = "recorded";
      };
      rec.start(1000);
      t0 = Date.now();
      button.textContent = "Stop recording";
      button.classList.add("rec");
      timer = setInterval(() => {
        const s = Math.round((Date.now() - t0) / 1000);
        timeLabel.textContent = `recording ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
      }, 500);
    } catch (e) {
      errBox.textContent = "Microphone not available: " + e.message + " (open the page over https and allow the microphone)";
    }
  };
  return state;
}

function upload(url, fd, prog) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    if (prog) { prog.hidden = false; xhr.upload.onprogress = e => { if (e.lengthComputable) prog.value = 100 * e.loaded / e.total; }; }
    xhr.onload = () => xhr.status === 200 ? resolve(JSON.parse(xhr.responseText)) : reject(new Error(xhr.status + " " + xhr.responseText));
    xhr.onerror = () => reject(new Error("network error, check the connection"));
    xhr.open("POST", url);
    xhr.send(fd);
  });
}

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
