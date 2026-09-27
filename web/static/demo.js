// Demo walkthrough of one real capture. All data comes from data.js (scripts/build_demo.py).
const D = window.DEMO, R = D.report;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const inr = v => v == null || v === 0 ? "–" : "₹" + Math.round(v).toLocaleString("en-IN");
const pct = v => v == null ? "–" : Math.round(v * 100) + "%";
const photo = n => `media/photos/${n}`;
const pic = (n, cap) => `<figure><img loading="lazy" src="${photo(n)}" alt="">${cap === false ? "" : `<figcaption>${esc(cap ?? n)}</figcaption>`}</figure>`;
const SRC = { frontier: "Opus", object: "Opus, per object", voice: "owner" };
const src = (s, on) => `<span class="src ${s} ${on ? "chosen" : ""}">${SRC[s] || s}</span>`;
const stat = (b, s) => `<div class="stat"><b>${b}</b><span>${s}</span></div>`;
const say = t => `<div class="say">${t}</div>`;
const link = u => /^https?:/.test(u || "") ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(new URL(u).hostname.replace("www.", ""))}</a>` : esc(u || "");
const bars = probs => Object.entries(probs || {}).sort((a, b) => b[1] - a[1])
  .map(([k, p]) => `<div class="pbar"><span style="min-width:90px;white-space:nowrap">${esc(k)}</span><i style="width:${Math.max(2, p * 220)}px"></i>${pct(p)}</div>`).join("");
// Brand words the name already says are not repeated ("Godrej Good Knight" + "Good Knight Flash").
const nm = (brand, name) => [(brand || "").split(" ").filter(w => !String(name || "").toLowerCase().includes(w.toLowerCase())).join(" "), name].filter(Boolean).join(" ");
const ago = y => y == null ? "" : y < 1 ? `about ${Math.max(1, Math.round(y * 12))} month${Math.round(y * 12) > 1 ? "s" : ""} ago` : `${y} years ago`;
const label = ln => ln.book && ln.name !== "unidentified book" ? `${ln.book.title} <span class="muted">(${esc(ln.book.author || "author not read")})</span>`
  : esc(nm(ln.brand, ln.name));
const roomPhotos = D.photos.filter(p => /^room_\d+\.jpg$/.test(p)), frames = D.photos.filter(p => p.includes("video_frame"));
const closeups = D.photos.filter(p => p.startsWith("item_"));
const byId = Object.fromEntries(D.items.map(i => [i.id, i]));
const questions = Object.assign({}, ...D.jev_calls.map(c => Object.fromEntries(Object.entries(c.questions).map(([k, q]) => [k, { q, a: c.answers[k] }]))));

const steps = [
  ["Capture", capture], ["Detect", detect], ["3D", place3d], ["Owner's list", ownerList], ["Item pages", itemPages],
  ["Pipeline 1: local", pipeline1], ["Pipeline 2: Opus", pipeline2], ["Jev", jev], ["Valuation", valuation], ["Ground truth", truth],
];

function capture() {
  const m = D.meta;
  return `<section><h2>Step 1: the owner photographs and films the room</h2>
    ${say("Photos, a video or both. For a video the app takes 2 frames a second, drops motion blur, and keeps a frame each time the view has moved on to something new: no cap, so a longer walk-through of more room keeps more frames. Everything below is the real capture, nothing staged.")}
    <div class="stats">${stat(esc(m.room), esc(m.city) + " (local prices)")}${stat(roomPhotos.length, "room photos")}
      ${stat(frames.length, "sharp frames from the video")}${stat(closeups.length, "close-ups")}
      ${stat(D.items.reduce((n, i) => n + i.voice.length, 0), "voice notes")}
      ${m.length_cm ? stat(`${m.length_cm} x ${m.width_cm} cm`, "tape, ceiling " + m.ceiling_cm + " cm") : ""}</div>
    ${m.merged_from ? `<p class="hint">Merged from captures ${m.merged_from.map(esc).join(" and ")} (a photo capture and a video capture of the same room).</p>` : ""}</section>
    <section><h2>Room photos</h2><div class="grid">${roomPhotos.map(p => pic(p)).join("")}</div></section>
    <section><h2>Close-ups, taken on the item pages (step 4)</h2><div class="grid">${closeups.map(p => {
      const it = byId[p.replace(/^item_/, "").replace(/_closeup_\d+\.jpg$/, "")];
      return pic(p, it ? nm(it.brand, it.name) : p);
    }).join("")}</div></section>
    ${D.video ? `<section><h2>Room video</h2><video src="media/video.mp4" controls preload="metadata"></video>
      <h2 style="margin-top:12px">The ${frames.length} frames kept from it</h2><div class="grid small">${frames.map(p => pic(p, false)).join("")}</div></section>` : ""}`;
}

// Which session item each detection box ended up in, to colour it kept or removed.
const boxKey = (p, b) => p + ":" + b.map(v => v.toFixed(3)).join(",");
const boxItem = {};
D.items.forEach(i => (i.regions || []).forEach(r => boxItem[boxKey(r.photo, r.box)] = i));

function detect() {
  const counts = {};
  D.detections.forEach(d => counts[d.photo] = (counts[d.photo] || 0) + 1);
  const shown = D.photos.filter(p => counts[p]);
  setTimeout(() => showPhoto(shown[0]), 0);
  return `<section><h2>Step 2: local detection</h2>
    ${say("OWLv2 looks for about 60 kinds of household object in every photo and frame. Qwen3-VL-2B then names each crop: category, name, readable brand. Green boxes were kept by the owner, orange ones removed.")}
    <div class="stats">${stat(D.detections.length, "boxes found")}${stat(shown.length, "photos with detections")}
      ${stat(D.items.length, "items after merging the same object across photos")}</div>
    <div class="strip" id="strip">${shown.map(p => `<img src="${photo(p)}" data-p="${p}" title="${p}: ${counts[p]} boxes">`).join("")}</div>
    <div class="viewer" id="viewer"></div><div id="boxinfo" class="hint" style="margin-top:8px">Click a box to see what the models said.</div></section>`;
}

function showPhoto(p) {
  document.querySelectorAll("#strip img").forEach(i => i.classList.toggle("on", i.dataset.p === p));
  // Largest first, so smaller boxes sit on top and stay clickable.
  const area = d => (d.detector.box[2] - d.detector.box[0]) * (d.detector.box[3] - d.detector.box[1]);
  const dets = D.detections.filter(d => d.photo === p).sort((a, b) => area(b) - area(a));
  document.getElementById("viewer").innerHTML = `<img src="${photo(p)}">` + dets.map((d, k) => {
    const [x0, y0, x1, y1] = d.detector.box, it = boxItem[boxKey(p, d.detector.box)];
    return `<div class="box ${it && it.state === "removed" ? "off" : ""}" data-k="${k}" style="left:${x0 * 100}%;top:${y0 * 100}%;width:${(x1 - x0) * 100}%;height:${(y1 - y0) * 100}%">
      <span>${esc(d.vlm?.name || d.detector.prompt)}</span></div>`;
  }).join("");
  document.querySelectorAll("#viewer .box").forEach(b => b.onclick = () => {
    const d = dets[b.dataset.k], it = boxItem[boxKey(p, d.detector.box)];
    document.getElementById("boxinfo").innerHTML = `<b>OWLv2:</b> "${esc(d.detector.prompt)}" at ${d.detector.score.toFixed(2)} &nbsp; <b>Qwen3-VL:</b> ${esc(d.vlm?.category)} / ${esc(d.vlm?.name)}${d.vlm?.brand ? " / " + esc(d.vlm.brand) : ""}
      ${it ? ` &nbsp; <b>Item:</b> ${esc(it.name)} (${esc(it.id)}, ${it.state === "removed" ? '<span class="flag">removed by the owner</span>' : "kept"})` : ""}
      ${it?.measured ? ` &nbsp; <b>3D:</b> about ${it.measured.width_cm} x ${it.measured.height_cm} cm, seen in ${it.measured.views} view${it.measured.views > 1 ? "s" : ""}` : ""}`;
  });
}

function place3d() {
  const g = D.geometry, placed = D.items.filter(i => i.measured);
  if (!g || !placed.length) return `<section><h2>3D</h2><p class="hint">This capture was detected before the 3D step existed.</p></section>`;
  // Top-down map: x across, z down, one dot per item, coloured kept or removed.
  const xs = placed.map(i => i.measured.position_m[0]), zs = placed.map(i => i.measured.position_m[2]);
  const [x0, x1, z0, z1] = [Math.min(...xs), Math.max(...xs), Math.min(...zs), Math.max(...zs)];
  const W = 640, H = Math.max(260, Math.round(W * (z1 - z0 + 0.6) / (x1 - x0 + 0.6)));
  const px = x => 30 + (x - x0) / (x1 - x0 + 1e-6) * (W - 60), pz = z => 20 + (z - z0) / (z1 - z0 + 1e-6) * (H - 40);
  const dots = placed.map(i => `<g><circle cx="${px(i.measured.position_m[0])}" cy="${pz(i.measured.position_m[2])}" r="${Math.min(14, 3 + Math.max(i.measured.width_cm, i.measured.height_cm) / 20)}"
      fill="${i.state === "removed" ? "#f79009" : "#12b76a"}" fill-opacity=".55"><title>${esc(i.name)}: ${i.measured.width_cm} x ${i.measured.height_cm} cm</title></circle>
      <text x="${px(i.measured.position_m[0]) + 8}" y="${pz(i.measured.position_m[2]) + 4}" font-size="10" fill="#344054">${esc(i.name.slice(0, 18))}</text></g>`).join("");
  return `<section><h2>Step 2b: every object placed in 3D</h2>
    ${say("VGGT turns every photo and frame into a 3D point per pixel and a camera pose, in one world; MoGe-2 gives the metric scale. Each detection box becomes the points of the object's front surface: their median is where the object is, their spread its width and height. Two boxes at one place are one object, whatever each view called it; two same-named objects far apart stay two. Sizes are estimates: they only rule out a product at nearly double or half the size.")}
    <div class="stats">${stat(g.images, "photos and frames reconstructed")}${stat(g.chunks, "VGGT chunks, aligned")}${stat(g.metric_scale, "metric scale (MoGe-2)")}${stat(placed.length, "items placed")}</div></section>
    <section><h2>Seen from above</h2><svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px;background:#fff;border:1px solid #e4e7ec;border-radius:8px">${dots}</svg>
      <p class="hint">Green: kept by the owner. Orange: removed. Circle size follows the measured size.</p></section>
    <section><h2>Measured sizes</h2><table><tr><th>Item</th><th>State</th><th class="num">Width</th><th class="num">Height</th><th class="num">Views</th><th class="num">Spread</th></tr>
      ${placed.sort((a, b) => b.measured.width_cm * b.measured.height_cm - a.measured.width_cm * a.measured.height_cm).map(i => `<tr><td>${esc(nm(i.brand, i.name))}</td><td>${esc(i.state)}</td>
        <td class="num">${i.measured.width_cm} cm</td><td class="num">${i.measured.height_cm} cm</td><td class="num">${i.measured.views}</td><td class="num">${i.measured.spread_m} m</td></tr>`).join("")}</table>
      <p class="hint">Spread: how far apart the views put it. Large for a curtain seen along its length, small for a laptop.</p></section>`;
}

function card(i) {
  // Items the owner added have no detection crop; their close-up stands in.
  const img = i.thumb ? `<img src="media/thumbs/${esc(i.thumb)}">` : i.closeups.length ? `<img src="${photo(i.closeups[0])}">` : `<div class="noimg"></div>`;
  return `<div class="card ${i.state === "removed" ? "removed" : ""}">${img}<div class="body"><div class="name">${esc(nm(i.brand, i.name))}${i.quantity > 1 ? " x" + i.quantity : ""}</div>
    <div class="muted" style="font-size:13px">${esc(i.category)}${i.state === "added" ? ' · <span class="badge">added by the owner</span>' : ""}</div></div></div>`;
}

function ownerList() {
  const kept = D.items.filter(i => i.state !== "removed"), removed = D.items.filter(i => i.state === "removed");
  return `<section><h2>Step 3: the owner checks the list</h2>
    ${say("Detection is never perfect, so the owner removes false or duplicate items and adds what was missed, before anything is priced.")}
    <div class="stats">${stat(kept.length, "kept")}${stat(removed.length, "removed")}${stat(kept.filter(i => i.state === "added").length, "added")}</div></section>
    <div class="cols"><section><h2>Kept and added</h2>${kept.map(i => card(i)).join("")}</section>
    <section><h2>Removed by the owner</h2>${removed.map(i => card(i)).join("")}</section></div>`;
}

function itemPages() {
  const withMedia = D.items.filter(i => i.state !== "removed" && (i.closeups.length || i.voice.length || i.note));
  const voiceOf = Object.fromEntries((D.voice?.items || []).map(v => [v.link, v]));
  return `<section><h2>Step 4: one page per item, most valuable first</h2>
    ${say("Optional: close-ups of labels and spines, any number of voice notes, a typed note. All notes on an item are read together. Prices and ages are read by rules, not by the small model.")}
    <div class="stats">${stat(withMedia.length, "items with close-ups or notes")}${stat(closeups.length, "close-ups")}${stat(D.items.reduce((n, i) => n + i.voice.length, 0), "voice notes")}</div></section>` +
    withMedia.map(i => {
      const v = voiceOf[i.id];
      const read = v ? [v.price_paid_inr ? `paid ${inr(v.price_paid_inr)}` : "", ago(v.age_years),
        v.rcv_inr ? `<span class="ok">counts as replacement cost ${inr(v.rcv_inr)}</span>` : "", v.price_note ? `<span class="flag">${esc(v.price_note)}</span>` : "",
        v.brand ? `brand: ${esc(v.brand)}` : ""].filter(Boolean).join(" · ") : "";
      return `<section><div class="item-card"><div class="pics">${i.closeups.map(c => `<img src="${photo(c)}">`).join("") || (i.thumb ? `<img src="media/thumbs/${esc(i.thumb)}">` : "")}</div>
        <div><h2>${esc(nm(i.brand, i.name))} <span class="muted" style="font-weight:400">${esc(i.category)}</span></h2>
        ${i.voice.map(n => `<audio controls preload="none" src="media/voice/${esc(n.file)}"></audio><div class="ocr">Whisper: "${esc(n.text)}"</div>`).join("")}
        ${i.note ? `<div class="ocr">Typed note: "${esc(i.note)}"</div>` : ""}
        ${read ? `<p class="hint" style="margin-top:6px"><b>Read by the rules:</b> ${read}</p>` : ""}</div></div></section>`;
    }).join("");
}

function pipeline1() {
  const lg = D.local_log || [], cl = lg.filter(e => e.closeup), sp = lg.filter(e => e.spine_texts);
  const dropped = Object.fromEntries(lg.filter(e => e.dropped_without_ocr_support).map(e => [e.photo, e.dropped_without_ocr_support]));
  const books = R.items.filter(l => l.book);
  const loc = (D.local?.items || []).filter(i => i.category !== "book");
  return `<section><h2>Pipeline 1: our own models, on this laptop's GPU</h2>
    ${say("PP-OCR reads the text, Qwen3-VL reads brand and model with the OCR as a hint, and every item gets its own live price search (Serper: Google Shopping India plus Blinkit and Zepto).")}
    <div class="stats">${stat(D.local?.items?.length ?? "–", "items read")}${stat(books.length, "books")}${stat(cl.length, "close-ups read")}</div></section>
    <section><h2>Close-ups: what OCR and the small VLM read</h2>${cl.map(e => `<div class="item-card" style="margin-bottom:10px"><div class="pics"><img src="${photo(e.closeup)}"></div><div>
      <div class="muted">${esc(byId[e.item]?.name || e.item)}</div><div class="ocr">OCR: ${esc(e.ocr || "(no text)")}</div>
      <div class="ocr">Qwen3-VL: ${esc(Object.entries(e.vlm || {}).filter(([, v]) => v && v !== "None" && v !== "nothing").map(([k, v]) => `${k}: ${v}`).join(" · "))}</div></div></div>`).join("")}
      <p class="hint">The small model is weak on exact models (it called the HP a Dell from a sticker). Opus and the owner outrank it on identity; its price search is what counts.</p></section>
    <section><h2>Book spines</h2>${say("OCR at 0, 90 and 270 degrees, keep the rotation where text lies flat, one band per spine. A title only the VLM claims needs half its words in the OCR: crossed out below.")}
      ${sp.map(e => `<div class="item-card" style="margin-bottom:10px"><div class="pics"><img src="${photo(e.photo)}"></div><div>
        ${e.spine_texts.map(t => `<div class="ocr">${esc(t)}</div>`).join("")}
        ${(dropped[e.photo] || []).map(t => `<div class="ocr bad">${esc(t)}</div>`).join("")}</div></div>`).join("")}</section>
    <section><h2>Matched to Open Library</h2><table><tr><th>Title</th><th>Genre</th><th>Match</th><th class="num">Local price</th><th>Basis</th></tr>
      ${books.map(l => `<tr><td>${label(l)}</td><td>${esc(l.book.genre)}</td><td>${l.book.match != null ? l.book.match.toFixed(2) : "–"}</td>
        <td class="num">${inr(l.candidates.local?.rcv_inr)}</td><td class="muted">${esc(l.candidates.local?.price_note || "")}</td></tr>`).join("")}</table></section>
    <section><h2>Pipeline 1's own prices</h2><table><tr><th>Item</th><th class="num">Price</th><th>Basis</th></tr>
      ${loc.map(i => `<tr><td>${esc(nm(i.brand, i.name))}</td><td class="num">${inr(i.rcv_inr)}</td><td class="muted">${esc(i.price_note || "")} ${link(i.price_source)}</td></tr>`).join("")}</table></section>`;
}

function pipeline2() {
  const f = D.frontier || { items: [], notes: [] };
  return `<section><h2>Pipeline 2: frontier model (Claude Opus 5.5 via claude -p, standing in for GPT-6 Astra)</h2>
    ${say("One prompt with every photo, each tagged as a room photo or a close-up of a named item. Read, WebSearch and WebFetch only. It dedupes, reads spines, counts switchboard modules, and prices each item new in India with a URL.")}
    <div class="stats">${stat(f.items.length, "items")}${stat(Math.round(f.seconds || D.status?.stages?.frontier?.seconds || 0) + " s", "wall time")}
      ${stat(f.room_area_m2 ? f.room_area_m2 + " m²" : "–", "its area estimate")}</div></section>
    <section><h2>Its notes for the insurer</h2><ul>${(f.notes || []).map(n => `<li>${esc(n)}</li>`).join("")}</ul></section>
    ${objectPass()}
    <section><h2>What the room pass found</h2><table><tr><th>Item</th><th>Qty</th><th>Evidence</th><th class="num">Price</th><th>Source</th></tr>
      ${f.items.map(i => `<tr><td><b>${esc(i.name)}</b><div class="muted">${esc(i.category)}</div></td><td>${i.quantity}</td><td class="muted">${esc(i.evidence || "")}</td>
        <td class="num">${inr(i.rcv_inr)}</td><td>${link(i.price_source)}<div class="muted" style="font-size:12px">${esc(i.price_note || "")}</div></td></tr>`).join("")}</table></section>`;
}

function objectPass() {
  const o = D.objects;
  if (!o || !o.items?.length) return "";
  const measured = Object.fromEntries(D.items.map(i => [i.id, i.measured]));
  return `<section><h2>Second pass: one Opus run per object, with every photo of it</h2>
    ${say("Each object on the owner's list gets its own run: its close-ups and crops of every place it was detected, all at once. Opus identifies it as exactly as the labels allow, finds its dimensions on the web, and prices it new in the room's city. Its answer joins Jev as a fourth reading of that object, and its dimensions are checked against the 3D measurement.")}
    <div class="stats">${stat(o.items.length, "objects")}${stat(Math.round(o.seconds || 0) + " s", "wall time, 4 in parallel")}${stat(esc((o.notes?.[0] || "").split("cost ")[1] || "–"), "reported cost")}</div></section>
    ${[...o.items].sort((a, b) => (b.rcv_inr || 0) - (a.rcv_inr || 0)).map(i => {
      const m = measured[i.link];
      return `<section><div class="item-card"><div class="pics">${(i.photos || []).slice(0, 6).map(p => `<img src="${photo(p)}">`).join("")}</div><div>
        <h2>${esc(nm(i.brand, i.name))} <span class="muted" style="font-weight:400">${esc(i.model || "")}</span></h2>
        <p><b>${inr(i.rcv_inr)}</b> <span class="muted">(${esc(i.price_kind || "")})</span> ${link(i.price_source)}</p>
        <div class="muted" style="font-size:13px">${esc(i.price_note || "")}</div>
        <p class="hint">Dimensions from the web: ${esc(i.product_size || "not found")} ${link(i.attributes?.dimensions_source)}${m ? ` · measured in 3D: about ${m.width_cm} x ${m.height_cm} cm` : ""}</p>
        ${["cpu", "gpu", "ram", "storage"].some(k => i.attributes?.[k]) ? `<p class="hint">Configuration: ${["cpu", "gpu", "ram", "storage"].map(k => i.attributes[k]).filter(Boolean).map(esc).join(", ")}</p>` : ""}
        <div class="ocr">${esc(i.evidence || "")}</div></div></div></section>`;
    }).join("")}`;
}

function jevQ(k) {
  const x = questions[k];
  if (!x) return "";
  const a = x.a || {};
  const res = a.type === "score" ? `score ${a.score} (confidence ${a.confidence})${bars(Object.fromEntries(Object.entries(a.probabilities || {}).map(([l, p]) => [(a.legend?.[l] || l).split(":")[0], p])))}`
    : `choice <b>${esc(a.choice)}</b> (confidence ${a.confidence})${bars(a.probabilities)}`;
  return `<div class="cols"><div><div class="muted">Question (${esc(k)})</div><pre>${esc(JSON.stringify(x.q, null, 1))}</pre></div><div><div class="muted">Jev's answer</div><div style="margin-top:6px">${res}</div></div></div>`;
}

