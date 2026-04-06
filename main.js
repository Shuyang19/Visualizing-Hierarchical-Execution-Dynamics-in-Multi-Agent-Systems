// ─────────────────────────────────────────────────────────────────────────────
// main.js
// Visualization logic for the behavior tree prototype.
// Depends on: mockData.js (must be loaded first via <script src="mockData.js">)
//
// Reads globals: TREE_A, TREE_B, LOGS
// ─────────────────────────────────────────────────────────────────────────────

const TICK_COUNT = LOGS.length;
const DARK = matchMedia('(prefers-color-scheme: dark)').matches;

let currentTick = 0;
let playing = true;

// ─── Node color palettes by type ──────────────────────────────────────────────
const NODE_COLORS = {
  light: {
    selector:  { fill: '#E1F5EE', stroke: '#0F6E56', text: '#085041' },
    sequence:  { fill: '#EEEDFE', stroke: '#534AB7', text: '#3C3489' },
    condition: { fill: '#E6F1FB', stroke: '#185FA5', text: '#0C447C' },
    action:    { fill: '#FAEEDA', stroke: '#BA7517', text: '#633806' }
  },
  dark: {
    selector:  { fill: '#04342C', stroke: '#5DCAA5', text: '#9FE1CB' },
    sequence:  { fill: '#26215C', stroke: '#AFA9EC', text: '#CECBF6' },
    condition: { fill: '#042C53', stroke: '#378ADD', text: '#B5D4F4' },
    action:    { fill: '#412402', stroke: '#EF9F27', text: '#FAC775' }
  }
};

// Visual style for each execution status
const STATUS_RING = {
  running: { stroke: '#1D9E75', dash: '4 2', fill: 'rgba(29,158,117,0.12)' },
  success: { stroke: '#1D9E75', dash: 'none', fill: 'rgba(29,158,117,0.25)' },
  failure: { stroke: '#E24B4A', dash: 'none', fill: 'rgba(226,75,74,0.25)'  }
};

function getCol(type) {
  return (DARK ? NODE_COLORS.dark : NODE_COLORS.light)[type];
}

// ─── Tree layout (recursive, computes _x / _y on each node) ──────────────────
// xSpan controls how wide the subtree is allowed to spread horizontally.
function layoutTree(node, x, y, xSpan) {
  node._x = x;
  node._y = y;
  if (!node.children || !node.children.length) return;
  const n = node.children.length;
  const step = xSpan / n;
  node.children.forEach((child, i) => {
    layoutTree(child, x - xSpan / 2 + step / 2 + i * step, y + 64, xSpan / n);
  });
}

layoutTree(TREE_A, 150, 28, 260);
layoutTree(TREE_B, 150, 28, 260);

