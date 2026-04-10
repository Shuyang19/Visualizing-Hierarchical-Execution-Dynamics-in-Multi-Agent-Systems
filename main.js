const TICK_COUNT = LOGS.length;
const DARK = matchMedia('(prefers-color-scheme: dark)').matches;

let currentTick = 0;
let playing = true;

const AGENTS = AGENT_DEFINITIONS.map(agent => ({
  ...agent,
  header: agent.accent,
  rows: agent.timeline.map(row => row.id),
  labels: agent.timeline.map(row => row.label)
}));

let selectedAgents = new Set(AGENTS.map(agent => agent.key));

const NODE_COLORS = {
  light: {
    selector: { fill: '#E1F5EE', stroke: '#0F6E56', text: '#085041' },
    sequence: { fill: '#EEEDFE', stroke: '#534AB7', text: '#3C3489' },
    condition: { fill: '#E6F1FB', stroke: '#185FA5', text: '#0C447C' },
    action: { fill: '#FAEEDA', stroke: '#BA7517', text: '#633806' }
  },
  dark: {
    selector: { fill: '#04342C', stroke: '#5DCAA5', text: '#9FE1CB' },
    sequence: { fill: '#26215C', stroke: '#AFA9EC', text: '#CECBF6' },
    condition: { fill: '#042C53', stroke: '#378ADD', text: '#B5D4F4' },
    action: { fill: '#412402', stroke: '#EF9F27', text: '#FAC775' }
  }
};

const STATUS_RING = {
  running: { stroke: '#1D9E75', dash: '4 2', fill: 'rgba(29,158,117,0.12)' },
  success: { stroke: '#1D9E75', dash: 'none', fill: 'rgba(29,158,117,0.25)' },
  failure: { stroke: '#E24B4A', dash: 'none', fill: 'rgba(226,75,74,0.25)' }
};

const TREE_LAYOUT = {
  levelGap: 68,
  siblingGap: 14,
  sidePad: 18,
  topPad: 18,
  bottomPad: 24,
  charWidth: 4.9
};

function getCol(type) {
  return (DARK ? NODE_COLORS.dark : NODE_COLORS.light)[type];
}

function getNodeSize(node) {
  const minW = node.type === 'condition' ? 70 : 58;
  const labelW = Math.ceil(node.label.length * TREE_LAYOUT.charWidth) + 20;
  return {
    width: Math.max(minW, labelW),
    height: 22,
    radius: node.type === 'condition' ? 11 : 5
  };
}

function measureTree(node) {
  const size = getNodeSize(node);
  node._boxW = size.width;
  node._boxH = size.height;
  node._rx = size.radius;

  if (!node.children || !node.children.length) {
    node._subtreeW = size.width + TREE_LAYOUT.sidePad;
    return node._subtreeW;
  }

  const childWidths = node.children.map(measureTree);
  const childrenSpan = childWidths.reduce((sum, width) => sum + width, 0)
    + TREE_LAYOUT.siblingGap * (node.children.length - 1);

  node._subtreeW = Math.max(size.width + TREE_LAYOUT.sidePad, childrenSpan);
  return node._subtreeW;
}

function positionTree(node, left, y) {
  node._x = left + node._subtreeW / 2;
  node._y = y;

  if (!node.children || !node.children.length) return;

  const childrenSpan = node.children.reduce((sum, child) => sum + child._subtreeW, 0)
    + TREE_LAYOUT.siblingGap * (node.children.length - 1);
  let cursor = node._x - childrenSpan / 2;

  node.children.forEach(child => {
    positionTree(child, cursor, y + TREE_LAYOUT.levelGap);
    cursor += child._subtreeW + TREE_LAYOUT.siblingGap;
  });
}

function prepareTreeLayout(root) {
  measureTree(root);
  positionTree(root, 0, TREE_LAYOUT.topPad + root._boxH / 2);
}

function allNodes(root) {
  return [root, ...(root.children || []).flatMap(allNodes)];
}

AGENTS.forEach(agent => prepareTreeLayout(agent.tree));

