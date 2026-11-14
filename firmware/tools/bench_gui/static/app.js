// Werkbank: Oberfläche der Testkonsole revb_test. Kein Framework, keine fremden Skripte (läuft ohne Netz).
// Daten kommen als Server-Sent Events vom Python-Programm (server.py), Befehle gehen als POST zurück.
'use strict';

const TOKEN = document.body.dataset.token;
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = (v, d = 2) => (v === null || v === undefined || !Number.isFinite(v) ? '–' : v.toFixed(d).replace('.', ','));
const vec = (a, d = 3) => (a || []).map((v) => fmt(v, d)).join('   ');
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

let S = { connected: false, cal: null, fit: {}, parts: {}, supply: {} };   // Zustand vom Server
let last = null;                 // langsame Werte des letzten Datenpakets
let mode = 'cal';                // 'cal' = kalibriert in Körperachsen, 'raw' = roh in Chip-Achsen
let calStep = 'gyro';
let capture = { kind: null };
let fitResult = null;
let magPts = [];
const tests = new Map();         // Name -> {cmd, result, detail, time}

async function api(action, body) {
  try {
    const r = await fetch('/api/' + action, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Token': TOKEN }, body: JSON.stringify(body || {}) });
    const j = await r.json();
    if (!j.ok) throw new Error(j.error || 'Fehler');
    return j;
  } catch (e) {
    toast(e.message, true);
    throw e;
  }
}
const cmd = (c) => api('cmd', { cmd: c }).catch(() => {});

function toast(text, err = false) {
  const t = document.createElement('div');
  t.className = 'toast' + (err ? ' err' : '');
  t.textContent = text;
  $('#toasts').append(t);
  setTimeout(() => t.remove(), err ? 7000 : 4000);
}

// ------------------------------------------------------------------ Diagramme
function niceTicks(lo, hi, n = 4) {
  if (!(hi > lo)) { hi = lo + 1; lo -= 1; }
  const raw = (hi - lo) / n, p = 10 ** Math.floor(Math.log10(raw)), f = raw / p;
  const step = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p;
  const t0 = Math.floor(lo / step) * step, t1 = Math.ceil(hi / step) * step, ticks = [];
  for (let v = t0; v <= t1 + step / 2; v += step) ticks.push(Math.abs(v) < step / 1e6 ? 0 : v);
  return { lo: t0, hi: t1, ticks, digits: Math.max(0, -Math.floor(Math.log10(step) + 1e-9)) };
}

class StripChart {
  // names: Reihen; cols(mode) -> Spalten der Datenzeile; windowS: sichtbare Zeit
  constructor(host, { title, unit, names, cols, digits = 2, windowS = 20 }) {
    this.names = names; this.cols = cols; this.digits = digits; this.windowS = windowS;
    this.t = []; this.v = names.map(() => []);
    this.hover = null;
    host.classList.add('card', 'chart');
    host.innerHTML = `<div class="head"><b>${esc(title)}</b><span class="unit">${esc(unit)}</span><span class="sub unit"></span>
      <div class="legend">${names.map((n, i) => `<span><i style="background:var(--series-${i + 1})"></i>${esc(n)}<b>–</b></span>`).join('')}</div></div>
      <div class="plot"><canvas></canvas><div class="tip" hidden></div></div>`;
    this.canvas = $('canvas', host); this.tip = $('.tip', host); this.sub = $('.sub', host);
    this.vals = $$('.legend b', host);
    const plot = $('.plot', host);
    plot.addEventListener('mousemove', (e) => { this.hover = e.offsetX; });
    plot.addEventListener('mouseleave', () => { this.hover = null; this.tip.hidden = true; });
  }
  clear() { this.t = []; this.v = this.names.map(() => []); }
  push(row) {
    const cols = this.cols(mode);
    this.t.push(row[0]);
    cols.forEach((c, i) => this.v[i].push(row[c]));
    if (this.t.length > 6000) { this.t.splice(0, 1500); this.v.forEach((a) => a.splice(0, 1500)); }
  }
  draw() {
    const cv = this.canvas, dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
    if (!w || !h) return;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    const g = cv.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    const L = 46, R = 8, T = 6, B = 18, pw = w - L - R, ph = h - T - B;
    const n = this.t.length, tEnd = n ? this.t[n - 1] : 0, tBeg = tEnd - this.windowS;
    let i0 = n;
    while (i0 > 0 && this.t[i0 - 1] >= tBeg) i0--;
    let lo = Infinity, hi = -Infinity;
    for (const a of this.v) for (let i = i0; i < n; i++) { const y = a[i]; if (y !== null) { if (y < lo) lo = y; if (y > hi) hi = y; } }
    if (lo === Infinity) { lo = -1; hi = 1; }
    const pad = Math.max((hi - lo) * 0.12, 10 ** -this.digits * 2);
    const sc = niceTicks(lo - pad, hi + pad);
    const X = (t) => L + ((t - tBeg) / this.windowS) * pw, Y = (y) => T + (1 - (y - sc.lo) / (sc.hi - sc.lo)) * ph;
    g.font = `11px ${css('--mono')}`; g.textBaseline = 'middle'; g.lineWidth = 1;
    for (const tk of sc.ticks) {                       // Gitter und y-Beschriftung, zurückhaltend
      const y = Math.round(Y(tk)) + 0.5;
      g.strokeStyle = tk === 0 ? css('--border') : css('--grid');
      g.beginPath(); g.moveTo(L, y); g.lineTo(w - R, y); g.stroke();
      g.fillStyle = css('--text-3'); g.textAlign = 'right';
      g.fillText(tk.toFixed(sc.digits).replace('.', ','), L - 6, y);
    }
    g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.fillStyle = css('--text-3');
    for (let s = 0; s <= this.windowS; s += 5) g.fillText(s === 0 ? 'jetzt' : `−${s} s`, Math.min(X(tEnd - s), w - R - 14), h - 4);
    g.save(); g.beginPath(); g.rect(L, T, pw, ph); g.clip();
    g.lineWidth = 1.75; g.lineJoin = 'round';
    this.v.forEach((a, k) => {
      g.strokeStyle = css(`--series-${k + 1}`);
      g.beginPath();
      let pen = false;
      for (let i = i0; i < n; i++) {
        if (a[i] === null) { pen = false; continue; }
        const x = X(this.t[i]), y = Y(a[i]);
        if (pen) g.lineTo(x, y); else { g.moveTo(x, y); pen = true; }
      }
      g.stroke();
    });
    g.restore();
    this.vals.forEach((el, k) => { const a = this.v[k]; el.textContent = fmt(a.length ? a[a.length - 1] : null, this.digits); });
    if (this.hover !== null && n > i0 && this.hover >= L && this.hover <= w - R) {     // Fadenkreuz mit Werten
      const tH = tBeg + ((this.hover - L) / pw) * this.windowS;
      let i = i0;
      while (i < n - 1 && this.t[i] < tH) i++;
      const x = X(this.t[i]);
      g.strokeStyle = css('--text-3'); g.lineWidth = 1;
      g.beginPath(); g.moveTo(x, T); g.lineTo(x, T + ph); g.stroke();
      this.tip.hidden = false;
      this.tip.innerHTML = `−${fmt(tEnd - this.t[i], 2)} s<br>` + this.names.map((nm, k) =>
        `<i style="background:var(--series-${k + 1})"></i>${esc(nm)} ${fmt(this.v[k][i], this.digits)}`).join('<br>');
      this.tip.style.left = `${Math.min(x + 10, w - this.tip.offsetWidth - 4)}px`;
      this.tip.style.top = `${T + 4}px`;
    } else this.tip.hidden = true;
  }
}

// ------------------------------------------------------------------ Lage (3D-Ansicht)
function quatMatrix([w, x, y, z]) {
  return [[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
          [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
          [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]];
}
function drawAttitude(cv, q) {
  const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  if (!w) return;
  if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const g = cv.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
  const Rm = quatMatrix(q || [1, 0, 0, 0]), az = 0.6, el = 0.42, s = Math.min(w, h) * 0.36, cx = w / 2, cy = h * 0.56;
  const rot = (p) => Rm.map((r) => r[0] * p[0] + r[1] * p[1] + r[2] * p[2]);
  const proj = (p) => {                                // Navigation (z oben) -> Bild; c = Nähe zur Kamera
    const xr = p[0] * Math.cos(az) - p[1] * Math.sin(az), yr = p[0] * Math.sin(az) + p[1] * Math.cos(az);
    return { x: cx + xr * s, y: cy - (p[2] * Math.cos(el) + yr * Math.sin(el)) * s, c: -yr * Math.cos(el) + p[2] * Math.sin(el) };
  };
  // Bodenkreis
  g.strokeStyle = css('--grid'); g.lineWidth = 1; g.beginPath();
  for (let a = 0; a <= 64; a++) { const p = proj([1.15 * Math.cos(a / 64 * 2 * Math.PI), 1.15 * Math.sin(a / 64 * 2 * Math.PI), -0.95]); a ? g.lineTo(p.x, p.y) : g.moveTo(p.x, p.y); }
  g.stroke();
  // Körper: Quader entlang der Rollachse (Körper z) mit Spitze
  const a = 0.22, z0 = -0.75, z1 = 0.55, tip = [0, 0, 0.95];
  const P = [[-a, -a, z0], [a, -a, z0], [a, a, z0], [-a, a, z0], [-a, -a, z1], [a, -a, z1], [a, a, z1], [-a, a, z1], tip].map(rot);
  const faces = [[0, 1, 2, 3], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [4, 5, 8], [5, 6, 8], [6, 7, 8], [7, 4, 8]];
  const light = [0.35, -0.5, 0.8], base = css('--text-3'), surf = css('--surface');
  faces.map((f) => {
    const pts = f.map((i) => P[i]), u = pts[1].map((v, i) => v - pts[0][i]), v2 = pts[2].map((v, i) => v - pts[0][i]);
    let nrm = [u[1] * v2[2] - u[2] * v2[1], u[2] * v2[0] - u[0] * v2[2], u[0] * v2[1] - u[1] * v2[0]];
    const ctr = pts.reduce((acc, p) => acc.map((v, i) => v + p[i] / pts.length), [0, 0, 0]);
    if (nrm[0] * ctr[0] + nrm[1] * ctr[1] + nrm[2] * (ctr[2] + 0.1) < 0) nrm = nrm.map((v) => -v);
    const len = Math.hypot(...nrm) || 1, sh = Math.max(0, (nrm[0] * light[0] + nrm[1] * light[1] + nrm[2] * light[2]) / len);
    return { pts: pts.map(proj), c: proj(ctr).c, sh, nose: f.length === 3 };
  }).sort((p1, p2) => p1.c - p2.c).forEach((f) => {
    g.beginPath(); f.pts.forEach((p, i) => (i ? g.lineTo(p.x, p.y) : g.moveTo(p.x, p.y))); g.closePath();
    g.fillStyle = `color-mix(in srgb, ${f.nose ? css('--accent') : base} ${Math.round(25 + 55 * f.sh)}%, ${surf})`;
    g.fill(); g.strokeStyle = css('--surface'); g.lineWidth = 1.5; g.stroke();
  });
  // Körperachsen
  g.font = '12px system-ui'; g.textBaseline = 'middle'; g.lineWidth = 2;
  [[1, 0, 0], [0, 1, 0], [0, 0, 1]].forEach((ax, i) => {
    const o = proj(rot([0, 0, 0])), e = proj(rot(ax.map((v) => v * (i === 2 ? 1.25 : 0.7))));
    g.strokeStyle = css(`--series-${i + 1}`); g.beginPath(); g.moveTo(o.x, o.y); g.lineTo(e.x, e.y); g.stroke();
    g.fillStyle = css('--text-2'); g.fillText('xyz'[i], e.x + 5, e.y);
  });
}

// ------------------------------------------------------------------ Aufbau der Reiter
const charts = [];
function buildLive() {
  $('#tab-live').innerHTML = `
    <div class="row toolbar">
      <button id="live-toggle" class="on">Live an</button>
      <div class="seg" id="rate">${[25, 50, 100].map((r) => `<button data-hz="${r}">${r} Hz</button>`).join('')}</div>
      <div class="seg" id="mode"><button data-mode="cal" class="on" title="Kalibrierung angewendet, Achsen des Raketenkörpers">Kalibriert · Körperachsen</button><button data-mode="raw" title="Wie der Chip sie liefert">Roh · Chip-Achsen</button></div>
      <button id="rec" title="Rohdaten des Stroms als CSV nach firmware/test_reports/">Aufzeichnen</button>
      <span class="spacer"></span>
      <span id="simctl" class="row" hidden><span class="note">Simulierte Bewegung</span>
        <div class="seg">${[['ruhe', 'Ruhe'], ['wackeln', 'Wackeln'], ['taumeln', 'Taumeln'], ['drehen', '360° drehen']].map(([m, t]) => `<button data-motion="${m}">${t}</button>`).join('')}</div></span>
    </div>
    <div class="tiles" id="tiles"></div>
    <div class="grid live-grid">
      <div class="grid charts"><div id="c-acc"></div><div id="c-gyro"></div><div id="c-mag"></div><div id="c-alt"></div></div>
      <div class="grid">
        <div class="card"><h3>Lage</h3><canvas id="att"></canvas>
          <dl class="kv"><dt>Neigung gegen die Senkrechte</dt><dd id="a-tilt">–</dd><dt>Kurs (Magnetometer)</dt><dd id="a-head">–</dd></dl>
          <p class="note" style="margin-top:8px">Aus Drehrate und Beschleunigung am PC geschätzt, nur zur Anzeige. Die Achsen stimmen erst nach der Achszuordnung (Kalibrierung → Achsen).</p></div>
        <div class="card"><h3>Bausteine</h3><div id="parts" class="kv"></div></div>
      </div>
    </div>`;
  const xyz = ['x', 'y', 'z'];
  charts.push(new StripChart($('#c-acc'), { title: 'Beschleunigung', unit: 'm/s²', names: xyz, cols: (m) => (m === 'raw' ? [1, 2, 3] : [10, 11, 12]) }));
  charts.push(new StripChart($('#c-gyro'), { title: 'Drehrate', unit: '°/s', names: xyz, cols: (m) => (m === 'raw' ? [4, 5, 6] : [13, 14, 15]) }));
  charts.push(new StripChart($('#c-mag'), { title: 'Magnetfeld', unit: 'gauss', names: xyz, digits: 3, cols: (m) => (m === 'raw' ? [7, 8, 9] : [16, 17, 18]) }));
  charts.push(new StripChart($('#c-alt'), { title: 'Höhe', unit: 'm, relativ zum Beginn des Stroms (Barometer)', names: ['Höhe'], cols: () => [19] }));
  $('#live-toggle').onclick = () => api('stream', { on: !S.want_stream });
  $('#rate').onclick = (e) => { if (e.target.dataset.hz) api('stream', { on: true, hz: +e.target.dataset.hz }); };
  $('#mode').onclick = (e) => {
    if (!e.target.dataset.mode) return;
    mode = e.target.dataset.mode;
    $$('#mode button').forEach((b) => b.classList.toggle('on', b.dataset.mode === mode));
    charts.forEach((c) => c.clear());
  };
  $('#rec').onclick = () => api('record', { on: !S.recording }).then((j) => { if (j.path) toast('Aufzeichnung: ' + j.path); });
  $('#simctl').onclick = (e) => {
    const m = e.target.dataset.motion;
    if (!m) return;
    api('sim_motion', { mode: m }).then(() => $$('#simctl button').forEach((b) => b.classList.toggle('on', b.dataset.motion === m && m !== 'drehen'))).catch(() => {});
  };
}

const TESTS = [
  ['Ohne Bewegung', [['all', 'Alle ohne Bewegung'], ['mux', 'Spannungen'], ['imu', 'IMU'], ['baro', 'Barometer'], ['mag', 'Magnetometer'], ['sht', 'Feuchte'], ['adxl', 'ADXL375'], ['ina', 'Strommessung'], ['timing', 'Loop-Timing'], ['mem', 'PSRAM / Flash']]],
  ['Mit Rückfragen', [['led', 'LEDs'], ['buzzer', 'Summer'], ['cam', 'Kamera-Trigger'], ['sd', 'SD-Karte'], ['lora', 'LoRa'], ['gps', 'GPS'], ['watchdog', 'Watchdog']]],
];
function buildTests() {
  $('#tab-tests').innerHTML = `
    <div class="grid" style="grid-template-columns:minmax(0,1fr)">
      <div class="card">
        ${TESTS.map(([g, items]) => `<h3>${g}</h3><div class="testbtns" style="margin-bottom:12px">${items.map(([c, t], i) => `<button data-cmd="${c}"${i === 0 && c === 'all' ? ' class="primary"' : ''}>${t}</button>`).join('')}</div>`).join('')}
        <h3>Bestückung</h3>
        <div class="fitlist" id="fitlist"></div>
        <p class="note" style="margin-top:6px">Ein Teil, das hier aus ist, meldet „nicht bestückt“ statt eines Fehlers. Die Liste gilt bis zum Neustart des Teensy (dauerhaft: <code>FitRevB.h</code>).</p>
      </div>
      <div class="card">
        <div class="row" style="margin-bottom:8px"><h2 style="margin:0">Ergebnisse</h2><span id="testsum" class="note"></span><span class="spacer"></span>
          <button id="report" title="Markdown und JSON nach firmware/test_reports/">Bericht speichern</button><button id="cleartests" class="small">Liste leeren</button></div>
        <div id="testtable"></div>
      </div>
    </div>`;
  $('#fitlist').onclick = (e) => { const c = e.target.closest('.chip'); if (c) cmd(`fit ${c.dataset.part} ${c.classList.contains('on') ? 'off' : 'on'}`); };
  $('#report').onclick = () => api('report').then((j) => toast('Bericht: ' + j.path)).catch(() => {});
  $('#cleartests').onclick = () => { tests.clear(); renderTests(); };
}

// Kalibrierschritte: bit = Bit in "valid"; flight = was die Flug-Firmware damit macht
const CAL_STEPS = [
  { id: 'gyro', bit: 1, title: 'Gyro-Nullpunkt' },
  { id: 'acc', bit: 2, title: 'Beschleunigung' },
  { id: 'mag', bit: 4, title: 'Magnetometer' },
  { id: 'axes', bit: 8, title: 'Achszuordnung' },
  { id: 'baro', bit: 16, title: 'Barometer' },
  { id: 'adc', bit: 32, title: 'Spannungsmessung' },
  { id: 'ina', bit: 64, title: 'Strommessung' },
  { id: 'servo', bit: 128, title: 'Servos' },
  { id: 'rot', bit: 0, title: 'Gyro-Skala prüfen' },
];
function buildCal() {
  $('#tab-cal').innerHTML = `
    <div class="grid cal-grid">
      <div class="card steps" id="steps"></div>
      <div><div class="card panel" id="calpanel"></div>
        <div class="card" style="margin-top:14px"><h3>Im Teensy</h3>
          <p class="note">Jede Kalibrierung ändert zuerst nur die Werte im Arbeitsspeicher. „Speichern“ schreibt den Block mit Prüfsumme ins EEPROM; die Flug-Firmware lädt ihn beim Start.</p>
          <div class="savebar"><button class="primary" data-cmd="cal save">Im Teensy speichern</button><button data-cmd="cal load">Gespeicherte Werte laden</button>
            <button data-cmd="cal defaults">Standardwerte</button><button data-cmd="cal erase" class="danger">Löschen …</button><span id="dirty"></span></div></div>
      </div>
    </div>`;
  $('#steps').onclick = (e) => { const b = e.target.closest('button'); if (b) { calStep = b.dataset.step; if (capture.kind) api('capture_stop'); fitResult = null; renderCal(); } };
  $('#calpanel').addEventListener('click', onCalClick);
}

function buildAct() {
  const names = ['Yaw', 'Pitch', 'Fallschirm', 'Beine / Drossel'];
  $('#tab-act').innerHTML = `
    <div class="grid act-grid">
      <div class="card"><h2>Servos</h2><p class="note">Braucht den 2S-Zweig. Die Firmware klemmt jeden Puls auf das Fenster aus <code>Config.h</code> und fragt nach jeder Bewegung, ob sie zu sehen war.</p>
        ${names.map((n, i) => `<div class="servo"><div><b>Servo ${i + 1}</b><br><small>${n}</small></div><div class="row">
          <button class="small" data-cmd="servo ${i + 1} center">Mitte</button><button class="small" data-cmd="servo ${i + 1} min">Min</button><button class="small" data-cmd="servo ${i + 1} max">Max</button>
          <button class="small" data-cmd="servo ${i + 1} sweep">Durchlauf</button><input type="number" id="us${i + 1}" value="1500" min="500" max="2500" step="10" aria-label="Puls in Mikrosekunden">
          <button class="small" data-us="${i + 1}">µs anfahren</button><button class="small" data-cmd="cal servo ${i + 1}">Trimmen …</button></div></div>`).join('')}
      </div>
      <div class="grid">
        <div class="card"><h2>Rollmotor</h2><p class="note">Zwei Pulse von 300 ms mit 30 % in beide Richtungen, nFAULT wird überwacht.</p><button data-cmd="motor">Motor prüfen</button></div>
        <div class="card"><h2>Pyrokanäle</h2>
          <div class="warnbox"><b>Nur mit Glühlämpchen oder 2-Ω-Widerstand, nie mit einer Ladung.</b> Die Firmware zündet nur bei scharfem ARM-Schalter und Durchgang und erst, nachdem du das Wort JA selbst eingetippt hast.</div>
          <dl class="kv" id="pyrostate" style="margin-bottom:10px"></dl>
          <div class="row"><label for="pyroms">Pulslänge</label><input type="number" id="pyroms" value="500" min="20" max="1000" step="10"> ms
            <button class="danger" data-pyro="1">Pyro 1 prüfen …</button><button class="danger" data-pyro="2">Pyro 2 prüfen …</button></div>
        </div>
      </div>
    </div>`;
  $('#tab-act').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.us) cmd(`servo ${b.dataset.us} us ${Math.round(+$('#us' + b.dataset.us).value) || 1500}`);
    if (b.dataset.pyro) cmd(`pyro ${b.dataset.pyro} ${Math.round(+$('#pyroms').value) || 500}`);
  });
}