function jev() {
  const tot = D.jev_calls.reduce((s, c) => ({ q: s.q + Object.keys(c.questions).length, t: s.t + c.usage.input_tokens, s: s.s + c.seconds }), { q: 0, t: 0, s: 0 });
  // Examples: the most valuable line that went through a pair score, and the line with the most price candidates.
  const members = l => l.key.split("|").map(x => x.split(":")[1]);
  const byValue = [...R.items].sort((a, b) => b.rcv_inr - a.rcv_inr);
  const pl = byValue.find(l => D.jev_pairs.some(p => members(l).includes(p.a) && members(l).includes(p.b)));
  const pairIdx = pl ? D.jev_pairs.findIndex(p => members(pl).includes(p.a) && members(pl).includes(p.b)) : -1;
  const nprice = l => Object.values(l.candidates || {}).filter(c => c.rcv_inr).length;
  const lap = byValue.reduce((best, l) => nprice(l) > nprice(best) ? l : best, byValue[0]);
  setTimeout(() => { const s = document.getElementById("jevline"); s.onchange = () => showLine(+s.value); showLine(lap ? lap.n : R.items[0].n); }, 0);
  return `<section><h2>Jev (TypeSafe, jev-1.13): which items are the same, and which reading to trust</h2>
    ${say("Jev only judges; the counting, thresholds and arithmetic stay in code. A similarity filter sends only comparable pairs, and the merge rules decide from Jev's scores.")}
    <div class="stats">${stat(R.jev_pairs_scored, "pairs scored")}${stat(R.jev_pairs_skipped, "pairs skipped by the filter")}${stat(tot.q, "questions")}
      ${stat(D.jev_calls.length, "calls (40 questions each)")}${stat(Math.round(tot.t / 1000) + "k", "input tokens")}${stat(tot.s.toFixed(1) + " s", "Jev time")}</div>
    <div class="muted">What Jev is told about the sources</div><pre>${esc(JSON.stringify(D.jev_calls[0]?.state, null, 1))}</pre></section>
    ${pairIdx >= 0 ? `<section><h2>Example: are these two readings the same ${esc(pl.category.replace("_", " "))}?</h2>${jevQ("pair_" + pairIdx)}</section>` : ""}
    ${listingExample()}
    ${lap ? `<section><h2>Example: which ${esc(lap.category.replace("_", " "))} price to trust?</h2>${jevQ("price_" + lap.n)}</section>` : ""}
    <section><h2>Any line: every question Jev was asked about it</h2>
      <select id="jevline">${R.items.map(l => `<option value="${l.n}">${l.name.replace(/<[^>]+>/g, "")}</option>`).join("")}</select>
      <div id="jevout" style="margin-top:10px"></div></section>`;
}