function buildAgentSelector() {
  const selector = document.getElementById('agentSelector');
  selector.innerHTML = '';

  AGENTS.forEach(agent => {
    const option = document.createElement('label');
    option.className = 'selector-option';
    option.innerHTML = `
      <input type="checkbox" value="${agent.key}" ${selectedAgents.has(agent.key) ? 'checked' : ''}>
      <span class="agent-dot ${agent.dotClass}"></span>
      <span>${agent.title}</span>
    `;
    const input = option.querySelector('input');
    input.addEventListener('change', () => {
      if (input.checked) {
        selectedAgents.add(agent.key);
      } else if (selectedAgents.size > 1) {
        selectedAgents.delete(agent.key);
      } else {
        input.checked = true;
      }
      render();
    });
    selector.appendChild(option);
  });
}

function buildLegend() {
  const legend = document.getElementById('legend');
  legend.innerHTML = '';

  AGENTS.filter(agent => selectedAgents.has(agent.key)).forEach(agent => {
    const item = document.createElement('div');
    item.className = 'legend-item';
    item.innerHTML = `<div class="legend-swatch" style="background:${agent.accent};opacity:.85"></div>${agent.title} active`;
    legend.appendChild(item);
  });

  ['Failure', 'Idle / not active', 'Current tick'].forEach(label => {
    const item = document.createElement('div');
    item.className = 'legend-item';
    if (label === 'Failure') item.innerHTML = '<div class="legend-swatch" style="background:#E24B4A;opacity:.85"></div>Failure';
    if (label === 'Idle / not active') item.innerHTML = '<div class="legend-swatch" style="background:#888780"></div>Idle / not active';
    if (label === 'Current tick') item.innerHTML = '<div class="legend-dash"></div>Current tick';
    legend.appendChild(item);
  });
}

function buildAgentRows() {
  const rows = document.getElementById('agentRows');
  rows.innerHTML = '';

  AGENTS.filter(agent => selectedAgents.has(agent.key)).forEach(agent => {
    const row = document.createElement('div');
    row.className = 'agent-row';
    row.innerHTML = `
      <div class="tree-card">
        <div class="tree-title">
          <span class="agent-dot ${agent.dotClass}"></span>${agent.title} - ${agent.subtitle}
        </div>
        <svg id="tree-${agent.key}" preserveAspectRatio="xMidYMid meet"></svg>
      </div>
      <div class="timeline-agent-card">
        <div class="tree-title">
          <span class="agent-dot ${agent.dotClass}"></span>${agent.title} timeline
        </div>
        <svg id="timeline-${agent.key}" preserveAspectRatio="xMidYMid meet"></svg>
      </div>
    `;
    rows.appendChild(row);
  });
}