// ─── Draw one behavior tree into its SVG element ──────────────────────────────
function drawTree(svgEl, root, statusMap) {
  svgEl.innerHTML = '';
  const ns = 'http://www.w3.org/2000/svg';

  // Flatten tree to a list of all nodes
  function allNodes(n) {
    return [n, ...(n.children || []).flatMap(allNodes)];
  }
  const nodes = allNodes(root);

  // ── Edges (drawn first so nodes sit on top) ────────────────────────────────
  nodes.forEach(n => {
    (n.children || []).forEach(child => {
      const line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', n._x);     line.setAttribute('y1', n._y + 16);
      line.setAttribute('x2', child._x); line.setAttribute('y2', child._y - 16);
      line.setAttribute('stroke', DARK ? '#444441' : '#c8c6bc');
      line.setAttribute('stroke-width', '1');
      svgEl.appendChild(line);
    });
  });

  // ── Nodes ──────────────────────────────────────────────────────────────────
  nodes.forEach(n => {
    const status = statusMap ? statusMap[n.id] : null;
    const col = getCol(n.type);
    const W  = n.type === 'condition' ? 88 : 76;
    const H  = 28;
    const rx = n.type === 'condition' ? 14 : 6;  // pills for conditions
    const g  = document.createElementNS(ns, 'g');

    // Glow / status ring (only when node has a status this tick)
    if (status) {
      const ring = STATUS_RING[status];
      const r = document.createElementNS(ns, 'rect');
      r.setAttribute('x', n._x - W / 2 - 4); r.setAttribute('y', n._y - H / 2 - 4);
      r.setAttribute('width', W + 8);         r.setAttribute('height', H + 8);
      r.setAttribute('rx', rx + 4);
      r.setAttribute('fill', ring.fill);
      r.setAttribute('stroke', ring.stroke);
      r.setAttribute('stroke-width', '1.5');
      if (ring.dash !== 'none') r.setAttribute('stroke-dasharray', ring.dash);
      g.appendChild(r);
    }

    // Node body
    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('x', n._x - W / 2); rect.setAttribute('y', n._y - H / 2);
    rect.setAttribute('width', W);         rect.setAttribute('height', H);
    rect.setAttribute('rx', rx);
    rect.setAttribute('fill', col.fill);
    rect.setAttribute('stroke', col.stroke);
    rect.setAttribute('stroke-width', '0.75');
    g.appendChild(rect);

    // Small success/failure icon in top-right corner of node
    if (status === 'success' || status === 'failure') {
      const icon = document.createElementNS(ns, 'text');
      icon.setAttribute('x', n._x + W / 2 - 7);
      icon.setAttribute('y', n._y - H / 2 + 9);
      icon.setAttribute('font-size', '9');
      icon.setAttribute('fill', status === 'success' ? '#1D9E75' : '#E24B4A');
      icon.setAttribute('text-anchor', 'middle');
      icon.textContent = status === 'success' ? '✓' : '✗';
      g.appendChild(icon);
    }

    // Node label
    const txt = document.createElementNS(ns, 'text');
    txt.setAttribute('x', n._x); txt.setAttribute('y', n._y);
    txt.setAttribute('text-anchor', 'middle');
    txt.setAttribute('dominant-baseline', 'central');
    txt.setAttribute('font-size', '10');
    txt.setAttribute('font-weight', '500');
    txt.setAttribute('fill', col.text);
    txt.textContent = n.label;
    g.appendChild(txt);

    // Type badge below node
    const badge = document.createElementNS(ns, 'text');
    badge.setAttribute('x', n._x); badge.setAttribute('y', n._y + H / 2 + 10);
    badge.setAttribute('text-anchor', 'middle');
    badge.setAttribute('font-size', '8');
    badge.setAttribute('fill', DARK ? '#888780' : '#b4b2a9');
    badge.textContent = n.type;
    g.appendChild(badge);

    svgEl.appendChild(g);
  });
}