const VERDICT = { exact: "this product", similar: "similar product", different: "different product" };
const listingRows = ls => ls.filter(li => li.verdict).map(li => `<tr><td>${esc(VERDICT[li.verdict])}</td><td>${esc(li.title)}${li.size_mismatch ? `<div class="flag">size: ${esc(li.size_mismatch)}</div>` : ""}</td>
  <td class="num">${inr(li.price)}</td><td class="muted">${esc(li.seller || "")}</td><td class="num">${li.jev_score ?? ""}</td></tr>`).join("");

function listingExample() {
  const lj = R.listings_judged;
  if (!lj) return "";
  // the line whose local listings Jev split most ways
  const kinds = l => new Set((l.candidates?.local?.listings || []).map(li => li.verdict)).size;
  const ex = [...R.items].sort((a, b) => kinds(b) - kinds(a) || (b.rcv_inr || 0) - (a.rcv_inr || 0))[0];
  const ls = ex?.candidates?.local?.listings || [];
  return `<section><h2>Listings: is this the product, a similar one, or a different one?</h2>
    ${say("After Jev settles what each item is, it reads every shopping listing behind a search price and judges it against that identity and the size measured in 3D. The exact price is the median of the listings of this product; failing that, the closest price is the median of the similar ones. A listing far from the measured size is a different product.")}
    <div class="stats">${stat(lj.exact, "listings: this product")}${stat(lj.similar, "similar")}${stat(lj.different, "different")}</div>
    ${ls.length ? `<h2>${label(ex)}: its local search listings</h2><table><tr><th>Jev</th><th>Listing</th><th class="num">Price</th><th>Seller</th><th class="num">Score</th></tr>${listingRows(ls)}</table>
      <p class="hint">Priced at ${inr(ex.candidates.local.rcv_inr)} (${esc(ex.candidates.local.price_kind || "no price")}): ${esc(ex.candidates.local.price_note || "")}</p>` : ""}</section>`;
}