function buildConsole() {
  $('#tab-console').innerHTML = `
    <div class="card"><div id="log" aria-live="off"></div>
      <form class="row" id="cmdform" style="margin-top:10px"><input type="text" id="cmdline" placeholder="Befehl, z. B. help, status, cal show, imu" style="flex:1" autocomplete="off" spellcheck="false">
        <button class="primary">Senden</button><button type="button" data-cmd="help">help</button><button type="button" data-cmd="status">status</button></form></div>`;
  $('#cmdform').onsubmit = (e) => { e.preventDefault(); const v = $('#cmdline').value.trim(); if (v) { cmd(v); $('#cmdline').value = ''; } };
}

// ------------------------------------------------------------------ Anzeigen
function renderHeader() {
  const c = S.connected, sup = last || {};
  const v1 = sup.v1 ?? S.supply.v1, v2 = sup.v2 ?? S.supply.v2, va = sup.varm ?? S.supply.varm;
  const pills = [`<span class="pill"><span class="dot ${c ? 'good' : ''}"></span>${c ? esc(S.sim ? 'Simulator' : S.port) : 'nicht verbunden'}</span>`];
  if (c) {
    if (S.imu_driver) pills.push(`<span class="pill">IMU <b>${esc(S.imu_driver)}</b></span>`);
    if (v1 != null) pills.push(`<span class="pill"><span class="dot ${v1 > 3.0 && v1 < 4.35 ? 'good' : 'warn'}"></span>1S <b>${fmt(v1)} V</b></span>`);
    if (v2 != null) pills.push(`<span class="pill"><span class="dot ${v2 > 6.0 ? 'good' : ''}"></span>2S <b>${v2 > 1 ? fmt(v2) + ' V' : 'aus'}</b></span>`);
    if (va != null) pills.push(`<span class="pill"><span class="dot ${va > 5 ? 'crit' : 'good'}"></span>ARM <b>${va > 5 ? 'SCHARF' : 'sicher'}</b></span>`);
    const nv = S.cal ? CAL_STEPS.filter((s) => s.bit && S.cal.valid & s.bit).length : 0;
    pills.push(`<span class="pill">Kalibriert <b>${nv}/8</b>${S.cal_dirty ? ' · ungespeichert' : ''}</span>`);
  }
  $('#pills').innerHTML = pills.join('');
  $('#connect').textContent = c ? 'Trennen' : 'Verbinden';
  $('#connect').classList.toggle('primary', !c);
  $('#port').disabled = c;
  $('#busy').classList.toggle('idle', !S.busy);
  $('#abort').disabled = !S.busy;
  $('#busytext').innerHTML = S.busy ? `Läuft: <code>${esc(S.cmd)}</code>${S.queued ? ` · ${S.queued} wartet` : ''}`
    : !c ? 'Nicht verbunden' : S.streaming ? `Bereit · Live-Daten ${S.hz} Hz` : 'Bereit';
  $$('[data-cmd]').forEach((b) => { b.disabled = !c; });
}