// ─── Draw the execution timeline ──────────────────────────────────────────────
function drawTimeline() {
  const svg = document.getElementById('timeline');
  svg.innerHTML = '';
  const ns = 'http://www.w3.org/2000/svg';

  const PAD_L = 82, PAD_R = 16, PAD_T = 24;
  const ROW_H = 28, GAP = 8, SEP = 14;
  const SVG_W = 680;
  const usableW = SVG_W - PAD_L - PAD_R;
  const cellW = usableW / TICK_COUNT;

  // Which node IDs to show per agent, in display order (top → bottom)
  const rowsA   = ['root','seq_attack','cond_enemy','act_attack','seq_patrol','act_patrol','act_idle_a'];
  const labelsA = ['Selector', 'Seq:Attack', 'Enemy vis?', 'Attack', 'Seq:Patrol', 'Patrol', 'Idle A'];
  const rowsB   = ['rootB','seq_guard','cond_threat','act_guard','seq_retreat','cond_health','act_retreat'];
  const labelsB = ['Selector', 'Seq:Guard', 'Threat?', 'Guard', 'Seq:Retreat', 'Low health?', 'Retreat'];

  // Y position where Agent B section starts
  const bStartY = PAD_T + 16 + rowsA.length * (ROW_H + GAP) + SEP;

  // Helper: append a <text> element to the SVG
  function addText(x, y, content, size, fill, anchor) {
    const t = document.createElementNS(ns, 'text');
    t.setAttribute('x', x); t.setAttribute('y', y);
    t.setAttribute('font-size', size || 9);
    t.setAttribute('fill', fill || (DARK ? '#888780' : '#5F5E5A'));
    t.setAttribute('text-anchor', anchor || 'start');
    t.textContent = content;
    svg.appendChild(t);
  }

  // Section header labels
  addText(PAD_L, PAD_T + 11,     'Agent A', 10, DARK ? '#5DCAA5' : '#0F6E56');
  addText(PAD_L, bStartY + 11,   'Agent B', 10, DARK ? '#AFA9EC' : '#534AB7');

  // Tick labels along the top (every 2 ticks to avoid crowding)
  for (let t = 0; t < TICK_COUNT; t += 2) {
    const x = PAD_L + t * cellW + cellW / 2;
    addText(x, PAD_T + 10, 't' + t, 9, null, 'middle');
  }

  // Draw one agent's rows
  function drawRows(nodeIds, labels, statusKey, startY, agentHex) {
    nodeIds.forEach((nodeId, ri) => {
      const y = startY + ri * (ROW_H + GAP);

      // Row background
      const bg = document.createElementNS(ns, 'rect');
      bg.setAttribute('x', PAD_L); bg.setAttribute('y', y);
      bg.setAttribute('width', usableW); bg.setAttribute('height', ROW_H);
      bg.setAttribute('rx', 3);
      bg.setAttribute('fill', DARK ? '#333331' : '#EEEDE8');
      svg.appendChild(bg);

      // Row label (left of row)
      const lbl = document.createElementNS(ns, 'text');
      lbl.setAttribute('x', PAD_L - 5); lbl.setAttribute('y', y + ROW_H / 2);
      lbl.setAttribute('text-anchor', 'end');
      lbl.setAttribute('dominant-baseline', 'central');
      lbl.setAttribute('font-size', '9');
      lbl.setAttribute('fill', DARK ? '#888780' : '#5F5E5A');
      lbl.textContent = labels[ri];
      svg.appendChild(lbl);

      // One cell per tick
      LOGS.forEach((log, ti) => {
        const status = log[statusKey][nodeId];
        if (!status) return;  // node not visited this tick → no cell

        let fill;
        if      (status === 'running') fill = agentHex + 'bb';
        else if (status === 'success') fill = agentHex + 'ee';
        else if (status === 'failure') fill = '#E24B4Acc';

        const cell = document.createElementNS(ns, 'rect');
        cell.setAttribute('x', PAD_L + ti * cellW + 1.5);
        cell.setAttribute('y', y + 2);
        cell.setAttribute('width',  cellW - 3);
        cell.setAttribute('height', ROW_H - 4);
        cell.setAttribute('rx', 2);
        cell.setAttribute('fill', fill);
        svg.appendChild(cell);
      });
    });
  }

  drawRows(rowsA, labelsA, 'A', PAD_T + 22, '#1D9E75');
  drawRows(rowsB, labelsB, 'B', bStartY + 18, '#534AB7');

  // ── Current tick marker (vertical dashed line) ─────────────────────────────
  const lineX = PAD_L + currentTick * cellW + cellW / 2;
  const totalH = bStartY + 18 + rowsB.length * (ROW_H + GAP);

  const tickLine = document.createElementNS(ns, 'line');
  tickLine.setAttribute('x1', lineX); tickLine.setAttribute('y1', PAD_T);
  tickLine.setAttribute('x2', lineX); tickLine.setAttribute('y2', totalH);
  tickLine.setAttribute('stroke', '#EF9F27');
  tickLine.setAttribute('stroke-width', '1.5');
  tickLine.setAttribute('stroke-dasharray', '3 2');
  svg.appendChild(tickLine);

  addText(lineX + 4, PAD_T + 4, 'tick ' + currentTick, 9, '#BA7517');

  // Adjust viewBox height to fit content tightly
  svg.setAttribute('viewBox', `0 0 680 ${totalH + 10}`);
}

// ─── Main render call ─────────────────────────────────────────────────────────
function render() {
  const log = LOGS[currentTick];
  drawTree(document.getElementById('treeA'), TREE_A, log.A);
  drawTree(document.getElementById('treeB'), TREE_B, log.B);
  drawTimeline();
  document.getElementById('tickSlider').value = currentTick;
  document.getElementById('tickDisplay').textContent = 'tick ' + currentTick;
}

// ─── Controls ─────────────────────────────────────────────────────────────────
function onSlider(val) {
  currentTick = parseInt(val, 10);
  render();
}

function togglePlay() {
  playing = !playing;
  document.getElementById('playBtn').textContent = playing ? '⏸ Pause' : '▶ Play';
}

// Auto-advance every 800ms when playing
setInterval(() => {
  if (!playing) return;
  currentTick = (currentTick + 1) % TICK_COUNT;
  render();
}, 800);

// Initial render
render();