function showLine(n) {
  const l = R.items.find(x => x.n === n), ids = l.key.split("|").map(s => s.split(":")[1]);
  const pairs = D.jev_pairs.map((p, i) => [p, i]).filter(([p]) => ids.includes(p.a) || ids.includes(p.b));
  document.getElementById("jevline").value = n;
  document.getElementById("jevout").innerHTML = `<p class="hint">Merged from: ${ids.map(esc).join(", ")}</p>` +
    ["id", "price", "cond", "genre"].map(t => questions[`${t}_${n}`] ? `<h2>${{ id: "Identity", price: "Price", cond: "Condition", genre: "Genre" }[t]}</h2>${jevQ(`${t}_${n}`)}` : "").join("") +
    Object.entries(l.candidates || {}).filter(([, c]) => (c.listings || []).some(li => li.verdict)).map(([s, c]) =>
      `<h2>Listings behind the ${s === "frontier" ? "Opus" : s} price</h2><table><tr><th>Jev</th><th>Listing</th><th class="num">Price</th><th>Seller</th><th class="num">Score</th></tr>${listingRows(c.listings)}</table>`).join("") +
    (pairs.length ? `<h2>Pair scores involving these items</h2><table><tr><th>a</th><th>b</th><th>same</th><th>possibly</th><th>different</th><th>score</th></tr>
      ${pairs.map(([p]) => `<tr><td>${esc(p.a)}</td><td>${esc(p.b)}</td><td>${pct(p.p_same)}</td><td>${pct(p.p_maybe)}</td><td>${pct(p.p_different)}</td><td>${p.score}</td></tr>`).join("")}</table>` : "");
}

