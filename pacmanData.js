// ─────────────────────────────────────────────────────────────────────────────
// mockData.js
// Pac-Man multi-agent behavior tree execution logs (50 ticks)
// tick 0 = 1:50, tick 49 = 2:39
// ─────────────────────────────────────────────────────────────────────────────

const AGENT_DEFINITIONS = [
  {
    key: 'pacman',
    title: 'Pac-Man',
    subtitle: 'Walk / Eat / Dead',
    dotClass: 'dot-pacman',
    accent: '#F2C94C',
    tree: {
      id: 'root_pacman',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_dead',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_caught', label: 'Caught by ghost?', type: 'condition', children: [] },
            { id: 'act_dead', label: 'Dead', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_eat',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_pellet', label: 'Pellet nearby?', type: 'condition', children: [] },
            { id: 'act_eat', label: 'Eat', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_walk',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_walk', label: 'Walk', type: 'action', children: [] }
          ]
        }
      ]
    }
  },
  {
    key: 'ghost-red',
    title: 'Ghost Red',
    subtitle: 'Patrol / Chase / Eaten / Cooldown',
    dotClass: 'dot-red',
    accent: '#E24B4A',
    tree: {
      id: 'root_red',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_eaten_red',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_eaten_red', label: 'Was eaten?', type: 'condition', children: [] },
            { id: 'act_eaten_red', label: 'Eaten', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_cooldown_red',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_cooldown_red', label: 'In cooldown?', type: 'condition', children: [] },
            { id: 'act_cooldown_red', label: 'Cooldown', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_chase_red',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_target_red', label: 'Pac-Man visible?', type: 'condition', children: [] },
            { id: 'act_chase_red', label: 'Chase', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_patrol_red',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_patrol_red', label: 'Patrol', type: 'action', children: [] }
          ]
        }
      ]
    }
  },
  {
    key: 'ghost-pink',
    title: 'Ghost Pink',
    subtitle: 'Patrol / Chase / Eaten / Cooldown',
    dotClass: 'dot-pink',
    accent: '#F08BC1',
    tree: {
      id: 'root_pink',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_eaten_pink',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_eaten_pink', label: 'Was eaten?', type: 'condition', children: [] },
            { id: 'act_eaten_pink', label: 'Eaten', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_cooldown_pink',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_cooldown_pink', label: 'In cooldown?', type: 'condition', children: [] },
            { id: 'act_cooldown_pink', label: 'Cooldown', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_chase_pink',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_target_pink', label: 'Pac-Man visible?', type: 'condition', children: [] },
            { id: 'act_chase_pink', label: 'Chase', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_patrol_pink',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_patrol_pink', label: 'Patrol', type: 'action', children: [] }
          ]
        }
      ]
    }
  },
  {
    key: 'ghost-green',
    title: 'Ghost Green',
    subtitle: 'Patrol / Chase / Eaten / Cooldown',
    dotClass: 'dot-green',
    accent: '#41B66E',
    tree: {
      id: 'root_green',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_eaten_green',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_eaten_green', label: 'Was eaten?', type: 'condition', children: [] },
            { id: 'act_eaten_green', label: 'Eaten', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_cooldown_green',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_cooldown_green', label: 'In cooldown?', type: 'condition', children: [] },
            { id: 'act_cooldown_green', label: 'Cooldown', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_chase_green',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_target_green', label: 'Pac-Man visible?', type: 'condition', children: [] },
            { id: 'act_chase_green', label: 'Chase', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_patrol_green',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_patrol_green', label: 'Patrol', type: 'action', children: [] }
          ]
        }
      ]
    }
  },
  {
    key: 'ghost-blue',
    title: 'Ghost Blue',
    subtitle: 'Patrol / Chase / Eaten / Cooldown',
    dotClass: 'dot-blue',
    accent: '#4A90E2',
    tree: {
      id: 'root_blue',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_eaten_blue',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_eaten_blue', label: 'Was eaten?', type: 'condition', children: [] },
            { id: 'act_eaten_blue', label: 'Eaten', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_cooldown_blue',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_cooldown_blue', label: 'In cooldown?', type: 'condition', children: [] },
            { id: 'act_cooldown_blue', label: 'Cooldown', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_chase_blue',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_target_blue', label: 'Pac-Man visible?', type: 'condition', children: [] },
            { id: 'act_chase_blue', label: 'Chase', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_patrol_blue',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_patrol_blue', label: 'Patrol', type: 'action', children: [] }
          ]
        }
      ]
    }
  }
];

function collectTimelineRows(root) {
  const rows = [];
  (function walk(node) {
    rows.push({ id: node.id, label: node.label });
    (node.children || []).forEach(walk);
  })(root);
  return rows;
}

AGENT_DEFINITIONS.forEach(agent => {
  agent.timeline = collectTimelineRows(agent.tree);
});

function inRanges(t, ranges) {
  return ranges.some(([start, end]) => t >= start && t <= end);
}