function renderLive() {
  const tg = $('#live-toggle');
  tg.textContent = S.want_stream ? 'Live an' : 'Live aus';
  tg.classList.toggle('on', !!S.want_stream);
  $$('#rate button').forEach((b) => b.classList.toggle('on', +b.dataset.hz === S.hz));
  $('#rec').textContent = S.recording ? 'Aufzeichnung stoppen' : 'Aufzeichnen';
  $('#rec').classList.toggle('on', !!S.recording);
  $('#simctl').hidden = !S.sim;
  const lbl = { imu: 'IMU', baro: 'Barometer 1', baro2: 'Barometer 2', ina: 'INA239 (Strom)', mag: 'Magnetometer', sht: 'SHT40 (Feuchte)', adxl: 'ADXL375', lora: 'LoRa E22', gps: 'GPS' };
  $('#parts').innerHTML = Object.keys(lbl).map((k) => {
    const fitted = S.fit[k], ok = S.parts[k];
    const st = fitted === undefined ? '–' : !fitted ? 'nicht bestückt' : ok === undefined ? 'bestückt' : ok ? 'bereit' : 'antwortet nicht';
    return `<dt>${lbl[k]}</dt><dd><span class="res ${!fitted ? 'NICHT_ERKANNT' : ok === false ? 'FEHL' : 'OK'}">${st}</span></dd>`;
  }).join('');
  charts.forEach((ch) => { ch.sub.textContent = ch.names.length === 3 ? (mode === 'raw' ? 'roh, Chip-Achsen' : 'kalibriert, Körperachsen') : ''; });
}