function valuation() {
  const t = R.totals, a = R.area || {};
  const groups = [["Contents", l => !l.book && !isBuilding(l)], ["Building fixtures", isBuilding], ["Books", l => l.book]];
  const lb = R.leaderboard || {};
  setTimeout(() => document.querySelectorAll("tr.line").forEach(tr => tr.onclick = () => toggle(tr)), 0);
  return `<section><h2>Valuation</h2>
    ${say("RCV is the market price Jev trusts times quantity: exact when a listing is this model, otherwise the closest similar product, with the 25th to 75th percentile of its listings. The owner's own price is evidence, not a candidate: far above the market, the line asks for a receipt. When Jev is unsure and the prices are 3 or more times apart, the line is held for review and left out of the total. ACV is straight-line over a per-category life, adjusted for condition and capped as US adjusters do (80% for electronics, 75% furniture, 70% building fixtures, 50% books). Building fixtures are totalled apart, since they fall under the building policy.")}
    <div class="stats">${stat(inr(t.rcv_inr), "total replacement (RCV)")}${stat(inr(t.acv_inr), "after depreciation (ACV)")}
      ${stat(inr(t.contents.rcv_inr), "contents RCV")}${stat(inr(t.building_fixtures.rcv_inr), "building fixtures RCV")}
      ${stat(`${t.books.count}, ${inr(t.books.rcv_inr)}`, "books")}${stat(a.area_sqft ? a.area_sqft + " sq ft" : "–", esc(a.source || ""))}
      ${t.held_for_review?.lines ? stat(`${inr(t.held_for_review.low_inr)} to ${inr(t.held_for_review.high_inr)}`, `${t.held_for_review.lines} lines held for review, not in the total`) : ""}
      ${stat(t.needs_review, "lines flagged for review")}</div>
    <p><a class="btn primary" href="/r/${esc(D.capture)}" target="_blank">Open the live review page (Remove / Same as / Undo)</a> <span class="hint">works when served by the app</span></p></section>
    <div class="cols"><section><h2>Floor area, every candidate</h2><table>${(a.candidates || []).map(c => `<tr><td>${esc(c.source)}</td><td class="num">${c.area_m2} m²</td><td class="num">${c.area_sqft} sq ft</td></tr>`).join("")}</table></section>
    ${D.plan ? `<section><h2>Floor plan</h2><img src="media/floor_plan.png" style="width:100%;border-radius:8px"></section>` : ""}</div>
    <section><h2>How the sources ranked</h2><table><tr><th>Source</th><th class="num">Items found</th><th class="num">Found alone</th><th class="num">Identity chosen</th><th class="num">Price chosen</th></tr>
      ${Object.entries(lb).map(([s, v]) => `<tr><td>${src(s)}</td><td class="num">${v.items_found}</td><td class="num">${v.found_alone}</td><td class="num">${v.identity.chosen}/${v.identity.contested}</td><td class="num">${v.price.chosen}/${v.price.contested}</td></tr>`).join("")}</table></section>
    <section><h2>Every line (click one for its photos, candidates and Jev's probabilities)</h2><table>
      <tr><th>Item</th><th>Qty</th><th class="num">RCV</th><th class="num">ACV</th><th>Price candidates (outlined: Jev's choice)</th></tr>
      ${groups.map(([g, f]) => `<tr><th colspan="5" style="font-size:14px;color:var(--fg)">${g}</th></tr>` + R.items.filter(f).map(row).join("")).join("")}</table></section>`;
}