// tick 0 = 1:50
// tick 5 = 1:55
// tick 11 = 2:01
// tick 15 = 2:05
function getPacmanMode(t) {
  if (t === 5 || t === 11) return 'dead';

  const eatRanges = [
    [15, 16], // 2:05–2:06
    [19, 20], // 2:09–2:10
    [22, 23], // 2:12–2:13
    [27, 28], // 2:17–2:18
    [35, 36], // 2:25–2:26
    [38, 39], // 2:28–2:29
    [44, 48]  // 2:34–2:38
  ];

  if (inRanges(t, eatRanges)) return 'eat';
  return 'walk';
}

function getGhostMode(color, t) {
  // default
  let mode = 'patrol';

  // red
  if (color === 'red') {
    if (t === 2) mode = 'chase';            // 1:52
    if (t === 4) mode = 'chase';            // 1:54
    if (t === 5) mode = 'chase';            // 1:55
    if (t === 8 || t === 9) mode = 'chase'; // 1:58–1:59
  }

  // pink
  if (color === 'pink') {
    if (t === 8 || t === 9 || t === 10) mode = 'chase'; // 1:58–2:00
    if (t === 11) mode = 'eaten';                       // 2:01
    if (t >= 12 && t <= 22) mode = 'cooldown';         // 2:02–2:12
    if (t >= 29 && t <= 31) mode = 'chase';            // 2:19–2:21
  }

  // green
  if (color === 'green') {
    if (t === 2) mode = 'chase';             // 1:52
    if (t === 4) mode = 'chase';             // 1:54
    if (t === 5) mode = 'eaten';             // 1:55
    if (t >= 15 && t <= 20) mode = 'cooldown'; // 2:05–2:10
    if (t >= 29 && t <= 31) mode = 'chase';  // 2:19–2:21
    if (t === 32 || t === 33) mode = 'chase'; // 2:22–2:23
  }

  // blue
  if (color === 'blue') {
    if (t === 4 || t === 5) mode = 'chase'; // 1:54–1:55
  }

  return mode;
}

function buildPacmanStatus(mode) {
  const S = {};
  S.root_pacman = 'running';

  if (mode === 'dead') {
    S.seq_dead = 'running';
    S.cond_caught = 'success';
    S.act_dead = 'running';

    S.seq_eat = null;
    S.cond_pellet = null;
    S.act_eat = null;

    S.seq_walk = null;
    S.act_walk = null;
  } else if (mode === 'eat') {
    S.seq_dead = 'running';
    S.cond_caught = 'failure';
    S.act_dead = null;

    S.seq_eat = 'running';
    S.cond_pellet = 'success';
    S.act_eat = 'running';

    S.seq_walk = null;
    S.act_walk = null;
  } else {
    S.seq_dead = 'running';
    S.cond_caught = 'failure';
    S.act_dead = null;

    S.seq_eat = 'running';
    S.cond_pellet = 'failure';
    S.act_eat = null;

    S.seq_walk = 'running';
    S.act_walk = 'running';
  }

  return S;
}

function buildGhostStatus(color, mode) {
  const prefix = color;
  const rootId = `root_${prefix}`;

  const S = {};
  S[rootId] = 'running';

  // eaten
  S[`seq_eaten_${prefix}`] = 'running';
  S[`cond_eaten_${prefix}`] = mode === 'eaten' ? 'success' : 'failure';
  S[`act_eaten_${prefix}`] = mode === 'eaten' ? 'running' : null;

  // cooldown
  S[`seq_cooldown_${prefix}`] = mode === 'eaten' ? null : 'running';
  S[`cond_cooldown_${prefix}`] = mode === 'eaten'
    ? null
    : (mode === 'cooldown' ? 'success' : 'failure');
  S[`act_cooldown_${prefix}`] = mode === 'cooldown' ? 'running' : null;

  // chase
  S[`seq_chase_${prefix}`] = (mode === 'eaten' || mode === 'cooldown') ? null : 'running';
  S[`cond_target_${prefix}`] = (mode === 'eaten' || mode === 'cooldown')
    ? null
    : (mode === 'chase' ? 'success' : 'failure');
  S[`act_chase_${prefix}`] = mode === 'chase' ? 'running' : null;

  // patrol
  S[`seq_patrol_${prefix}`] =
    (mode === 'eaten' || mode === 'cooldown' || mode === 'chase') ? null : 'running';
  S[`act_patrol_${prefix}`] = mode === 'patrol' ? 'running' : null;

  return S;
}

function generateLogs(tickCount) {
  const logs = [];

  for (let t = 0; t < tickCount; t++) {
    const pacmanMode = getPacmanMode(t);

    const redMode = getGhostMode('red', t);
    const pinkMode = getGhostMode('pink', t);
    const greenMode = getGhostMode('green', t);
    const blueMode = getGhostMode('blue', t);

    logs.push({
      tick: t,
      env: {
        pacmanMode,
        redMode,
        pinkMode,
        greenMode,
        blueMode
      },
      agentStatus: {
        'pacman': buildPacmanStatus(pacmanMode),
        'ghost-red': buildGhostStatus('red', redMode),
        'ghost-pink': buildGhostStatus('pink', pinkMode),
        'ghost-green': buildGhostStatus('green', greenMode),
        'ghost-blue': buildGhostStatus('blue', blueMode)
      }
    });
  }

  return logs;
}

const LOGS = generateLogs(50);