function drawTree(svgEl, root, statusMap) {
  svgEl.innerHTML = '';
  const ns = 'http://www.w3.org/2000/svg';
  const nodes = allNodes(root);

  nodes.forEach(node => {
    (node.children || []).forEach(child => {
      const line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', node._x);
      line.setAttribute('y1', node._y + node._boxH / 2);
      line.setAttribute('x2', child._x);
      line.setAttribute('y2', child._y - child._boxH / 2);
      line.setAttribute('stroke', DARK ? '#444441' : '#c8c6bc');
      line.setAttribute('stroke-width', '1');
      svgEl.appendChild(line);
    });
  });

  nodes.forEach(node => {
    const status = statusMap ? statusMap[node.id] : null;
    const col = getCol(node.type);
    const g = document.createElementNS(ns, 'g');

    if (status) {
      const ring = STATUS_RING[status];
      const outline = document.createElementNS(ns, 'rect');
      outline.setAttribute('x', node._x - node._boxW / 2 - 4);
      outline.setAttribute('y', node._y - node._boxH / 2 - 4);
      outline.setAttribute('width', node._boxW + 8);
      outline.setAttribute('height', node._boxH + 8);
      outline.setAttribute('rx', node._rx + 4);
      outline.setAttribute('fill', ring.fill);
      outline.setAttribute('stroke', ring.stroke);
      outline.setAttribute('stroke-width', '1.5');
      if (ring.dash !== 'none') outline.setAttribute('stroke-dasharray', ring.dash);
      g.appendChild(outline);
    }

    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('x', node._x - node._boxW / 2);
    rect.setAttribute('y', node._y - node._boxH / 2);
    rect.setAttribute('width', node._boxW);
    rect.setAttribute('height', node._boxH);
    rect.setAttribute('rx', node._rx);
    rect.setAttribute('fill', col.fill);
    rect.setAttribute('stroke', col.stroke);
    rect.setAttribute('stroke-width', '0.75');
    g.appendChild(rect);

    if (status === 'success' || status === 'failure') {
      const icon = document.createElementNS(ns, 'text');
      icon.setAttribute('x', node._x + node._boxW / 2 - 7);
      icon.setAttribute('y', node._y - node._boxH / 2 + 8);
      icon.setAttribute('font-size', '8');
      icon.setAttribute('fill', status === 'success' ? '#1D9E75' : '#E24B4A');
      icon.setAttribute('text-anchor', 'middle');
      icon.textContent = status === 'success' ? '✓' : '✗';
      g.appendChild(icon);
    }

    const txt = document.createElementNS(ns, 'text');
    txt.setAttribute('x', node._x);
    txt.setAttribute('y', node._y);
    txt.setAttribute('text-anchor', 'middle');
    txt.setAttribute('dominant-baseline', 'central');
    txt.setAttribute('font-size', '8');
    txt.setAttribute('font-weight', '500');
    txt.setAttribute('fill', col.text);
    txt.textContent = node.label;
    g.appendChild(txt);

    const badge = document.createElementNS(ns, 'text');
    badge.setAttribute('x', node._x);
    badge.setAttribute('y', node._y + node._boxH / 2 + 9);
    badge.setAttribute('text-anchor', 'middle');
    badge.setAttribute('font-size', '7');
    badge.setAttribute('fill', DARK ? '#888780' : '#b4b2a9');
    badge.textContent = node.type;
    g.appendChild(badge);

    svgEl.appendChild(g);
  });

  const minX = Math.min(...nodes.map(node => node._x - node._boxW / 2 - 8));
  const maxX = Math.max(...nodes.map(node => node._x + node._boxW / 2 + 8));
  const minY = Math.min(...nodes.map(node => node._y - node._boxH / 2 - 8));
  const maxY = Math.max(...nodes.map(node => node._y + node._boxH / 2 + 18));
  const viewW = Math.ceil(maxX - minX + TREE_LAYOUT.sidePad * 2);
  const viewH = Math.ceil(maxY - minY + TREE_LAYOUT.bottomPad);
  svgEl.setAttribute('viewBox', `${Math.floor(minX - TREE_LAYOUT.sidePad)} ${Math.floor(minY - 4)} ${viewW} ${viewH}`);
}

function drawTimeline(agent, svgEl, statusMap) {
  svgEl.innerHTML = '';
  const ns = 'http://www.w3.org/2000/svg';
  const PAD_L = 84;
  const PAD_R = 12;
  const PAD_T = 20;
  const ROW_H = 18;
  const GAP = 6;
  const SVG_W = 680;
  const usableW = SVG_W - PAD_L - PAD_R;
  const cellW = usableW / TICK_COUNT;
  const totalH = PAD_T + 18 + agent.rows.length * (ROW_H + GAP);

  function addText(x, y, content, size, fill, anchor) {
    const t = document.createElementNS(ns, 'text');
    t.setAttribute('x', x);
    t.setAttribute('y', y);
    t.setAttribute('font-size', size || 9);
    t.setAttribute('fill', fill || (DARK ? '#888780' : '#5F5E5A'));
    t.setAttribute('text-anchor', anchor || 'start');
    t.textContent = content;
    svgEl.appendChild(t);
  }

  addText(PAD_L, PAD_T + 10, agent.title, 10, agent.header);

  for (let t = 0; t < TICK_COUNT; t += 2) {
    const x = PAD_L + t * cellW + cellW / 2;
    addText(x, PAD_T + 9, 't' + t, 9, null, 'middle');
  }

  agent.rows.forEach((nodeId, index) => {
    const y = PAD_T + 18 + index * (ROW_H + GAP);

    const bg = document.createElementNS(ns, 'rect');
    bg.setAttribute('x', PAD_L);
    bg.setAttribute('y', y);
    bg.setAttribute('width', usableW);
    bg.setAttribute('height', ROW_H);
    bg.setAttribute('rx', 3);
    bg.setAttribute('fill', DARK ? '#333331' : '#EEEDE8');
    svgEl.appendChild(bg);

    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', PAD_L - 6);
    label.setAttribute('y', y + ROW_H / 2);
    label.setAttribute('text-anchor', 'end');
    label.setAttribute('dominant-baseline', 'central');
    label.setAttribute('font-size', '9');
    label.setAttribute('fill', DARK ? '#888780' : '#5F5E5A');
    label.textContent = agent.labels[index];
    svgEl.appendChild(label);

    LOGS.forEach((log, ti) => {
      const status = log.agentStatus[agent.key][nodeId];
      if (!status) return;

      let fill;
      if (status === 'running') fill = agent.accent + 'bb';
      else if (status === 'success') fill = agent.accent + 'ee';
      else fill = '#E24B4Acc';

      const cell = document.createElementNS(ns, 'rect');
      cell.setAttribute('x', PAD_L + ti * cellW + 1.5);
      cell.setAttribute('y', y + 2);
      cell.setAttribute('width', cellW - 3);
      cell.setAttribute('height', ROW_H - 4);
      cell.setAttribute('rx', 2);
      cell.setAttribute('fill', fill);
      svgEl.appendChild(cell);
    });
  });

  svgEl.dataset.tickX = String(PAD_L + currentTick * cellW + cellW / 2);
  svgEl.dataset.tickTop = String(PAD_T);
  svgEl.dataset.tickBottom = String(totalH);
  svgEl.dataset.viewBoxWidth = String(SVG_W);
  svgEl.dataset.viewBoxHeight = String(totalH + 10);
  svgEl.setAttribute('viewBox', `0 0 680 ${totalH + 10}`);
}