const isBuilding = l => D.building.includes(l.category);

function row(l) {
  const cands = Object.entries(l.candidates || {}).filter(([, c]) => c.rcv_inr).map(([s, c]) => `${src(s, s === l.price_from)} ${inr(c.rcv_inr)}`).join(" &nbsp;");
  const under = l.held ? `<div class="flag">held: ${inr(l.held.low_inr)} to ${inr(l.held.high_inr)}</div>`
    : `<div class="muted" style="font-size:12px">${esc(l.price_kind || "")}${l.price_range_inr && l.price_range_inr[0] !== l.price_range_inr[1] ? ` ${inr(l.price_range_inr[0])} to ${inr(l.price_range_inr[1])}` : ""}</div>`;
  return `<tr class="line" data-n="${l.n}" ${l.held ? 'style="background:#fffaeb"' : ""}><td>${label(l)}${l.flags?.length ? `<div class="flag">${l.flags.map(esc).join("<br>")}</div>` : ""}</td>
    <td>${l.quantity}</td><td class="num">${inr(l.rcv_inr)}${under}</td><td class="num">${inr(l.acv_inr)}</td><td>${cands || "–"}</td></tr>`;
}

function toggle(tr) {
  if (tr.nextElementSibling?.classList.contains("detail")) return tr.nextElementSibling.remove();
  const l = R.items.find(x => x.n === +tr.dataset.n);
  const c = Object.entries(l.candidates || {}).map(([s, x]) => `<div style="margin-bottom:6px">${src(s, s === l.price_from)} <b>${esc(nm(x.brand, x.name))}</b> ${inr(x.rcv_inr)}${x.price_kind ? ` <span class="muted">(${esc(x.price_kind)})</span>` : ""}
    <div class="muted" style="font-size:12px">${esc(x.price_note || "")} ${link(x.price_source)}${x.product_size ? ` · product size ${esc(x.product_size)}` : ""}</div></div>`).join("");
  const m = l.measured ? `<p class="hint">Measured in 3D: about ${l.measured.width_cm} x ${l.measured.height_cm} cm from ${l.measured.views} view${l.measured.views > 1 ? "s" : ""}</p>` : "";
  tr.insertAdjacentHTML("afterend", `<tr class="detail"><td colspan="5"><div class="cols"><div><div class="grid small">${(l.photos || []).slice(0, 8).map(p => pic(p, false)).join("")}</div>
    <p class="hint">ACV: ${esc(l.acv_basis || "")}</p>${m}${l.owner_price_inr ? `<p class="hint">The owner said they paid ${inr(l.owner_price_inr)}${l.age_years != null ? ", " + esc(ago(l.age_years)) : ""}</p>` : ""}</div><div>${c}<div class="muted" style="margin-top:8px">Identity (Jev)</div>${bars(l.identity_probs)}
    <div class="muted" style="margin-top:8px">Price (Jev)</div>${bars(l.price_probs)}</div></div></td></tr>`);
  tr.nextElementSibling.querySelectorAll("img").forEach(zoomable);
}