function tile(k, v, unit, sub = '', dot = '') {
  return `<div class="tile"><div class="k">${k}</div><div class="v">${v}<small>${unit}</small></div><div class="s">${dot ? `<span class="dot ${dot}"></span>` : ''}${sub}</div></div>`;
}
function renderTiles() {
  const d = last || {};
  const armed = d.varm > 5, has2s = d.v2 > 6;
  const pyro = (v) => (!armed ? ['–', 'ARM nicht scharf', ''] : v > 0.8 * d.varm ? ['Durchgang', fmt(v) + ' V', 'good'] : ['offen', fmt(v) + ' V', 'warn']);
  const p1 = pyro(d.py1), p2 = pyro(d.py2);
  $('#tiles').innerHTML = [
    tile('1S-Akku', fmt(d.v1), 'V', d.v1 == null ? '' : d.v1 > 3.0 && d.v1 < 4.35 ? 'im Bereich' : 'außerhalb 3,0–4,35 V', d.v1 == null ? '' : d.v1 > 3.0 && d.v1 < 4.35 ? 'good' : 'warn'),
    tile('2S-Akku', has2s || d.v2 > 1 ? fmt(d.v2) : '–', has2s || d.v2 > 1 ? 'V' : '', d.v2 == null ? '' : has2s ? 'Servos, Motor, Pyro versorgt' : 'nicht versorgt', has2s ? 'good' : ''),
    tile('ARM', d.varm == null ? '–' : armed ? 'SCHARF' : 'sicher', '', d.varm == null ? '' : fmt(d.varm) + ' V', d.varm == null ? '' : armed ? 'crit' : 'good'),
    tile('Pyro 1', p1[0], '', p1[1], p1[2]), tile('Pyro 2', p2[0], '', p2[1], p2[2]),
    tile('Strom 2S', fmt(d.ia, 3), d.ia == null ? '' : 'A', d.ia == null ? 'INA239 nicht bestückt' : 'VSERVO ' + fmt(d.vbus) + ' V'),
    tile('Druck', d.p == null ? '–' : fmt(d.p / 100, 2), d.p == null ? '' : 'hPa', 'Barometer ' + fmt(d.tb, 1) + ' °C'),
    tile('Temperatur', fmt(d.ti, 1), '°C', 'IMU'),
    tile('Feuchte', fmt(d.rh, 1), d.rh == null ? '' : '%', d.rh == null ? '' : 'SHT40 ' + fmt(d.ts, 1) + ' °C'),
    tile('IMU-Sätze', d.n == null ? '–' : String(d.n), '', 'gemittelt je Zeile'),
  ].join('');
  $('#a-tilt').textContent = fmt(d.tilt, 1) + ' °';
  $('#a-head').textContent = d.mag_cal ? fmt(d.heading, 0) + ' °' : 'Magnetometer unkalibriert';
  const ps = $('#pyrostate');
  if (ps) ps.innerHTML = `<dt>2S-Zweig</dt><dd>${d.v2 == null ? '–' : has2s ? fmt(d.v2) + ' V' : 'nicht versorgt'}</dd><dt>ARM</dt><dd>${d.varm == null ? '–' : armed ? 'SCHARF' : 'sicher'}</dd>
    <dt>Durchgang 1</dt><dd>${p1[0]}</dd><dt>Durchgang 2</dt><dd>${p2[0]}</dd>`;
}

