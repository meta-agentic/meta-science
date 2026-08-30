// worldviz.js — shared drawing code for the demo page and the inspector.
// One copy, loaded locally by both pages: the self-containment rule bans external
// LOADS, not local files shipped in the same image.
const NS = "http://www.w3.org/2000/svg";
const el = (n, a, text) => {
  const x = document.createElementNS(NS, n);
  for (const [k, v] of Object.entries(a)) x.setAttribute(k, v);
  if (text != null) x.textContent = text;
  return x;
};
const pre = text => {
  const p = document.createElement("pre");
  p.textContent = text;
  return p;
};

function layers(truth) {
  const edges = truth.ground_truth.edges;
  const depth = {};
  const d = n => depth[n] ??= (edges[n] || []).length
    ? 1 + Math.max(...edges[n].map(d)) : 0;
  Object.keys(edges).forEach(d);
  const cols = [];
  for (const [n, k] of Object.entries(depth)) (cols[k] ??= []).push(n);
  cols.forEach(c => c.sort());
  return {cols, depth, edges};
}

// Auto-layout: Sugiyama-style, deliberately medium-complexity. Three passes —
// longest-path layering (in layers()), barycenter ordering sweeps to reduce edge
// crossings, then y-coordinate relaxation pulling each node toward the mean of its
// neighbours with per-layer separation. Chosen over a physics simulation on purpose:
// it is deterministic (same world, same picture — the project's replayability ethos
// applies to diagrams too) and it completes synchronously in milliseconds, so the
// drawing is settled at first paint, well inside any settle budget.
function autoLayout(cols, edges, RH, PAD, H) {
  const parentsOf = edges;
  const childrenOf = {};
  for (const [c, ps] of Object.entries(edges))
    for (const p of ps) (childrenOf[p] ??= []).push(c);

  // 1 · Crossing reduction: four alternating barycenter sweeps. A node moves to the
  // average order-index of its neighbours in the adjacent layer; ties stay stable.
  const order = cols.map(c => [...c]);
  const idx = {};
  const reindex = () => order.forEach(col => col.forEach((n, i) => idx[n] = i));
  reindex();
  const bary = (n, neigh) => {
    const ns = (neigh[n] || []).filter(m => idx[m] !== undefined);
    return ns.length ? ns.reduce((s, m) => s + idx[m], 0) / ns.length : idx[n];
  };
  for (let sweep = 0; sweep < 4; sweep++) {
    const [start, end, step, neigh] = sweep % 2 === 0
      ? [1, order.length, 1, parentsOf] : [order.length - 2, -1, -1, childrenOf];
    for (let li = start; li !== end; li += step) {
      order[li].sort((a, b) => bary(a, neigh) - bary(b, neigh) || a.localeCompare(b));
      reindex();
    }
  }

  // 2 · Coordinates: start from the crossing-reduced order, then 30 relaxation
  // rounds pulling each y toward the mean of ALL neighbours, re-separating each
  // layer after every round so nodes never overlap.
  const y = {};
  order.forEach(col => {
    const free = H - PAD * 2 - col.length * RH;
    col.forEach((n, ri) => y[n] = PAD + ri * RH + free / 2 + RH / 2);
  });
  for (let round = 0; round < 30; round++) {
    for (const col of order) {
      for (const n of col) {
        const ns = [...(parentsOf[n] || []), ...(childrenOf[n] || [])];
        if (ns.length)
          y[n] += 0.4 * (ns.reduce((s, m) => s + y[m], 0) / ns.length - y[n]);
      }
      col.sort((a, b) => y[a] - y[b]);
      for (let i = 1; i < col.length; i++)
        y[col[i]] = Math.max(y[col[i]], y[col[i - 1]] + RH);
      const over = y[col[col.length - 1]] - (H - PAD - RH / 2);
      if (over > 0) for (const n of col) y[n] -= over * 0.5;
    }
  }
  return {order, y};
}