function truth() {
  const s = D.score;
  if (!s) return `<section><p class="hint">No ground truth for this capture.</p></section>`;
  const recent = s.items.filter(i => i.rcv_error_pct != null);
  return `<section><h2>Against the owner's ground truth</h2>
    ${say("What the owner paid, from memory. The pipeline never reads it; scoring runs after. Error is computed only where the purchase is within 2 years, so the price paid is a fair replacement cost. The owner's own price is only evidence now, so this is the error of the market prices the pipelines found.")}
    <div class="stats">${stat(s.summary.split(" ")[0], "ground-truth items found")}${stat(pct(recent.reduce((a, i) => a + Math.abs(i.rcv_error_pct), 0) / recent.length / 100), "mean RCV error, " + recent.length + " recent purchases")}</div>
    <p class="hint">${recent.filter(i => i.chosen_from === "voice").length ? `On ${recent.filter(i => i.chosen_from === "voice").length} of the ${recent.length}, only the owner priced it. ` : ""}The last two columns show each pipeline alone. The biggest miss is an item priced as a cheaper version of itself, which a model sticker or a receipt fixes.</p></section>
    <section><table><tr><th>Owner's item</th><th class="num">Paid</th><th class="num">Age (y)</th><th>Candidates</th><th class="num">RCV</th><th class="num">Error</th><th class="num">Local alone</th><th class="num">Opus alone</th></tr>
      ${s.items.map(i => `<tr><td>${esc(i.truth)}${i.found ? "" : ' <span class="flag">not found</span>'}</td><td class="num">${inr(i.paid_inr)}</td><td class="num">${i.age_years ?? "–"}</td>
        <td>${Object.entries(i.candidates_inr || {}).filter(([, v]) => v).map(([k, v]) => `${src(k, k === i.chosen_from)} ${inr(v)}`).join(" &nbsp;")}</td>
        <td class="num">${inr(i.rcv_inr)}</td><td class="num"><b>${signed(i.rcv_error_pct)}</b></td>
        <td class="num">${i.rcv_error_pct != null ? signed(i.per_source_error_pct?.local) : "–"}</td><td class="num">${i.rcv_error_pct != null ? signed(i.per_source_error_pct?.frontier) : "–"}</td></tr>`).join("")}</table></section>`;
}