const RES_TEXT = { OK: 'in Ordnung', FEHL: 'Fehler', SKIP: 'übersprungen', NICHT_ERKANNT: 'nicht bestückt' };
function renderTests() {
  const rows = [...tests.entries()];
  const fails = rows.filter(([, t]) => t.result === 'FEHL').length;
  $('#failbadge').hidden = !fails; $('#failbadge').textContent = fails;
  $('#testsum').textContent = rows.length ? `${rows.length} Prüfungen · ${fails} Fehler · ${rows.filter(([, t]) => t.result === 'SKIP').length} übersprungen · ${rows.filter(([, t]) => t.result === 'NICHT_ERKANNT').length} nicht bestückt` : '';
  $('#testtable').innerHTML = rows.length ? `<table><thead><tr><th>Prüfung</th><th>Ergebnis</th><th>Detail</th><th>Befehl</th><th>Zeit</th></tr></thead><tbody>${rows.map(([n, t]) =>
    `<tr><td class="mono">${esc(n)}</td><td><span class="res ${t.result}">${RES_TEXT[t.result]}</span></td><td>${esc(t.detail)}</td><td class="mono">${esc(t.cmd || '')}</td><td class="mono">${t.time}</td></tr>`).join('')}</tbody></table>`
    : '<div class="empty">Noch keine Prüfung gelaufen. „Alle ohne Bewegung“ prüft Spannungen, Sensoren, Timing und Speicher, ohne dass sich etwas bewegt.</div>';
  const names = { imu: 'IMU', baro: 'Baro 1', baro2: 'Baro 2', ina: 'INA239', mag: 'Magnetometer', sht: 'SHT40', adxl: 'ADXL375', lora: 'LoRa', gps: 'GPS' };
  $('#fitlist').innerHTML = Object.keys(names).map((k) => `<button class="chip ${S.fit[k] ? 'on' : ''}" data-part="${k}" ${S.connected ? '' : 'disabled'} aria-pressed="${!!S.fit[k]}"><span class="dot"></span>${names[k]}</button>`).join('');
}

// ---- Kalibrierung
const calVals = (pairs) => `<dl class="vals">${pairs.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>`;
function calPanel(id) {
  const c = S.cal || {};
  const run = (label, command, primary = true) => `<button ${primary ? 'class="primary"' : ''} data-cmd="${command}">${label}</button>`;
  switch (id) {
    case 'gyro': return `<h2>Gyro-Nullpunkt</h2>
      <p>Der Gyro zeigt in Ruhe nicht genau null. Die Firmware mittelt die Drehrate über die gewählte Zeit und merkt sich Nullpunkt, Rauschen und Temperatur.</p>
      <div class="how"><ol><li>Platine flach hinlegen und nicht berühren.</li><li>Messen. Bei Bewegung beginnt die Messung von vorn.</li></ol></div>
      <div class="row"><label for="gyros">Dauer</label><input type="number" id="gyros" value="10" min="2" max="120"> s <button class="primary" data-run="gyro">Nullpunkt messen</button></div>
      ${calVals([['Nullpunkt x y z', vec(c.gyro_bias_dps, 4) + ' °/s'], ['Rauschen x y z', vec(c.gyro_noise_dps, 4) + ' °/s'], ['Temperatur dabei', fmt(c.gyro_bias_temp_c, 1) + ' °C']])}
      <p class="note">Die Flug-Firmware misst den Nullpunkt vor jedem Start auf der Rampe neu. Der Wert hier prüft das Bauteil (Betrag unter 5 °/s) und wird für die Anzeige benutzt.</p>`;
    case 'acc': return `<h2>Beschleunigung</h2>
      <p>Offset und Skalierung je Achse, so dass der Sensor in jeder Lage genau 1 g misst. Die Flug-Firmware benutzt diese Werte (Lage auf der Rampe, Starterkennung).</p>
      <h3 style="margin-top:14px">Geführt: sechs Lagen</h3>
      <div class="how">Die Firmware sagt jede Lage an (flach, über Kopf, vier Kanten). Platine jeweils ruhig halten und bestätigen.</div>
      ${run('Sechs Lagen starten', 'cal acc')}
      <h3 style="margin-top:18px">Frei: beliebige Lagen, Fit am PC</h3>
      <div class="how">Aufnahme starten und die Platine nacheinander in mindestens sechs verschiedene Lagen bringen, jede etwa zwei Sekunden ruhig halten. Jede Achse muss einmal nach oben und einmal nach unten zeigen; genau ausrichten muss man nicht. Der Fit sucht Offset und Skalierung, bei denen der Betrag in allen Lagen 1 g ist.</div>
      <div id="cap-acc"></div>
      ${calVals([['Offset x y z', vec(c.acc_offset_ms2, 4) + ' m/s²'], ['Skalierung x y z', vec(c.acc_scale, 5)]])}`;
    case 'mag': return `<h2>Magnetometer</h2>
      <p>Eisen und Ströme auf der Platine verschieben (Hard-Iron) und verzerren (Soft-Iron) das gemessene Erdfeld. Dreht man die Platine in alle Richtungen, liegen die Messpunkte auf einem Ellipsoid; der Fit macht daraus wieder eine Kugel um den Ursprung.</p>
      <h3 style="margin-top:14px">Auf der Platine</h3>
      <div class="row"><label for="mags">Dauer</label><input type="number" id="mags" value="40" min="10" max="180"> s <button class="primary" data-run="mag">Drehen und fitten</button></div>
      <h3 style="margin-top:18px">Am PC mit Bild der Abdeckung</h3>
      <div class="how">Aufnahme starten und die Platine langsam um alle Achsen drehen, auch über Kopf, bis die drei Ansichten rundum gefüllt sind. Weg von Stahl, Lautsprechern und Netzteilen.</div>
      <div id="cap-mag"></div>
      ${calVals([['Hard-Iron x y z', vec(c.mag_offset_gauss, 4) + ' gauss'], ['Soft-Iron (3×3)', (c.mag_soft_iron || []).map((v, i) => fmt(v, 4) + (i % 3 === 2 ? '<br>' : '   ')).join('')], ['Feldbetrag', fmt(c.mag_field_gauss, 3) + ' gauss']])}
      <p class="note">Die Werte gelten für die Umgebung, in der gemessen wurde. In der fertig montierten Avionik (Akkus, Servos, Schrauben) wiederholen. Die Flug-Firmware nutzt das Magnetometer nur am Boden für den Kurs, und nur wenn auch die Achszuordnung gemacht ist.</p>`;
    case 'axes': return `<h2>Achszuordnung</h2>
      <p>Legt fest, welche Chip-Achse welche Achse des Raketenkörpers ist (x, y quer, z entlang der Rollachse zur Spitze). Ohne diesen Schritt nimmt die Flug-Firmware die Chip-Achsen unverändert.</p>
      <div class="how"><ol><li>Spitze nach oben halten: die Achse mit +1 g wird Körper-z.</li><li>Die Seite nach oben halten, die Körper +x sein soll.</li><li>20 s in alle Richtungen drehen: das Magnetometer wird gegen die Drehrate zugeordnet.</li></ol></div>
      ${run('Achsen bestimmen', 'cal axes')}
      ${calVals([['IMU: Körper x y z', axesText(c.imu_axis_map, c.imu_axis_sign)], ['Magnetometer: Körper x y z', axesText(c.mag_axis_map, c.mag_axis_sign)]])}`;
    case 'baro': return `<h2>Barometer</h2>
      <p>Bodendruck und Rauschen in Ruhe. Ein Rauschen unter 6 Pa entspricht etwa einem halben Meter.</p>
      <div class="row"><label for="baros">Dauer</label><input type="number" id="baros" value="20" min="5" max="120"> s <button class="primary" data-run="baro">Bodenreferenz messen</button></div>
      ${calVals([['Bodendruck', fmt(c.baro_ground_pa, 1) + ' Pa'], ['Rauschen', fmt(c.baro_noise_pa, 2) + ' Pa'], ['Temperatur', fmt(c.baro_ground_temp_c, 1) + ' °C']])}
      <p class="note">Die Flug-Firmware misst den Bodendruck vor jedem Start selbst; hier geht es um das Rauschen des Sensors.</p>`;
    case 'adc': return `<h2>Spannungsmessung</h2>
      <p>Der Teensy misst 1S, 2S und ARM über Spannungsteiler. Ein Multimeter liefert den wahren Wert, daraus wird ein Korrekturfaktor je Kanal (höchstens ±10 %).</p>
      <div class="how">Multimeter bereithalten. Die Firmware fragt für jeden versorgten Kanal nach dem gemessenen Wert in Volt.</div>
      ${run('1S, 2S und ARM abgleichen', 'cal adc')}
      ${calVals([['Faktor 1S', fmt((c.adc_gain || [])[4], 4)], ['Faktor 2S', fmt((c.adc_gain || [])[5], 4)], ['Faktor ARM', fmt((c.adc_gain || [])[6], 4)]])}
      <p class="note">Bisher wendet nur die Testkonsole diese Faktoren an, die Flug-Firmware noch nicht.</p>`;
    case 'ina': return `<h2>Strommessung</h2>
      <p>Nullpunkt des INA239 ohne Last und, wenn eine bekannte Last da ist, die Verstärkung gegen das Multimeter.</p>
      ${S.fit.ina ? '' : '<div class="how">Der INA239 steht in der Bestückungsliste auf „aus“. Nach dem Einlöten unter Prüfungen → Bestückung einschalten.</div>'}
      ${run('Strommessung abgleichen', 'cal ina')}
      ${calVals([['Offset', fmt(c.ina_offset_a * 1000, 2) + ' mA'], ['Verstärkung', fmt(c.ina_gain, 4)]])}`;
    case 'servo': return `<h2>Servos</h2>
      <p>Mitte und mechanische Grenzen je Servo in Mikrosekunden. Beim Trimmen fährt der Servo in kleinen Schritten; Mitte, Minimum und Maximum werden an der jeweiligen Stelle gesetzt.</p>
      <div class="row">${[1, 2, 3, 4].map((i) => `<button data-cmd="cal servo ${i}">Servo ${i} trimmen</button>`).join('')}</div>
      ${calVals((c.servo_us || []).map((s, i) => [`Servo ${i + 1} (${['Yaw', 'Pitch', 'Fallschirm', 'Beine'][i]})`, `Mitte ${s[0]} · ${s[1]} bis ${s[2]} µs`]))}
      <p class="note">Braucht den 2S-Zweig. Die Flug-Firmware nimmt Mitte und Grenzen bisher aus <code>Config.h</code>, nicht aus diesen Werten.</p>`;
    case 'rot': return `<h2>Gyro-Skala prüfen</h2>
      <p>Prüft, ob der Gyro Winkel richtig misst: die über die Zeit aufsummierte Drehrate muss den gedrehten Winkel ergeben. Es wird nichts gespeichert.</p>
      <div class="how"><ol><li>Platine an eine gerade Kante (Buch, Tischkante) legen und ruhig halten.</li><li>Um eine Achse genau eine volle Umdrehung (oder 90°, 180°) drehen und wieder an die Kante legen.</li><li>Für die anderen Achsen wiederholen.</li></ol></div>
      <div id="cap-rot"></div>`;
    default: return '';
  }
}
function axesText(map, sign) {
  if (!map) return '–';
  return map.map((m, i) => `${'xyz'[i]} = ${sign[i] > 0 ? '+' : '−'}${'xyz'[m]}`).join('   ') + '  (Chip)';
}

