import { type ReactNode, useEffect, useRef } from "react";

/*
 * The hero title's pointer effect, after the studied reference.
 *
 * The text is drawn, pixel for pixel, onto a canvas laid exactly over it (through an SVG that embeds
 * the page's own font, so the copy matches the live text). The pixels are grouped into 12 x 12 blocks.
 * A moving pointer knocks the blocks it passes loose: each packs its pixels into a tight square and
 * becomes a rigid body (Rapier physics) that is pushed away from the pointer, spins, and falls onto a
 * floor at the foot of the text, where the pointer can bat it about. A moment after the pointer
 * leaves, every block flies home, lowest first, unpacks into its glyph, and the live text returns.
 *
 * Fine pointers with hover only; never with reduced motion. The physics engine loads on first touch.
 * All lengths are CSS px; the physics world works in blocks (12 device pixels).
 */

const F = 1 / 60; // fixed physics step, seconds
const BLOCK = 12; // cells per block side
const RELEASE_DELAY = 450; // ms after the pointer leaves before blocks fly home
const RETURN_MAX = Math.round(2 / F); // ticks: a block always lands within 2 s
const STAGGER_MAX = Math.round(0.2 / F);
const STAGGER_RANDOM = Math.round(0.0667 / F);
const STAGGER_PER_ROW = 0.017 / F;
const FLASH_DECAY = Math.exp(-F / 0.11);
const RETURN_SMOOTH = 1 - Math.exp(-6.02 * F);
const RETURN_DRAG = Math.exp(-1.4 * F);
const SPIN_DECAY = Math.exp(-12 * F);

const hash = (t: number) => {
  const e = 43758.5453 * Math.sin(127.1 * t + 311.7);
  return e - Math.floor(e);
};
const wrapAngle = (a: number) => Math.atan2(Math.sin(a), Math.cos(a));

type RapierT = typeof import("@dimforge/rapier2d-compat");
let rapier: Promise<RapierT> | null = null;
const loadRapier = () =>
  (rapier ??= import("@dimforge/rapier2d-compat").then(async (m) => {
    const R = (m as unknown as { default?: RapierT }).default ?? m;
    await R.init();
    return R;
  }));