function dagDiagram(truth) {
  const {cols, depth, edges} = layers(truth);
  const hidden = new Set(truth.hidden);
  const mechs = truth.ground_truth.mechanisms;
  const exo = truth.exogenous || {};
  const mnoise = truth.noise || {};
  const CW = 170, RH = 92, PAD = 40, R = 22;
  const W = Math.max(520, cols.length * CW + PAD * 2);
  const H = Math.max(...cols.map(c => c.length)) * RH + PAD * 2 + 10;
  const {order, y} = autoLayout(cols, edges, RH, PAD, H);
  const pos = {};
  order.forEach((col, ci) => col.forEach(n => {
    pos[n] = [PAD + ci * CW + 60, y[n]];
  }));
  const svg = el("svg", {viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Causal graph of the world, hidden nodes dashed"});
  const defs = el("defs", {});
  const marker = el("marker", {id: "arr", viewBox: "0 0 10 10", refX: 9, refY: 5,
    markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse"});
  marker.append(el("path", {d: "M0,0 L10,5 L0,10 z",
    fill: getComputedStyle(document.querySelector(".viz-root")).getPropertyValue("--ink-3")}));
  defs.append(marker);
  svg.append(defs);
  // Complex groupings first, painted UNDER nodes and edges: a rounded hull around
  // the two components with the z = a + j·b label, so the pair reads as one
  // quantity with two tappable outputs without inventing a fake node for z.
  for (const [z, comps] of Object.entries(truth.ground_truth.complex_vars || {})) {
    const known = comps.filter(c => pos[c]);
    if (known.length < 2) continue;
    const xs = known.map(c => pos[c][0]), ys = known.map(c => pos[c][1]);
    const x0 = Math.min(...xs) - 34, x1 = Math.max(...xs) + 34;
    const y0 = Math.min(...ys) - 34, y1 = Math.max(...ys) + 56;
    svg.append(el("rect", {x: x0, y: y0, width: x1 - x0, height: y1 - y0, rx: 14,
      fill: "var(--concordant)", opacity: 0.08,
      stroke: "var(--concordant)", "stroke-width": 1, "stroke-dasharray": "3 4"}));
    svg.append(el("text", {x: x0 + 8, y: y0 + 14, class: "mech",
      style: "font-style:italic"}, `${z} = ${comps[0]} + j·${comps[1]}`));
  }
  for (const [child, parents] of Object.entries(edges)) {
    for (const p of parents) {
      const [x1, y1] = pos[p], [x2, y2] = pos[child];
      const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
      const ux = dx / len, uy = dy / len;
      const sx = x1 + ux * (R + 3), sy = y1 + uy * (R + 3);
      const ex = x2 - ux * (R + 9), ey = y2 - uy * (R + 9);
      const attrs = {stroke: "var(--ink-3)", "stroke-width": 1.5, fill: "none",
        "marker-end": "url(#arr)", opacity: 0.85,
        "stroke-dasharray": hidden.has(p) ? "4 4" : "none"};
      if (Math.abs(depth[child] - depth[p]) > 1) {
        const bow = (28 + 6 * Math.abs(depth[child] - depth[p]))
                    * (pos[child][1] <= H / 2 ? -1 : 1);
        const mx = (sx + ex) / 2 - uy * bow, my = (sy + ey) / 2 + ux * bow;
        svg.append(el("path", {...attrs, d: `M${sx},${sy} Q${mx},${my} ${ex},${ey}`}));
      } else {
        svg.append(el("line", {...attrs, x1: sx, y1: sy, x2: ex, y2: ey}));
      }
    }
  }
  for (const [n, [x, y]] of Object.entries(pos)) {
    const isH = hidden.has(n);
    svg.append(el("circle", {cx: x, cy: y, r: R,
      fill: isH ? "none" : "var(--concordant)",
      stroke: isH ? "var(--discordant)" : "none",
      "stroke-width": isH ? 2 : 0, "stroke-dasharray": isH ? "5 4" : "none"}));
    svg.append(el("text", {x, y: y + 4, "text-anchor": "middle",
      fill: isH ? "var(--discordant)" : "#fff", style: "font-weight:650"}, n));
    const m = mechs[n];
    const line1 = m ? m.form : (isH ? "hidden · gaussian" : "gaussian");
    let line2;
    if (m) {
      line2 = `c ${(+m.const).toPrecision(3)} · σ ${(+(mnoise[n] ?? 0)).toPrecision(2)}`;
    } else {
      const e = exo[n];
      line2 = e ? `μ ${(+e.mean).toPrecision(3)} · σ ${(+e.sd).toPrecision(2)}` : "";
    }
    svg.append(el("text", {x, y: y + 36, "text-anchor": "middle", class: "mech"}, line1));
    if (line2)
      svg.append(el("text", {x, y: y + 49, "text-anchor": "middle", class: "mech"}, line2));
  }
  return svg;
}

// The agent's diagram: the same circles, deliberately no edges — visual parity with
// the DAG makes the absence of structure legible instead of merely stated.
function surfaceDiagram(surface) {
  const vars = surface.variables;
  const PER = 6, R = 22;
  const rows = Math.ceil(vars.length / PER);
  const W = 520, RH = 66;
  const H = rows * RH + 30;
  const svg = el("svg", {viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "The agent's view: labels only, no structure"});
  vars.forEach((v, i) => {
    const perRow = Math.min(PER, vars.length - Math.floor(i / PER) * PER);
    const x = (W / (perRow + 1)) * ((i % PER) + 1);
    const y = Math.floor(i / PER) * RH + RH / 2 + 6;
    svg.append(el("circle", {cx: x, cy: y, r: R, fill: "var(--concordant)"}));
    svg.append(el("text", {x, y: y + 4, "text-anchor": "middle",
      fill: "#fff", style: "font-weight:650"}, v));
  });
  return svg;
}

// laneChart — the raw draws behind a run, one lane per variable.
//
// Encoding: x is concatenated draw index, banded by phase (observe, then each
// do() arm); y is the value on a per-lane scale shared across ALL bands of that
// lane, so a shift between bands is a real shift, not a rescale. In a do() band
// the intervened variable's dots turn orange and sit on a flat guide at the
// pinned value — the meaning of intervention, visible in the data itself.
// Per-lane min/max are printed on the right, because lanes deliberately do NOT
// share a scale with each other (an exponential child would flatten every
// other lane to a hairline).
function laneChart(sim) {
  const vars = sim.variables;
  const bands = sim.bands;
  const LANE_H = 46, GAP = 10, LAB_W = 64, VAL_W = 86, TOP = 26, DOT = 1.8;
  const bandW = Math.max(60, Math.min(120, 640 / bands.length));
  const W = LAB_W + bands.length * bandW + VAL_W;
  const H = TOP + vars.length * (LANE_H + GAP) + 8;
  const svg = el("svg", {viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Raw simulation draws, one lane per variable, banded by phase"});

  // Per-lane range across every band, so cross-band shifts are honest.
  const range = {};
  for (const v of vars) {
    let lo = Infinity, hi = -Infinity;
    for (const b of bands) for (const r of b.rows) {
      lo = Math.min(lo, r[v]); hi = Math.max(hi, r[v]);
    }
    if (hi - lo < 1e-9) { hi += 1; lo -= 1; }
    range[v] = [lo, hi];
  }

  bands.forEach((b, bi) => {
    const x0 = LAB_W + bi * bandW;
    if (bi) svg.append(el("line", {x1: x0, x2: x0, y1: TOP - 8, y2: H - 6,
      stroke: "var(--line)", "stroke-width": 1}));
    svg.append(el("text", {x: x0 + bandW / 2, y: 14, "text-anchor": "middle",
      class: "mech"}, b.label));
  });

  vars.forEach((v, vi) => {
    const yTop = TOP + vi * (LANE_H + GAP);
    const [lo, hi] = range[v];
    const py = val => yTop + LANE_H - ((val - lo) / (hi - lo)) * LANE_H;
    svg.append(el("text", {x: LAB_W - 10, y: yTop + LANE_H / 2 + 4,
      "text-anchor": "end", style: "font-weight:650"}, v));
    svg.append(el("line", {x1: LAB_W, x2: W - VAL_W, y1: yTop + LANE_H,
      y2: yTop + LANE_H, class: "tick", stroke: "var(--line)"}));
    svg.append(el("text", {x: W - VAL_W + 8, y: yTop + 9, class: "mech"},
      hi.toPrecision(3)));
    svg.append(el("text", {x: W - VAL_W + 8, y: yTop + LANE_H, class: "mech"},
      lo.toPrecision(3)));

    bands.forEach((b, bi) => {
      const x0 = LAB_W + bi * bandW;
      const pinned = b.cause === v;
      if (pinned)
        svg.append(el("line", {x1: x0 + 2, x2: x0 + bandW - 2,
          y1: py(b.value), y2: py(b.value),
          stroke: "var(--discordant)", "stroke-width": 1, opacity: 0.5,
          "stroke-dasharray": "3 3"}));
      b.rows.forEach((r, i) => {
        const x = x0 + 3 + (i / Math.max(1, b.rows.length - 1)) * (bandW - 6);
        svg.append(el("circle", {cx: x, cy: py(r[v]), r: DOT,
          fill: pinned ? "var(--discordant)" : "var(--concordant)",
          "fill-opacity": pinned ? 0.9 : 0.5}));
      });
    });
  });
  return svg;
}