function renderCal() {
  const v = S.cal ? S.cal.valid : 0;
  $('#steps').innerHTML = CAL_STEPS.map((s) => `<button data-step="${s.id}" class="${s.id === calStep ? 'active' : ''}">
    <span class="dot ${s.bit && v & s.bit ? 'good' : ''}"></span>${s.title}<span class="state">${!s.bit ? 'Prüfung' : v & s.bit ? 'gemacht' : 'offen'}</span></button>`).join('');
  const keep = document.activeElement && document.activeElement.id, keepVal = keep && $('#calpanel #' + keep) ? $('#' + keep).value : null;
  $('#calpanel').innerHTML = calPanel(calStep);
  if (keepVal !== null && $('#' + keep)) $('#' + keep).value = keepVal;
  $('#dirty').innerHTML = S.cal_dirty ? '<span class="dirty"><span class="dot warn"></span>Ungespeicherte Änderungen im Arbeitsspeicher</span>' : '';
  renderCapture();
  $$('#tab-cal [data-cmd]').forEach((b) => { b.disabled = !S.connected; });
}

function fitBox() {
  const r = fitResult;
  if (!r) return '';
  if (!('offset' in r)) return `<div class="resultbox bad"><b>Fit nicht möglich:</b> ${esc(r.reason)}</div>`;
  const body = r.kind === 'acc'
    ? calVals([['Offset x y z', vec(r.offset, 4) + ' m/s²'], ['Skalierung x y z', vec(r.scale, 5)], ['Abweichung von 1 g vorher', fmt(r.rms_before, 3) + ' m/s² (RMS)'], ['Abweichung von 1 g nachher', fmt(r.rms_after, 3) + ' m/s² (RMS)'], ['Lagen', r.n]])
    : calVals([['Hard-Iron x y z', vec(r.offset, 4) + ' gauss'], ['Feldbetrag', fmt(r.field, 3) + ' gauss'], ['Residuum', fmt(r.residual_pct, 1) + ' %'], ['Achsverhältnis', fmt(r.axis_ratio, 2)], ['Abdeckung', `${r.octants}/8 Oktanten, ${fmt(r.coverage * 100, 0)} % der Kugel`], ['Punkte', r.n]]);
  return `<div class="resultbox ${r.ok ? 'ok' : 'bad'}"><b>${r.ok ? 'Fit plausibel' : 'Fit außerhalb der Grenzen'}</b>${r.ok ? '' : `: ${esc(r.reason)}`}${body}
    <div class="row"><button class="primary" data-cap="apply" ${r.ok ? '' : 'disabled'}>An die Platine senden</button><span class="note">Setzt die Werte im Arbeitsspeicher des Teensy (<code>cal set</code>). Danach „Im Teensy speichern“.</span></div></div>`;
}