const signed = v => v == null ? "–" : (v > 0 ? "+" : "") + Math.round(v) + "%";

function zoomable(img) {
  img.style.cursor = "zoom-in";
  img.onclick = e => { e.stopPropagation(); const z = document.getElementById("zoom"); z.querySelector("img").src = img.src; z.style.display = "flex"; };
}
document.getElementById("zoom").onclick = e => e.currentTarget.style.display = "none";

function go(k) {
  k = Math.max(0, Math.min(steps.length - 1, k));
  document.querySelectorAll("nav.steps button").forEach((b, i) => b.classList.toggle("on", i === k));
  const p = document.getElementById("panes");
  p.innerHTML = steps[k][1]();
  p.querySelectorAll(".grid img, .item-card img").forEach(zoomable);
  p.querySelectorAll("#strip img").forEach(i => i.onclick = () => showPhoto(i.dataset.p));
  location.hash = k + 1;
  window.scrollTo(0, 0);
  cur = k;
}

let cur = 0;
document.getElementById("title").textContent = `${D.meta.room[0].toUpperCase() + D.meta.room.slice(1)}, ${D.meta.city}`;
document.getElementById("lead").innerHTML = `${esc(D.title)}. Capture ${esc(D.capture)}, run ${esc(D.run)}. Pipeline 2: ${esc(R.backend)}. Every photo, voice note and number below is from the real run. <a href="../">All demos</a>`;
document.getElementById("nav").innerHTML = steps.map(([n], i) => `<button data-k="${i}">${i + 1}. ${n}</button>`).join("") + `<span class="keys">← → to move</span>`;
document.querySelectorAll("nav.steps button").forEach(b => b.onclick = () => go(+b.dataset.k));
document.addEventListener("keydown", e => {
  if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
  if (e.key === "ArrowRight") go(cur + 1);
  if (e.key === "ArrowLeft") go(cur - 1);
  if (e.key === "Escape") document.getElementById("zoom").style.display = "none";
});
window.onhashchange = () => { const k = (parseInt(location.hash.slice(1)) || 1) - 1; if (k !== cur) go(k); };
go((parseInt(location.hash.slice(1)) || 1) - 1);