const fontCache = new Map<string, Promise<string>>();
/** The @font-face rules for one family, with the font inlined, so an SVG image can use it. */
function inlineFaces(family: string): Promise<string> {
  const hit = fontCache.get(family);
  if (hit) return hit;
  const p = (async () => {
    const rules: CSSFontFaceRule[] = [];
    const walk = (list: CSSRuleList) => {
      for (const r of Array.from(list)) {
        if (r instanceof CSSFontFaceRule) {
          if (r.style.getPropertyValue("font-family").replace(/["']/g, "").trim() === family) rules.push(r);
        } else if ("cssRules" in r) walk((r as CSSGroupingRule).cssRules);
      }
    };
    for (const s of Array.from(document.styleSheets)) {
      try {
        walk(s.cssRules);
      } catch {
        /* a cross-origin sheet: skip */
      }
    }
    const out = await Promise.all(
      rules.map(async (r) => {
        const src = /url\(\s*["']?([^"')]+)["']?\s*\)/.exec(r.style.getPropertyValue("src"))?.[1];
        if (!src) return "";
        const url = new URL(src, r.parentStyleSheet?.href ?? document.baseURI);
        const bytes = new Uint8Array(await (await fetch(url)).arrayBuffer());
        let bin = "";
        for (let i = 0; i < bytes.length; i += 8192) bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
        const fmt = url.pathname.endsWith(".woff") ? "woff" : "woff2";
        const weight = r.style.getPropertyValue("font-weight");
        return `@font-face{font-family:"${family}";src:url(data:font/${fmt};base64,${btoa(bin)}) format("${fmt}");${weight ? `font-weight:${weight};` : ""}}`;
      }),
    );
    return out.join("");
  })();
  fontCache.set(family, p);
  p.catch(() => fontCache.delete(family));
  return p;
}

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const STYLE_PROPS = [
  "font-family", "font-feature-settings", "font-kerning", "font-size", "font-stretch", "font-style", "font-variant",
  "font-variation-settings", "font-weight", "letter-spacing", "line-height", "text-rendering", "text-transform", "word-spacing",
];

/** Rasterise the text node of `text` into an alpha map the size of `host`, at device pixels. */
async function rasterise(host: HTMLElement, text: HTMLElement) {
  await document.fonts.ready;
  const content = (text.textContent ?? "").trim();
  if (!content) return null;
  const range = document.createRange();
  range.selectNodeContents(text);
  const hr = host.getBoundingClientRect();
  const tr = range.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  if (!tr.width) return null;
  // The canvas sits on the device-pixel grid, so its pixels land exactly on screen pixels:
  // snap its top-left to the grid and size it in whole device pixels, never stretched.
  const gx = Math.floor(hr.left * dpr) / dpr;
  const gy = Math.floor(hr.top * dpr) / dpr;
  const W = Math.ceil((hr.right - gx) * dpr);
  const H = Math.ceil((hr.bottom - gy) * dpr);
  if (W < 1 || H < 1) return null;
  const cs = getComputedStyle(text);
  const run = STYLE_PROPS.map((p) => `${p}:${cs.getPropertyValue(p)}`).join(";");
  const family = cs.fontFamily.split(",")[0].replace(/["']/g, "").trim();
  const faces = await inlineFaces(family);
  if (!faces) return null;
  const w = W / dpr;
  const h = H / dpr;
  const left = tr.left - gx;
  const top = tr.top - gy;
  // A 1 px marker on the baseline (an inline-block sits on it) lets us find where the copy's baseline
  // landed, to compare with the live text's.
  const svg = (marker: boolean) =>
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${w} ${h}"><style>${esc(faces)}</style>` +
    `<foreignObject x="0" y="0" width="${w}" height="${h}"><div xmlns="http://www.w3.org/1999/xhtml" style="position:relative;width:${w}px;height:${h}px">` +
    `<div style="${esc(`position:absolute;left:${left}px;top:${top}px;${run};line-height:${tr.height}px;white-space:pre;color:${marker ? "transparent" : "#fff"}`)}">` +
    (marker ? '<span style="display:inline-block;width:8px;height:1px;margin-right:-8px;background:#fff"></span>' : "") +
    `${esc(content)}</div></div></foreignObject></svg>`;
  const paint = async (markup: string, dy: number) => {
    const img = new Image();
    img.decoding = "sync";
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(markup)}`;
    await img.decode();
    const c = document.createElement("canvas");
    c.width = W;
    c.height = H;
    const ctx = c.getContext("2d", { willReadFrequently: true })!;
    ctx.drawImage(img, 0, dy, W, H);
    return ctx;
  };
  try {
    // Where the copy's baseline is: the first opaque row under the marker, plus one.
    const m = await paint(svg(true), 0);
    const mx = Math.min(W - 1, Math.max(0, Math.floor(left * dpr)));
    const mw = Math.min(W - mx, Math.ceil(8 * dpr));
    const md = m.getImageData(mx, 0, mw, H).data;
    let copyBase = -1;
    for (let yy = 0; yy < H && copyBase < 0; yy++)
      for (let xx = 0; xx < mw; xx++) if (md[(yy * mw + xx) * 4 + 3] >= 128) { copyBase = yy + 1; break; }
    // Where the live text's baseline is: a zero-size inline-block sits on it.
    const probe = document.createElement("span");
    probe.style.cssText = "display:inline-block;width:0;height:0";
    text.append(probe);
    const liveBase = Math.round(probe.getBoundingClientRect().top * dpr) - Math.round(gy * dpr);
    probe.remove();
    const step = Math.round(dpr);
    const dy = copyBase < 0 ? 0 : Math.max(-step, Math.min(step, liveBase - copyBase));
    const ctx = await paint(svg(false), dy);
    const alpha = ctx.getImageData(0, 0, W, H).data;
    let sum = 0;
    for (let i = 3; i < alpha.length; i += 4) sum += alpha[i];
    if (sum === 0) return null;
    return { alpha, W, H, dpr, left: gx - hr.left, top: gy - hr.top };
  } catch {
    return null;
  }
}

type Field = Awaited<ReturnType<typeof rasterise>> & {};

/** One running effect: physics, blocks and drawing, for one title element. */
function createEffect(R: RapierT, canvas: HTMLCanvasElement, field: NonNullable<Field>, color: () => string) {
  const { alpha, W, H, dpr } = field;
  const g = 1 / dpr; // cell size in CSS px
  const bpx = 1 / g / BLOCK; // CSS px -> blocks
  const DETACH_R = 15 * bpx;
  const PUSH = 28 * bpx;
  const SPEED_CAP = 420 * bpx;
  const SWEEP_R = 12 * bpx;
  const MIN_MOVE = 0.5 * bpx;
  const IMPULSE_SPEED_CAP = 900 * bpx;
  const IMPULSE_CAP = 45 * bpx;
  const FLASH_SPEED = 90 * bpx;
  const RET_MIN = 180 / g; // cells/s
  const RET_ACC_Y = 3400 / g;
  const RET_ACC = 3600 / g;
  const RET_VMAX = 1100 / g;
  const RET_ACC_X = 2600 / g;
  const ARRIVE = 2 * RET_ACC * F * F;

  // blocks: home position (cells), cell offsets of their pixels, packed layout
  const cols = Math.ceil(W / BLOCK);
  const rows = Math.ceil(H / BLOCK);
  const idOf = new Int32Array(cols * rows).fill(-1);
  const cellsOf: number[][] = [];
  let maxRow = 0;
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      if (alpha[(y * W + x) * 4 + 3] === 0) continue;
      const k = Math.floor(y / BLOCK) * cols + Math.floor(x / BLOCK);
      if (idOf[k] < 0) {
        idOf[k] = cellsOf.length;
        cellsOf.push([]);
      }
      cellsOf[idOf[k]].push(y * W + x);
      if (y > maxRow) maxRow = y;
    }
  const n = cellsOf.length;
  const homeX = new Float32Array(n), homeY = new Float32Array(n);
  for (let k = 0; k < idOf.length; k++) {
    const b = idOf[k];
    if (b < 0) continue;
    homeX[b] = (k % cols) * BLOCK;
    homeY[b] = Math.floor(k / cols) * BLOCK;
  }
  const half = new Float32Array(n);
  // each block's pixels as a little canvas: original glyph cut-out, and the packed square
  const glyph: HTMLCanvasElement[] = [];
  const packed: HTMLCanvasElement[] = [];
  const ink = color();
  for (let b = 0; b < n; b++) {
    const cells = cellsOf[b];
    const side = Math.ceil(Math.sqrt(cells.length));
    half[b] = Math.max(0.16, side / 24 - 0.006);
    const off = (BLOCK - side) / 2;
    const gc = document.createElement("canvas");
    gc.width = gc.height = BLOCK;
    const pc = document.createElement("canvas");
    pc.width = pc.height = BLOCK;
    const gx = gc.getContext("2d")!, px = pc.getContext("2d")!;
    const gi = gx.createImageData(BLOCK, BLOCK), pi = px.createImageData(BLOCK, BLOCK);
    cells.forEach((c, i) => {
      const x = c % W, y = Math.floor(c / W);
      const a = alpha[c * 4 + 3];
      const gIdx = ((y - homeY[b]) * BLOCK + (x - homeX[b])) * 4;
      gi.data[gIdx + 3] = a;
      const qx = Math.floor(off + (i % side)), qy = Math.floor(off + Math.floor(i / side));
      pi.data[(qy * BLOCK + qx) * 4 + 3] = a;
    });
    gx.putImageData(gi, 0, 0);
    px.putImageData(pi, 0, 0);
    for (const ctx of [gx, px]) {
      ctx.globalCompositeOperation = "source-in";
      ctx.fillStyle = ink;
      ctx.fillRect(0, 0, BLOCK, BLOCK);
    }
    glyph.push(gc);
    packed.push(pc);
  }

  // state: 0 home, 1 physics body, 2 flying home
  const state = new Uint8Array(n);
  const x = Float32Array.from(homeX), y = Float32Array.from(homeY); // cells
  const vx = new Float32Array(n), vy = new Float32Array(n), rot = new Float32Array(n);
  const flash = new Float32Array(n), wait = new Uint8Array(n), ticks = new Uint16Array(n);
  const spinDir = new Int8Array(n), jitter = new Uint8Array(n);
  for (let b = 0; b < n; b++) {
    spinDir[b] = hash(b + 17) < 0.5 ? -1 : 1;
    jitter[b] = Math.floor(hash(b + 53) * STAGGER_RANDOM);
  }
  const floorTop = (maxRow + 1) / BLOCK;

  const world = new R.World({ x: 0, y: 1200 * bpx });
  world.timestep = F;
  world.numSolverIterations = 8;
  const events = new R.EventQueue(true);
  world.createCollider(R.ColliderDesc.cuboid(2048, 1).setTranslation(cols / 2, floorTop + 1).setFriction(0.62).setRestitution(0));
  const bodies: (InstanceType<RapierT["RigidBody"]> | null)[] = Array(n).fill(null);
  const byHandle = new Map<number, number>();
  const sweep = new R.Capsule(0, SWEEP_R);
  let loose = 0, moving = 0;
  let last: { x: number; y: number } | null = null;

  const detach = (b: number, px: number, py: number, dx: number, dy: number, speed: number) => {
    const cx = homeX[b] / BLOCK + 0.5, cy = homeY[b] / BLOCK + 0.5;
    const ox = cx - px, oy = cy - py, d = Math.hypot(ox, oy) || 1, s = Math.min(speed, SPEED_CAP);
    const body = world.createRigidBody(
      R.RigidBodyDesc.dynamic().setTranslation(cx, cy)
        .setLinvel((ox / d) * PUSH + dx * s * 0.12, (oy / d) * PUSH + dy * s * 0.12)
        .setAngvel(spinDir[b] * Math.min(0.45 + 0.018 * s, 1.2))
        .setLinearDamping(0.55).setAngularDamping(1.8).setCcdEnabled(true),
    );
    const col = world.createCollider(
      R.ColliderDesc.cuboid(half[b], half[b]).setDensity(1).setFriction(0.62).setRestitution(0.06)
        .setActiveEvents(R.ActiveEvents.COLLISION_EVENTS),
      body,
    );
    bodies[b] = body;
    byHandle.set(col.handle, b);
    state[b] = 1;
    rot[b] = 0;
    flash[b] = 0;
    loose++;
  };

  const release = (b: number) => {
    const body = bodies[b]!;
    const t = body.translation(), v = body.linvel();
    x[b] = BLOCK * t.x - 6;
    y[b] = BLOCK * t.y - 6;
    vx[b] = BLOCK * v.x;
    vy[b] = BLOCK * v.y;
    rot[b] = wrapAngle(body.rotation());
    vy[b] = homeY[b] > y[b] ? Math.max(vy[b], RET_MIN) : Math.min(vy[b], -RET_MIN);
    world.removeRigidBody(body);
    bodies[b] = null;
    loose--;
    state[b] = 2;
    const height = Math.max(0, Math.floor((maxRow + 1 - y[b]) / BLOCK));
    wait[b] = Math.min(STAGGER_MAX, Math.floor(height * STAGGER_PER_ROW) + jitter[b]);
    ticks[b] = 0;
  };

  /** Steer a block home: capped speed, approach along the line to home. True once it has landed. */
  const flyHome = (b: number) => {
    rot[b] *= SPIN_DECAY;
    if (Math.abs(rot[b]) < 0.01) rot[b] = 0;
    ticks[b]++;
    const dx = homeX[b] - x[b], dy = homeY[b] - y[b], dist = Math.hypot(dx, dy);
    if (dist <= ARRIVE || ticks[b] >= RETURN_MAX) {
      x[b] = homeX[b]; y[b] = homeY[b]; vx[b] = vy[b] = rot[b] = 0; state[b] = 0;
      return true;
    }
    let ax = 42 * dx;
    if (ax > RET_ACC_X) ax = RET_ACC_X;
    if (ax < -RET_ACC_X) ax = -RET_ACC_X;
    let nx = (vx[b] + ax * F) * RETURN_DRAG;
    const ay = dy > ARRIVE ? RET_ACC_Y : dy < -ARRIVE ? -RET_ACC_Y : 0;
    let ny = vy[b] + ay * F;
    let sp = Math.hypot(nx, ny);
    if (sp > RET_VMAX) { nx *= RET_VMAX / sp; ny *= RET_VMAX / sp; sp = RET_VMAX; }
    const ux = dx / dist, uy = dy / dist;
    const cap = Math.min(RET_VMAX, Math.sqrt(2 * RET_ACC * dist));
    if (sp > cap) { nx += (ux * cap - nx) * RETURN_SMOOTH; ny += (uy * cap - ny) * RETURN_SMOOTH; }
    let along = nx * ux + ny * uy;
    let sx = nx - along * ux, sy = ny - along * uy;
    along = Math.min(cap, Math.max(0.62 * cap, along));
    const side = Math.hypot(sx, sy), sideMax = Math.sqrt(Math.max(0, cap * cap - along * along));
    if (side > sideMax) { sx *= sideMax / side; sy *= sideMax / side; }
    vx[b] = along * ux + sx;
    vy[b] = along * uy + sy;
    x[b] += vx[b] * F;
    y[b] += vy[b] * F;
    return false;
  };

  const ctx = canvas.getContext("2d")!;
  const draw = () => {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let b = 0; b < n; b++) {
      if (state[b] === 0) {
        ctx.setTransform(1, 0, 0, 1, homeX[b], homeY[b]);
        ctx.drawImage(glyph[b], 0, 0);
        continue;
      }
      const c = Math.cos(rot[b]), s = Math.sin(rot[b]);
      ctx.setTransform(c, s, -s, c, x[b] + 6, y[b] + 6);
      ctx.globalAlpha = flash[b] > 0 ? 1 - (42 / 255) * flash[b] : 1;
      ctx.drawImage(packed[b], -6, -6);
      ctx.globalAlpha = 1;
    }
  };

  /** One physics tick. Returns whether anything still moves. */
  const tick = (pointer: { active: boolean; x: number; y: number }, holding: boolean) => {
    let busy = false;
    if (pointer.active) {
      const px = pointer.x * bpx, py = pointer.y * bpx;
      const from = last ?? { x: px, y: py };
      const dx = px - from.x, dy = py - from.y, step = Math.hypot(dx, dy);
      const ux = step ? dx / step : 0, uy = step ? dy / step : 0, speed = step / F;
      const movingNow = step >= MIN_MOVE;
      if (movingNow && loose > 0) {
        const mid = { x: (from.x + px) / 2, y: (from.y + py) / 2 };
        sweep.halfHeight = step / 2;
        const hit: number[] = [];
        world.intersectionsWithShape(mid, Math.atan2(dy, dx) - Math.PI / 2, sweep, (c) => {
          const b = byHandle.get(c.handle);
          if (b !== undefined) hit.push(b);
          return true;
        });
        const k = Math.min(0.055 * Math.min(speed, IMPULSE_SPEED_CAP), IMPULSE_CAP);
        for (const b of hit) {
          const body = bodies[b];
          if (!body) continue;
          const m = k * body.mass();
          body.applyImpulse({ x: ux * m, y: uy * m }, true);
          const t = body.translation();
          const cross = ux * (t.y - mid.y) - uy * (t.x - mid.x);
          body.applyTorqueImpulse((cross === 0 ? spinDir[b] : Math.sign(cross)) * m * 0.08, true);
        }
      }
      let freed = 0;
      if (movingNow)
        for (let b = 0; b < n && freed < 3; b++) {
          if (state[b] !== 0) continue;
          const cx = homeX[b] / BLOCK + 0.5 - px, cy = homeY[b] / BLOCK + 0.5 - py;
          if (cx * cx + cy * cy <= DETACH_R * DETACH_R) { detach(b, px, py, ux, uy, speed); freed++; }
        }
      last = { x: px, y: py };
      busy = freed > 0 || movingNow;
    } else last = null;

    if (!pointer.active && !holding && loose > 0) for (let b = 0; b < n; b++) if (state[b] === 1) release(b);

    if (loose > 0) {
      const vel = new Float32Array(n * 2);
      for (let b = 0; b < n; b++) if (bodies[b]) { const v = bodies[b]!.linvel(); vel[b * 2] = v.x; vel[b * 2 + 1] = v.y; }
      world.step(events);
      events.drainCollisionEvents((h1, h2, started) => {
        if (!started) return;
        const a = byHandle.get(h1), c = byHandle.get(h2);
        if (a === undefined || c === undefined) return;
        if (Math.hypot(vel[a * 2] - vel[c * 2], vel[a * 2 + 1] - vel[c * 2 + 1]) >= FLASH_SPEED) flash[a] = flash[c] = 1;
      });
    }
    moving = 0;
    for (let b = 0; b < n; b++) {
      if (state[b] === 1) {
        const body = bodies[b]!;
        const t = body.translation();
        x[b] = BLOCK * t.x - 6;
        y[b] = BLOCK * t.y - 6;
        rot[b] = wrapAngle(body.rotation());
        if (!body.isSleeping()) busy = true;
        if (flash[b] > 0) { flash[b] *= FLASH_DECAY; if (flash[b] < 0.02) flash[b] = 0; else busy = true; }
        moving++;
      } else if (state[b] === 2) {
        busy = true;
        moving++;
        if (wait[b] > 0) { wait[b]--; continue; }
        if (flyHome(b)) moving--;
      }
    }
    return busy;
  };

  return {
    tick,
    draw,
    /** Nothing loose or flying: the live text can come back. */
    settled: () => moving === 0 && loose === 0,
    destroy: () => { world.free(); events.free(); },
  };
}

/** Wraps one line of the hero title. The children are the text; the effect draws over them. */
export function GlitchText({ children, className }: { children: ReactNode; className?: string }) {
  const host = useRef<HTMLSpanElement>(null);
  const text = useRef<HTMLSpanElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const el = host.current, txt = text.current, cv = canvas.current;
    if (!el || !txt || !cv) return;
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)");
    const still = window.matchMedia("(prefers-reduced-motion: reduce)");
    let effect: ReturnType<typeof createEffect> | null = null;
    let building: Promise<void> | null = null;
    let raf = 0, acc = 0, lastT = 0, holdTimer = 0, holding = false, dead = false;
    const pointer = { active: false, x: 0, y: 0 };

    const showText = (on: boolean) => {
      txt.style.color = on ? "" : "transparent";
      cv.style.visibility = on ? "hidden" : "visible";
    };
    const reset = () => {
      cancelAnimationFrame(raf);
      raf = 0;
      effect?.destroy();
      effect = null;
      building = null;
      showText(true);
    };
    const build = () =>
      (building ??= (async () => {
        const [R, field] = await Promise.all([loadRapier(), rasterise(el, txt)]);
        if (dead || !field) return;
        // exact device pixels, placed on the pixel grid: the copy lines up with the live text
        cv.width = field.W;
        cv.height = field.H;
        cv.style.left = `${field.left}px`;
        cv.style.top = `${field.top}px`;
        cv.style.width = `${field.W / field.dpr}px`;
        cv.style.height = `${field.H / field.dpr}px`;
        effect = createEffect(R, cv, field, () => getComputedStyle(txt).color);
      })().catch(() => { building = null; }));

    const loop = (t: number) => {
      if (!effect) { raf = 0; return; }
      acc += Math.min(100, t - (lastT || t));
      lastT = t;
      let busy = false;
      while (acc >= F * 1000) {
        acc -= F * 1000;
        busy = effect.tick(pointer, holding) || busy;
      }
      effect.draw();
      if (!busy && !pointer.active && effect.settled()) {
        showText(true);
        raf = 0;
        lastT = 0;
        return;
      }
      raf = requestAnimationFrame(loop);
    };
    const start = () => {
      if (!effect) return;
      showText(false);
      if (!raf) { lastT = 0; acc = 0; raf = requestAnimationFrame(loop); }
    };

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== "mouse" || !fine.matches || still.matches) return;
      const r = el.getBoundingClientRect();
      pointer.active = true;
      pointer.x = e.clientX - r.left;
      pointer.y = e.clientY - r.top;
      window.clearTimeout(holdTimer);
      holding = true;
      if (effect) start();
      else void build().then(start);
    };
    const onLeave = () => {
      pointer.active = false;
      window.clearTimeout(holdTimer);
      holdTimer = window.setTimeout(() => { holding = false; }, RELEASE_DELAY);
    };
    // A new size or zoom means a new pixel grid: drop the effect, rebuild on the next touch.
    const ro = new ResizeObserver(() => { if (effect && !raf) reset(); });
    ro.observe(el);
    // The blocks are drawn in the text's colour: a theme switch rebuilds them on the next touch.
    const mo = new MutationObserver(() => { if (effect && !raf) reset(); });
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", onLeave);
    return () => {
      dead = true;
      ro.disconnect();
      mo.disconnect();
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      window.clearTimeout(holdTimer);
      reset();
    };
  }, []);

  return (
    <span ref={host} className={`glitch ${className ?? ""}`}>
      <span ref={text} className="glitch__text">
        {children}
      </span>
      <canvas ref={canvas} className="glitch__canvas" aria-hidden />
    </span>
  );
}
