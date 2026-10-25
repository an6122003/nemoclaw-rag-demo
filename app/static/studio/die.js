/* The studio page's living circuit.
 *
 * A chip on a porcelain page, its traces fanning out like a board breakout:
 * white, slightly embossed, and lit by NVIDIA-green pulses when work happens.
 * The page calls Die.token(), Die.step(), Die.retrieve(), Die.tool(), Die.item()
 * and Die.batch(); the GPU load from /api/telemetry sets the idle pulse rate;
 * Die.focus() moves the chip to where each chapter wants it.
 *
 * Plain canvas 2D, no dependencies. Pauses when the page is hidden; draws one
 * still frame for people who ask their system for less motion.
 */
(function () {
  'use strict';

  const NV = [118, 185, 0];
  const REDUCED = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const ease = t => 1 - Math.pow(1 - t, 3);
  const pick = arr => arr[(Math.random() * arr.length) | 0];
  const rand = (a, b) => a + Math.random() * (b - a);

  let canvas, ctx, dpr = 1, vw = 0, vh = 0;
  let traces = [], cells = [], regions = {}, pulses = [];
  const spec = {sm: 48, cores: 20, gpuCores: 0, memGb: 0, label: ''};
  let running = false, last = 0, clock = 0, boot = 0;
  let ambient = 0, ambientTarget = 0, memLevel = 0, memTarget = 0;
  let batchRate = 0, batchAcc = 0, idleAcc = 0, waveAt = 2.2;
  let hover = null, hoverAmt = 0;
  let glow = null;
  const pointer = {x: 0, y: 0, tx: 0, ty: 0};

  // Where the chip sits for each chapter: anchor in the viewport (0..1), and a zoom.
  const cam = {ax: 0.72, ay: 0.5, zoom: 1, alpha: 1, labels: 1};
  const SHOTS = {
    home: {ax: 0.73, ay: 0.5, zoom: 1.0, labels: 1},
    lab1: {ax: 0.83, ay: 0.3, zoom: 0.7, labels: 0.75},
    lab2: {ax: 0.83, ay: 0.3, zoom: 0.7, labels: 0.75},
    lab3: {ax: 0.83, ay: 0.3, zoom: 0.7, labels: 0.75},
    ent: {ax: 0.83, ay: 0.3, zoom: 0.7, labels: 0.75},
  };
  const PKG = 110;  // half the package, in world units
  const DIE = 66;   // half the die

  /* ------------------------------------------------------------ layout --- */
  function mulberry(seed) {
    return () => {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function polyline(pts, w, glowy) {
    const segs = [];
    let len = 0;
    for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); segs.push(l); len += l; }
    return {pts, segs, len, w, glow: glowy};
  }
  function buildTraces() {
    const r = mulberry(1307);
    traces = [];
    const sides = [{dx: 1, dy: 0, n: 15}, {dx: -1, dy: 0, n: 15}, {dx: 0, dy: 1, n: 11}, {dx: 0, dy: -1, n: 11}];
    for (const s of sides) {
      for (let i = 0; i < s.n; i++) {
        const t = ((i + 0.5) / s.n) * 2 - 1;          // -1 .. 1 along the edge
        const along = t * (PKG - 16);
        let x = s.dx ? s.dx * PKG : along, y = s.dy ? s.dy * PKG : along;
        const pts = [[x, y]];
        const l1 = 26 + r() * 10;
        x += s.dx * l1; y += s.dy * l1; pts.push([x, y]);
        // fan out: the further from the middle of the edge, the longer the diagonal
        const sign = t >= 0 ? 1 : -1, ex = s.dx ? 0 : sign, ey = s.dy ? 0 : sign;
        const l2 = (10 + Math.abs(t) * 150 + r() * 12) * 0.7071;
        x += (s.dx + ex) * l2; y += (s.dy + ey) * l2; pts.push([x, y]);
        const l3 = 160 + r() * (s.dx ? 900 : 560);
        x += s.dx * l3; y += s.dy * l3; pts.push([x, y]);
        if (r() < 0.5) {  // a last jog, and on
          const l4 = (30 + r() * 90) * 0.7071, sg = r() < 0.5 ? 1 : -1;
          x += (s.dx + (s.dx ? 0 : sg)) * l4; y += (s.dy + (s.dy ? 0 : sg)) * l4; pts.push([x, y]);
          const l5 = 60 + r() * 380;
          x += s.dx * l5; y += s.dy * l5; pts.push([x, y]);
        }
        traces.push(polyline(pts, 2.2 + r() * 2.2, r() < 0.45));
      }
    }
  }
  function buildDie() {
    cells = []; regions = {};
    const cell = (kind, x, y, w, h, extra) => { const c = Object.assign({kind, x, y, w, h, heat: 0, base: 0}, extra || {}); cells.push(c); return c; };
    // GPU: the SM grid on the right of the die
    const cols = 8, rows = Math.ceil(spec.sm / cols), gx = -18, gy = -58, gw = 78, gh = 98, gap = 1.6;
    const cw = (gw - (cols - 1) * gap) / cols, ch = (gh - (rows - 1) * gap) / rows;
    regions.gpu = {x: gx, y: gy, w: gw, h: gh, cells: []};
    for (let i = 0; i < spec.sm; i++) {
      const c = i % cols, rr = Math.floor(i / cols);
      regions.gpu.cells.push(cell('sm', gx + c * (cw + gap), gy + rr * (ch + gap), cw, ch, {col: c, row: rr}));
    }
    // CPU: cores on the left, four a row
    const n = spec.cores, ccols = 4, crows = Math.ceil(n / ccols), cx = -58, cy = -58, cww = 34, chh = 64;
    const kw = (cww - (ccols - 1) * gap) / ccols, kh = (chh - (crows - 1) * gap) / crows;
    regions.cpu = {x: cx, y: cy, w: cww, h: chh, cells: []};
    for (let i = 0; i < n; i++) regions.cpu.cells.push(cell('core', cx + (i % ccols) * (kw + gap), cy + Math.floor(i / ccols) * (kh + gap), kw, kh));
    // cache under the cores, L2 and the NPU along the bottom
    regions.slc = {x: -58, y: 10, w: 34, h: 30, cells: []};
    for (let i = 0; i < 8; i++) regions.slc.cells.push(cell('cache', -58 + (i % 4) * 8.9, 10 + Math.floor(i / 4) * 15.2, 7.3, 13.6));
    regions.l2 = {x: -18, y: 44, w: 78, h: 14, cells: []};
    for (let i = 0; i < 8; i++) regions.l2.cells.push(cell('cache', -18 + i * 9.9, 44, 8.3, 14));
    regions.npu = {x: -58, y: 44, w: 34, h: 14, cells: [cell('npu', -58, 44, 34, 14)]};
    // memory: controllers along the top and bottom edge of the die
    regions.mem = {x: -DIE, y: -DIE, w: DIE * 2, h: DIE * 2, cells: []};
    for (let i = 0; i < 8; i++) {
      regions.mem.cells.push(cell('mem', -58 + i * 15.2, -64, 13.6, 3.2));
      regions.mem.cells.push(cell('mem', -58 + i * 15.2, 60.8, 13.6, 3.2));
    }
  }

  /* ------------------------------------------------------------ camera --- */
  function view() {
    const s = Math.min(vw / 1600, vh / 900) * 1.18 * cam.zoom;
    return {s, ox: vw * cam.ax + pointer.x * 14, oy: vh * cam.ay + pointer.y * 9};
  }

  /* ------------------------------------------------------------ pulses --- */
  function at(tr, d) {
    let rest = clamp(d, 0, tr.len);
    for (let i = 0; i < tr.segs.length; i++) {
      if (rest <= tr.segs[i]) {
        const k = rest / (tr.segs[i] || 1), a = tr.pts[i], b = tr.pts[i + 1];
        return [lerp(a[0], b[0], k), lerp(a[1], b[1], k)];
      }
      rest -= tr.segs[i];
    }
    return tr.pts[tr.pts.length - 1];
  }
  function pulse(dir, speed, size) {
    const tr = pick(traces);
    pulses.push({tr, d: 0, dir: dir || (Math.random() < 0.5 ? 1 : -1), speed: speed || rand(340, 560), size: size || 1});
    if (pulses.length > 160) pulses.splice(0, pulses.length - 160);
  }
  const heat = (c, v) => { c.heat = Math.min(1.25, c.heat + v); };

  /* ------------------------------------------------------------ events --- */
  const Die = {
    token(n) {
      for (let i = 0; i < (n || 1); i++) {
        heat(pick(regions.gpu.cells), 0.8);
        if (Math.random() < 0.5) pulse(1, rand(480, 640));
      }
    },
    step(progress, loss) {
      const k = clamp((loss == null ? 1 : loss) / 2.5, 0.3, 1);
      regions.gpu.cells.forEach(c => setTimeout(() => heat(c, 0.45 + 0.5 * k), (c.col + c.row * 0.6) * 32));
      for (let i = 0; i < 5; i++) pulse(-1, rand(420, 600));
    },
    retrieve(n) {
      regions.slc.cells.concat(regions.mem.cells).forEach(c => heat(c, rand(0.4, 1)));
      for (let i = 0; i < (n || 5) * 4; i++) setTimeout(() => pulse(-1, rand(520, 760), 1.1), i * 45);
    },
    tool() {
      for (let i = 0; i < 8; i++) setTimeout(() => { heat(pick(regions.cpu.cells), 0.95); if (i % 2) pulse(1, rand(420, 560)); }, i * 70);
    },
    item() {
      heat(pick(regions.gpu.cells), 0.6);
      pulse(Math.random() < 0.6 ? -1 : 1, rand(560, 820));
    },
    batch(rate) { batchRate = Math.max(0, rate || 0); },
    telemetry(util, memShare) {
      if (util != null) ambientTarget = clamp(util / 100, 0, 1);
      if (memShare != null) memTarget = clamp(memShare, 0, 1);
    },
    focus(name, seconds) {
      const s = SHOTS[name] || SHOTS.home;
      if (window.gsap && !REDUCED) gsap.to(cam, Object.assign({duration: seconds == null ? 1.6 : seconds, ease: 'expo.inOut', overwrite: true}, s));
      else { Object.assign(cam, s); requestDraw(); }
    },
    highlight(name) { hover = name || null; },
    configure(o) {
      const before = spec.sm + '/' + spec.cores;
      Object.assign(spec, o || {});
      spec.sm = clamp(Math.round(spec.sm || 48), 8, 96);
      spec.cores = clamp(Math.round(spec.cores || 20), 4, 40);
      if (spec.sm + '/' + spec.cores !== before) buildDie();
    },
    opacity(a) { cam.alpha = clamp(a, 0, 1); if (!running) requestDraw(); },
    boot() {
      boot = 0;
      if (REDUCED) { boot = 1; requestDraw(); return; }
      const all = cells.slice().sort((a, b) => (a.x + a.y) - (b.x + b.y));
      all.forEach((c, i) => setTimeout(() => heat(c, 0.9), 700 + i * 8));
      for (let i = 0; i < 26; i++) setTimeout(() => pulse(1, rand(420, 640)), 900 + i * 60);
    },
  };
  window.Die = Die;

  /* -------------------------------------------------------------- loop --- */
  function update(dt) {
    clock += dt;
    boot = Math.min(1, boot + dt / 1.8);
    pointer.x = lerp(pointer.x, pointer.tx, Math.min(1, dt * 2));
    pointer.y = lerp(pointer.y, pointer.ty, Math.min(1, dt * 2));
    ambient = lerp(ambient, ambientTarget, Math.min(1, dt * 1.5));
    memLevel = lerp(memLevel, memTarget, Math.min(1, dt * 1.2));
    hoverAmt = lerp(hoverAmt, hover ? 1 : 0, Math.min(1, dt * 6));
    idleAcc += dt * (2.4 + ambient * 16);
    while (idleAcc > 1) {
      idleAcc -= 1;
      pulse();
      heat(pick(Math.random() < 0.7 ? regions.gpu.cells : cells), 0.25 + ambient * 0.5);
    }
    // every few seconds a soft wave runs across the GPU, like a kernel launch
    waveAt -= dt;
    if (waveAt <= 0) {
      waveAt = rand(3.2, 5.5);
      regions.gpu.cells.forEach(c => setTimeout(() => heat(c, 0.32 + ambient * 0.4), c.col * 70 + c.row * 18));
    }
    batchAcc += dt * batchRate;
    while (batchAcc > 1) { batchAcc -= 1; Die.item(); }
    const decay = Math.exp(-dt * 2.4);
    for (const c of cells) c.heat *= decay;
    for (let i = pulses.length - 1; i >= 0; i--) {
      const p = pulses[i];
      p.d += p.speed * dt;
      if (p.d > p.tr.len + 80) {
        if (p.dir < 0) heat(pick(regions.gpu.cells), 0.35);
        pulses.splice(i, 1);
      }
    }
    const lit = memLevel * 8;  // memory in use: controllers fill like a gauge
    regions.mem.cells.forEach((c, i) => { const k = Math.floor(i / 2); c.base = k < Math.floor(lit) ? 0.35 : k < lit ? 0.35 * (lit % 1) : 0; });
  }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }
  function strokeTrace(tr, upTo) {
    ctx.beginPath();
    ctx.moveTo(tr.pts[0][0], tr.pts[0][1]);
    let acc = 0;
    for (let i = 1; i < tr.pts.length; i++) {
      const l = tr.segs[i - 1];
      if (acc + l >= upTo) {
        const k = (upTo - acc) / (l || 1), a = tr.pts[i - 1], b = tr.pts[i];
        ctx.lineTo(lerp(a[0], b[0], k), lerp(a[1], b[1], k));
        break;
      }
      ctx.lineTo(tr.pts[i][0], tr.pts[i][1]);
      acc += l;
    }
    ctx.stroke();
  }

  function draw() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (cam.alpha <= 0.01) return;
    const {s, ox, oy} = view();
    ctx.setTransform(s * dpr, 0, 0, s * dpr, ox * dpr, oy * dpr);
    ctx.globalAlpha = cam.alpha;
    const px = 1 / s;
    const grow = ease(boot);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // a green halo breathing under the chip
    const breath = 0.5 + 0.5 * Math.sin(clock * 1.1);
    const halo = ctx.createRadialGradient(0, 0, PKG * 0.6, 0, 0, PKG * (3.1 + ambient));
    halo.addColorStop(0, `rgba(118,185,0,${0.16 + 0.08 * breath + ambient * 0.12})`);
    halo.addColorStop(0.45, `rgba(118,185,0,${0.05 + 0.03 * breath})`);
    halo.addColorStop(1, 'rgba(118,185,0,0)');
    ctx.fillStyle = halo;
    ctx.fillRect(-PKG * 4.2, -PKG * 4.2, PKG * 8.4, PKG * 8.4);

    // traces: a green under-glow on some, a shadow for depth, then the white trace
    for (const tr of traces) {
      if (!tr.glow) continue;
      ctx.strokeStyle = `rgba(118,185,0,${0.1 + 0.05 * breath})`;
      ctx.lineWidth = tr.w + 10 * px * 2;
      strokeTrace(tr, tr.len * grow);
      ctx.strokeStyle = 'rgba(118,185,0,0.22)';
      ctx.lineWidth = tr.w + 3.2 * px * 2;
      strokeTrace(tr, tr.len * grow);
    }
    ctx.save();
    ctx.translate(0, 2.2 * px);
    ctx.strokeStyle = 'rgba(27,26,25,0.07)';
    for (const tr of traces) { ctx.lineWidth = tr.w + 1.8 * px; strokeTrace(tr, tr.len * grow); }
    ctx.restore();
    ctx.strokeStyle = '#ffffff';
    for (const tr of traces) { ctx.lineWidth = tr.w; strokeTrace(tr, tr.len * grow); }
    // vias at the ends
    if (grow > 0.98) {
      for (const tr of traces) {
        const [x, y] = tr.pts[tr.pts.length - 1];
        ctx.beginPath(); ctx.arc(x, y + 1.6 * px, tr.w * 1.7, 0, Math.PI * 2); ctx.fillStyle = 'rgba(27,26,25,0.08)'; ctx.fill();
        ctx.beginPath(); ctx.arc(x, y, tr.w * 1.7, 0, Math.PI * 2); ctx.fillStyle = '#ffffff'; ctx.fill();
        ctx.beginPath(); ctx.arc(x, y, tr.w * 0.6, 0, Math.PI * 2); ctx.fillStyle = 'rgba(27,26,25,0.16)'; ctx.fill();
      }
    }

    // pulses: a green comet on the trace
    for (const p of pulses) {
      const tr = p.tr;
      const head = p.dir > 0 ? p.d : tr.len - p.d;
      const tail = p.dir > 0 ? head - 95 : head + 95;
      if (head < 0 || head > tr.len) continue;
      const h = at(tr, head), t0 = at(tr, tail);
      const g = ctx.createLinearGradient(t0[0], t0[1], h[0], h[1]);
      g.addColorStop(0, 'rgba(118,185,0,0)');
      g.addColorStop(1, 'rgba(118,185,0,0.95)');
      ctx.strokeStyle = g;
      ctx.lineWidth = tr.w * 1.05 * p.size;
      ctx.beginPath();
      ctx.moveTo(t0[0], t0[1]);
      // follow the bends between tail and head
      let acc = 0;
      const lo = Math.min(head, tail), hi = Math.max(head, tail);
      const mids = [];
      for (let i = 1; i < tr.pts.length - 1; i++) { acc += tr.segs[i - 1]; if (acc > lo && acc < hi) mids.push(tr.pts[i]); }
      (p.dir > 0 ? mids : mids.reverse()).forEach(m => ctx.lineTo(m[0], m[1]));
      ctx.lineTo(h[0], h[1]);
      ctx.stroke();
      const r = 24 * p.size * Math.max(0.8, px * 1.2);
      ctx.drawImage(glow, h[0] - r, h[1] - r, r * 2, r * 2);
      ctx.beginPath(); ctx.arc(h[0], h[1], tr.w * 0.55, 0, Math.PI * 2); ctx.fillStyle = '#ffffff'; ctx.fill();
    }

    // the package
    ctx.save();
    ctx.shadowColor = 'rgba(27,26,25,0.20)';
    ctx.shadowBlur = 46 * s * dpr;
    ctx.shadowOffsetY = 20 * s * dpr;
    roundRect(-PKG, -PKG, PKG * 2, PKG * 2, 16);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.restore();
    const pg = ctx.createLinearGradient(-PKG, -PKG, PKG, PKG);
    pg.addColorStop(0, '#ffffff'); pg.addColorStop(1, '#efede8');
    roundRect(-PKG, -PKG, PKG * 2, PKG * 2, 16);
    ctx.fillStyle = pg; ctx.fill();
    ctx.lineWidth = px; ctx.strokeStyle = 'rgba(27,26,25,0.12)'; ctx.stroke();
    // pins where the traces leave
    ctx.fillStyle = '#d8d5ce';
    for (const tr of traces) {
      const [x, y] = tr.pts[0];
      const horiz = Math.abs(x) >= PKG - 0.5;
      ctx.fillRect(horiz ? x - (x > 0 ? 7 : 0) : x - 2.2, horiz ? y - 2.2 : y - (y > 0 ? 7 : 0), horiz ? 7 : 4.4, horiz ? 4.4 : 7);
    }
    // engraving
    if (spec.label) {
      ctx.fillStyle = 'rgba(27,26,25,0.32)';
      ctx.font = '600 7px "Plus Jakarta Sans", sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(spec.label.toUpperCase(), PKG - 12, PKG - 12);
      ctx.textAlign = 'left';
    }
    // the die
    roundRect(-DIE - 4, -DIE - 4, DIE * 2 + 8, DIE * 2 + 8, 6);
    ctx.fillStyle = '#e9e7e1'; ctx.fill();
    ctx.lineWidth = px; ctx.strokeStyle = 'rgba(27,26,25,0.14)'; ctx.stroke();
    for (const c of cells) {
      const h = clamp(c.heat + c.base, 0, 1.2);
      ctx.fillStyle = h > 0.02
        ? `rgb(${Math.round(lerp(220, NV[0], Math.min(1, h)))},${Math.round(lerp(218, NV[1], Math.min(1, h)))},${Math.round(lerp(211, NV[2], Math.min(1, h)))})`
        : (c.kind === 'mem' ? '#cfccc4' : c.kind === 'cache' ? '#d9d6cf' : c.kind === 'npu' ? '#dad8d1' : '#dedcd5');
      ctx.fillRect(c.x, c.y, c.w, c.h);
    }
    for (const c of cells) {
      const h = c.heat + c.base * 0.5;
      if (h < 0.12) continue;
      const r = Math.max(c.w, c.h) * (1.2 + h);
      ctx.globalAlpha = cam.alpha * clamp(h, 0, 1) * 0.55;
      ctx.drawImage(glow, c.x + c.w / 2 - r, c.y + c.h / 2 - r, r * 2, r * 2);
    }
    ctx.globalAlpha = cam.alpha;
    if (hover && regions[hover] && hoverAmt > 0.02) {
      const r = regions[hover];
      ctx.strokeStyle = `rgba(200,161,107,${0.9 * hoverAmt})`;
      ctx.lineWidth = 1.6 * px;
      roundRect(r.x - 2.5, r.y - 2.5, r.w + 5, r.h + 5, 2.5);
      ctx.stroke();
    }

    // callouts, flat on the screen
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    labels(s, ox, oy);
    ctx.globalAlpha = 1;
  }

  function labels(s, ox, oy) {
    if (cam.labels <= 0.02 || boot < 0.6) return;
    const P = (x, y) => [ox + x * s, oy + y * s];
    const items = [
      ['gpu', 60, -58, 1, -1, spec.gpuCores ? `GPU · ${spec.gpuCores.toLocaleString('en-US')} CUDA cores` : 'GPU'],
      ['cpu', -58, -58, -1, -1, `CPU · ${spec.cores} cores`],
      ['mem', 60, 66, 1, 1, spec.memGb ? `Unified memory · ${spec.memGb} GB` : 'Unified memory'],
      ['slc', -58, 40, -1, 1, 'Cache'],
    ];
    ctx.font = '600 11px "Plus Jakarta Sans", sans-serif';
    ctx.textBaseline = 'middle';
    for (const [key, x, y, sx, sy, text] of items) {
      const [ax, ay] = P(x, y);
      const on = hover === key ? hoverAmt : 0;
      const reach = (PKG - Math.abs(y)) * s + 40;   // leave the package before turning
      const ex = ax + sx * (Math.abs(sx * PKG - x) * s + 34), ey = ay + sy * (reach * 0.35 + 26);
      const a = cam.alpha * cam.labels * clamp((boot - 0.6) * 2.5, 0, 1);
      ctx.globalAlpha = a;
      ctx.strokeStyle = on > 0.05 ? `rgba(200,161,107,${0.6 + 0.4 * on})` : 'rgba(27,26,25,0.28)';
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(ex, ey); ctx.lineTo(ex + sx * 18, ey); ctx.stroke();
      ctx.fillStyle = on > 0.05 ? '#9a7546' : 'rgba(27,26,25,0.62)';
      ctx.textAlign = sx > 0 ? 'left' : 'right';
      ctx.fillText(text, ex + sx * 24, ey);
      ctx.beginPath(); ctx.arc(ax, ay, 2.2, 0, Math.PI * 2); ctx.fillStyle = on > 0.05 ? '#c8a16b' : 'rgba(27,26,25,0.45)'; ctx.fill();
    }
    ctx.textAlign = 'left';
  }

  /* ------------------------------------------------------- the machine --- */
  let raf = 0, drawRequested = false;
  function requestDraw() {
    if (drawRequested || !ctx) return;
    drawRequested = true;
    requestAnimationFrame(() => { drawRequested = false; if (!running) draw(); });
  }
  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - last) / 1000 || 0);
    last = now;
    update(dt);
    draw();
  }
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    vw = window.innerWidth; vh = window.innerHeight;
    canvas.width = Math.round(vw * dpr); canvas.height = Math.round(vh * dpr);
    canvas.style.width = vw + 'px'; canvas.style.height = vh + 'px';
    if (!running) requestDraw();
  }
  function start() { if (running || REDUCED) return; running = true; last = performance.now(); raf = requestAnimationFrame(frame); }
  function stop() { running = false; cancelAnimationFrame(raf); }

  Die.init = function (el) {
    canvas = el;
    ctx = canvas.getContext('2d');
    glow = document.createElement('canvas');
    glow.width = glow.height = 128;
    const g = glow.getContext('2d'), grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    grd.addColorStop(0, 'rgba(150,215,20,0.9)');
    grd.addColorStop(0.25, 'rgba(118,185,0,0.45)');
    grd.addColorStop(0.6, 'rgba(118,185,0,0.12)');
    grd.addColorStop(1, 'rgba(118,185,0,0)');
    g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
    buildTraces();
    buildDie();
    resize();
    window.addEventListener('resize', resize);
    window.addEventListener('pointermove', e => {
      pointer.tx = (e.clientX / Math.max(1, vw) - 0.5) * 2;
      pointer.ty = (e.clientY / Math.max(1, vh) - 0.5) * 2;
    }, {passive: true});
    document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
    if (REDUCED) { boot = 1; requestDraw(); } else start();
  };
})();