function updateSharedTickOverlay() {
  const shell = document.querySelector('.page-shell');
  const line = document.getElementById('sharedTickLine');
  const label = document.getElementById('sharedTickLabel');
  const timelineSvgs = AGENTS
    .filter(agent => selectedAgents.has(agent.key))
    .map(agent => document.getElementById(`timeline-${agent.key}`))
    .filter(Boolean);

  if (!shell || !line || !label || !timelineSvgs.length) return;

  const firstSvg = timelineSvgs[0];
  const lastSvg = timelineSvgs[timelineSvgs.length - 1];
  const shellRect = shell.getBoundingClientRect();
  const firstRect = firstSvg.getBoundingClientRect();
  const lastRect = lastSvg.getBoundingClientRect();
  if (!firstRect.width || !lastRect.width) return;

  const tickX = Number(firstSvg.dataset.tickX);
  const tickTop = Number(firstSvg.dataset.tickTop);
  const tickBottom = Number(lastSvg.dataset.tickBottom);
  const viewBoxWidth = Number(firstSvg.dataset.viewBoxWidth);
  const firstViewBoxHeight = Number(firstSvg.dataset.viewBoxHeight);
  const lastViewBoxHeight = Number(lastSvg.dataset.viewBoxHeight);

  const x = firstRect.left - shellRect.left + (tickX / viewBoxWidth) * firstRect.width;
  const yTop = firstRect.top - shellRect.top + (tickTop / firstViewBoxHeight) * firstRect.height;
  const yBottom = lastRect.top - shellRect.top + (tickBottom / lastViewBoxHeight) * lastRect.height;

  line.style.display = 'block';
  line.style.left = `${x}px`;
  line.style.top = `${yTop}px`;
  line.style.height = `${Math.max(0, yBottom - yTop)}px`;

  label.style.display = 'block';
  label.style.left = `${x + 8}px`;
  label.style.top = `${Math.max(0, yTop - 18)}px`;
  label.textContent = `tick ${currentTick}`;
}

function render() {
  buildLegend();
  buildAgentRows();

  const log = LOGS[currentTick];
  AGENTS.filter(agent => selectedAgents.has(agent.key)).forEach(agent => {
    drawTree(document.getElementById(`tree-${agent.key}`), agent.tree, log.agentStatus[agent.key]);
    drawTimeline(agent, document.getElementById(`timeline-${agent.key}`), log.agentStatus[agent.key]);
  });

  document.getElementById('tickSlider').value = currentTick;
  document.getElementById('tickDisplay').textContent = 'tick ' + currentTick;
  requestAnimationFrame(updateSharedTickOverlay);
}

function onSlider(val) {
  currentTick = parseInt(val, 10);
  render();
}

function togglePlay() {
  playing = !playing;
  document.getElementById('playBtn').textContent = playing ? '⏸ Pause' : '▶ Play';
}

setInterval(() => {
  if (!playing) return;
  currentTick = (currentTick + 1) % TICK_COUNT;
  render();
}, 800);

addEventListener('resize', () => {
  requestAnimationFrame(updateSharedTickOverlay);
});

buildAgentSelector();
render();