function setHTML(el, html) { if (el && el._html !== html) { el.innerHTML = html; el._html = html; } }
function renderCapture() {
  // Gerüst je Aufnahme einmal bauen, danach nur Texte und Klassen ändern: die Knöpfe bleiben
  // stehen, sonst gingen Klicks verloren, während viermal je Sekunde neue Werte kommen.
  const acc = $('#cap-acc'), mag = $('#cap-mag'), rot = $('#cap-rot');
  const on = (k) => capture.kind === k;
  const startBtn = (kind, label) => `<div class="row"><button class="primary" data-cap="start" data-kind="${kind}" ${S.connected ? '' : 'disabled'}>${label}</button></div>`;
  if (acc) {
    if (on('acc')) {
      if (!$('#accfaces')) {
        acc.innerHTML = `<div class="row"><button data-cap="stop">Aufnahme beenden</button><button class="primary" data-cap="fit" id="accfitbtn">Fit berechnen</button>
          <span class="pill"><span class="dot" id="accdot"></span><span id="accstill"></span></span><span class="note" id="accn"></span></div>
          <div class="faces" id="accfaces">${['+x', '−x', '+y', '−y', '+z', '−z'].map((n) => `<span class="face">${n} oben</span>`).join('')}</div><div id="accfit"></div>`;
        acc._html = null;
      }
      const f = capture.faces || [];
      $('#accfitbtn').disabled = !(capture.n >= 6);
      $('#accdot').className = 'dot ' + (capture.still ? 'good' : 'warn');
      $('#accstill').textContent = capture.still ? 'ruhig' : 'bewegt';
      $('#accn').textContent = `${capture.n || 0} Lagen erfasst (mindestens 6)`;
      $$('#accfaces .face').forEach((el, i) => el.classList.toggle('on', !!f[i]));
      setHTML($('#accfit'), fitBox());
    } else setHTML(acc, startBtn('acc', 'Aufnahme starten') + (fitResult && fitResult.kind === 'acc' ? fitBox() : ''));
  }
  if (mag) {
    if (on('mag')) {
      if (!$('#magscatter')) {
        mag.innerHTML = `<div class="row"><button data-cap="stop">Aufnahme beenden</button><button class="primary" data-cap="fit">Fit berechnen</button><span class="note" id="magstat"></span></div>
          <div class="scatter" id="magscatter">${['x–y', 'x–z', 'y–z'].map((n) => `<figure><canvas></canvas><figcaption>${n}</figcaption></figure>`).join('')}</div>
          <div class="legend" style="margin:0 0 6px"><span><i style="background:var(--series-1)"></i>roh</span><span><i style="background:var(--series-3)"></i>nach dem Fit</span></div><div id="magfit"></div>`;
        mag._html = null;
      }
      $('#magstat').textContent = `${capture.n || 0} Punkte · ${fmt((capture.coverage || 0) * 100, 0)} % der Kugel abgedeckt`;
      setHTML($('#magfit'), fitBox());
      drawScatter();
    } else setHTML(mag, startBtn('mag', 'Aufnahme starten') + (fitResult && fitResult.kind === 'mag' ? fitBox() : ''));
  }
  if (rot) {
    if (on('rot')) {
      if (!$('#rotstate')) {
        rot.innerHTML = `<div class="row"><button data-cap="stop">Beenden</button><button data-cap="start" data-kind="rot">Neue Drehung</button>
          <span class="pill"><span class="dot" id="rotdot"></span><span id="rotstate"></span></span></div>
          <dl class="vals"><dt>Winkel x y z</dt><dd id="rotangle"></dd></dl><div id="rotresult"></div>`;
        rot._html = null;
      }
      const r = capture.result, st = capture.state;
      $('#rotdot').className = 'dot ' + (st === 'bereit' || st === 'fertig' ? 'good' : 'warn');
      $('#rotstate').textContent = { 'warte auf Ruhe': 'Platine ruhig halten …', bereit: 'Bereit: jetzt drehen', dreht: 'Dreht … danach wieder ruhig halten', fertig: 'Fertig' }[st] || 'Platine ruhig halten …';
      $('#rotangle').textContent = vec(capture.angle, 1) + ' °';
      setHTML($('#rotresult'), r ? `<div class="resultbox ${r.scale_error_pct !== null && Math.abs(r.scale_error_pct) < 2 ? 'ok' : 'bad'}"><b>Achse ${r.axis}: ${fmt(r.angle_deg, 1)}° gemessen</b>${r.reference_deg ? `, verglichen mit ${fmt(r.reference_deg, 0)}°: Abweichung ${fmt(r.scale_error_pct, 2)} %` : ''}
          <p class="note" style="margin:6px 0 0">Bis etwa ±2 % ist bei einer Drehung von Hand normal. Größere Abweichung: Drehung wiederholen, sonst Bauteil oder Messbereich prüfen.</p></div>` : '');
    } else setHTML(rot, startBtn('rot', 'Prüfung starten'));
  }
}

function drawScatter() {
  const cvs = $$('#magscatter canvas');
  if (!cvs.length) return;
  const corr = fitResult && fitResult.corrected, all = corr ? magPts.concat(corr) : magPts;
  let r = 0.1;
  for (const p of all) r = Math.max(r, Math.abs(p[0]), Math.abs(p[1]), Math.abs(p[2]));
  r *= 1.1;
  [[0, 1], [0, 2], [1, 2]].forEach(([a, b], k) => {
    const cv = cvs[k], dpr = window.devicePixelRatio || 1, w = cv.clientWidth;
    if (!w) return;
    cv.width = cv.height = Math.round(w * dpr);
    const g = cv.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const X = (v) => w / 2 + (v / r) * (w / 2), Y = (v) => w / 2 - (v / r) * (w / 2);
    g.strokeStyle = css('--border'); g.lineWidth = 1;
    g.beginPath(); g.moveTo(0, w / 2); g.lineTo(w, w / 2); g.moveTo(w / 2, 0); g.lineTo(w / 2, w); g.stroke();
    if (corr) { g.beginPath(); g.arc(w / 2, w / 2, (fitResult.field / r) * (w / 2), 0, 2 * Math.PI); g.stroke(); }
    g.fillStyle = css('--series-1'); g.globalAlpha = 0.55;
    for (const p of magPts) g.fillRect(X(p[a]) - 1, Y(p[b]) - 1, 2, 2);
    if (corr) { g.fillStyle = css('--series-3'); for (const p of corr) g.fillRect(X(p[a]) - 1, Y(p[b]) - 1, 2, 2); }
    g.globalAlpha = 1;
  });
}

function onCalClick(e) {
  const b = e.target.closest('button');
  if (!b) return;
  const num = (id, def) => Math.round(+($('#' + id) || {}).value) || def;
  if (b.dataset.run === 'gyro') cmd(`cal gyro ${num('gyros', 10)}`);
  if (b.dataset.run === 'mag') cmd(`cal mag ${num('mags', 40)}`);
  if (b.dataset.run === 'baro') cmd(`cal baro ${num('baros', 20)}`);
  const cap = b.dataset.cap;
  if (cap === 'start') { fitResult = null; magPts = []; capture = { kind: b.dataset.kind }; api('capture_start', { kind: b.dataset.kind }).then(renderCapture).catch(() => {}); }
  if (cap === 'stop') { capture = { kind: null }; api('capture_stop').then(renderCal).catch(() => {}); }
  if (cap === 'fit') api('capture_fit').then((j) => { fitResult = j.fit; renderCapture(); }).catch(() => {});
  if (cap === 'apply') api('capture_apply').then(() => { toast('Werte an die Platine geschickt. Zum Behalten „Im Teensy speichern“.'); capture = { kind: null }; fitResult = null; renderCapture(); }).catch(() => {});
}

// ---- Rückfragen der Firmware (WAIT / ASK / CONFIRM)
let promptKey = '';
function renderPrompt() {
  const p = S.prompt, box = $('#prompt');
  if (!p) { box.hidden = true; promptKey = ''; return; }
  const key = p.kind + '|' + p.text + '|' + (p.context || []).join('|');
  if (key === promptKey && !box.hidden) return;
  promptKey = key;
  const ctx = (p.context || []).length ? `<div class="ctx">${esc(p.context.join('\n'))}</div>` : '';
  let inner;
  if (p.kind === 'WAIT' && p.text === 'Befehl') {            // Servo trimmen (cal servo)
    inner = `<div class="kind">Servo trimmen</div><div class="q">${esc((p.context || []).slice(-1)[0] || 'Servo')}</div>
      <div class="row">${[['--', '−50'], ['-', '−10'], ['+', '+10'], ['++', '+50']].map(([a, t]) => `<button data-ans="${a}">${t} µs</button>`).join('')}
        <input type="number" id="pin" placeholder="µs" aria-label="Puls in Mikrosekunden"><button data-ansinput>Anfahren</button></div>
      <div class="row"><button data-ans="c">Hier ist die Mitte</button><button data-ans="a">Hier ist das Minimum</button><button data-ans="b">Hier ist das Maximum</button></div>
      <div class="row"><span class="spacer"></span><button data-ans="q">Abbrechen</button><button class="primary" data-ans="ok">Übernehmen</button></div>`;
  } else if (p.kind === 'WAIT') {
    const yesno = /n = nein/.test(p.text);
    const text = p.text.replace(/\s*\(Enter = ja[^)]*\)\s*$/, '').replace(/[,.]?\s*(dann )?Enter( zum Start)?\s*$/, '');
    inner = `<div class="kind">Die Platine wartet</div><div class="q">${esc(text)}</div>${ctx}
      <div class="row"><span class="spacer"></span><button data-ans="q">Abbrechen</button>${yesno ? '<button data-ans="n">Nein</button>' : ''}<button class="primary" data-ans="" id="pdef">${yesno ? 'Ja' : 'Weiter'}</button></div>`;
  } else if (p.kind === 'ASK') {
    inner = `<div class="kind">Messwert eingeben</div><div class="q">${esc(p.text)}</div>${ctx}
      <div class="row"><input type="text" id="pin" inputmode="decimal" placeholder="Zahl, z. B. 3,98" style="flex:1"><button data-ans="">Überspringen</button><button class="primary" data-ansinput>Senden</button></div>`;
  } else {
    inner = `<div class="kind">Bestätigung nötig</div><div class="q">${esc(p.text)}</div>${ctx}
      <div class="row"><input type="text" id="pin" placeholder="JA eintippen" style="flex:1" autocomplete="off"><button data-ans="n">Abbrechen</button><button class="danger" data-ansinput>Senden</button></div>`;
  }
  box.innerHTML = `<div class="dialog ${p.kind === 'CONFIRM' ? 'confirm' : ''}" role="dialog" aria-modal="true">${inner}</div>`;
  box.hidden = false;
  const focus = $('#pin', box) || $('#pdef', box);
  if (focus) focus.focus();
}
$('#prompt').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  if (b.dataset.ans !== undefined) api('answer', { text: b.dataset.ans }).catch(() => {});
  else if (b.dataset.ansinput !== undefined) { const v = $('#pin').value.trim(); if (v) api('answer', { text: v }).catch(() => {}); }
});
$('#prompt').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.target.id === 'pin') { const v = e.target.value.trim(); if (v) api('answer', { text: v }).catch(() => {}); }
});

// ---- Konsole
function logLine(ev) {
  const log = $('#log'), atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
  const d = document.createElement('div');
  d.className = ev.kind + (ev.result ? ' ' + ev.result : '');
  d.textContent = ev.kind === 'tx' ? '› ' + ev.text : ev.text;
  log.append(d);
  while (log.childElementCount > 3000) log.firstChild.remove();
  if (atEnd) log.scrollTop = log.scrollHeight;
  if (ev.kind === 'error') toast(ev.text, true);
}

// ------------------------------------------------------------------ Ereignisse vom Server
function onState(st) {
  const calChanged = JSON.stringify(st.cal) !== JSON.stringify(S.cal) || st.connected !== S.connected || st.cal_dirty !== S.cal_dirty || JSON.stringify(st.fit) !== JSON.stringify(S.fit) || st.capture !== S.capture;
  const wasConnected = S.connected;
  S = st;
  if (!S.connected) { last = null; capture = { kind: null }; }
  if (!S.capture && capture.kind) capture = { kind: null };
  renderHeader(); renderLive(); renderPrompt();
  if (calChanged) { renderCal(); renderTests(); }
  if (wasConnected !== S.connected) { renderTiles(); if (S.connected) charts.forEach((c) => c.clear()); }
}
function onEvent(ev) {
  switch (ev.type) {
    case 'state': onState(ev.state); break;
    case 'data': for (const row of ev.rows) charts.forEach((c) => c.push(row)); last = ev.last; break;
    case 'line': logLine(ev); break;
    case 'test': tests.delete(ev.name); tests.set(ev.name, { cmd: ev.cmd, result: ev.result, detail: ev.detail, time: new Date().toLocaleTimeString('de-DE') }); renderTests(); break;
    case 'done': if (ev.result === 'FEHL') toast(`${ev.cmd}: Fehler, Details unter Prüfungen und Konsole`, true); break;
    case 'capture':
      if (ev.kind && ev.kind === capture.kind) {
        if (ev.points) magPts = magPts.concat(ev.points);
        const keys = JSON.stringify([ev.n, ev.faces, ev.still, ev.state, ev.result, ev.coverage, ev.angle]);
        if (keys !== capture._keys) { capture = { ...capture, ...ev, _keys: keys }; renderCapture(); }
      }
      break;
    default: break;
  }
}

function frame() {
  if ($('#tab-live').classList.contains('active')) {
    charts.forEach((c) => c.draw());
    drawAttitude($('#att'), last && last.q);
  }
  requestAnimationFrame(frame);
}

async function loadPorts() {
  const j = await api('ports');
  const sel = $('#port'), cur = sel.value;
  sel.innerHTML = j.ports.map((p) => `<option value="${esc(p.device)}">${esc(p.device === 'sim' ? 'Simulator' : p.device)}${p.teensy ? ' · Teensy' : ''}${p.description && p.device !== 'sim' ? ' · ' + esc(p.description) : ''}</option>`).join('');
  const teensy = j.ports.find((p) => p.teensy);
  sel.value = S.port || (j.ports.some((p) => p.device === cur) ? cur : teensy ? teensy.device : j.ports[j.ports.length - 1].device);
}

function init() {
  buildLive(); buildTests(); buildCal(); buildAct(); buildConsole();
  renderHeader(); renderLive(); renderTiles(); renderTests(); renderCal();
  $('#tabs').onclick = (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    $$('#tabs button').forEach((x) => x.classList.toggle('active', x === b));
    $$('section.tab').forEach((s) => s.classList.toggle('active', s.id === 'tab-' + b.dataset.tab));
    if (b.dataset.tab === 'cal') drawScatter();
  };
  document.addEventListener('click', (e) => { const b = e.target.closest('[data-cmd]'); if (b && !b.disabled) cmd(b.dataset.cmd); });
  $('#connect').onclick = () => (S.connected ? api('disconnect') : api('connect', { port: $('#port').value })).catch(() => {});
  $('#refresh').onclick = () => loadPorts().catch(() => {});
  $('#abort').onclick = () => api('abort').catch(() => {});
  loadPorts().catch(() => {});
  const es = new EventSource('/events?token=' + encodeURIComponent(TOKEN));
  es.onmessage = (m) => onEvent(JSON.parse(m.data));
  es.onerror = () => { if (S.connected !== null) { S = { ...S, connected: false, busy: false, prompt: null }; renderHeader(); renderPrompt(); } };
  setInterval(renderTiles, 250);
  setInterval(() => { if (!S.busy) renderHeader(); }, 1000);
  requestAnimationFrame(frame);
}
init();
