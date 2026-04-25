// ─────────────────────────────────────────────────────────────────────────────
// sokobanData.js
// Sokoban single-agent behavior tree execution logs
// Compatible with the existing AGENT_DEFINITIONS + LOGS visualizer contract
// ─────────────────────────────────────────────────────────────────────────────

const AGENT_DEFINITIONS = [
  {
    key: 'sokoban',
    title: 'Sokoban Solver',
    subtitle: 'Scan / Setup / Push / Recover / Finish',
    dotClass: 'dot-a',
    accent: '#1D9E75',
    tree: {
      id: 'root_sokoban',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_finish',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_solved', label: 'Solved?', type: 'condition', children: [] },
            { id: 'act_finish', label: 'Finish level', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_recover',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_deadlock', label: 'Deadlock risk?', type: 'condition', children: [] },
            { id: 'act_recover', label: 'Reposition', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_push',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_push_ready', label: 'Push available?', type: 'condition', children: [] },
            { id: 'act_push', label: 'Push crate', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_setup',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_path_ready', label: 'Path to setup?', type: 'condition', children: [] },
            { id: 'act_setup', label: 'Move to setup', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_scan',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_scan', label: 'Scan room', type: 'action', children: [] }
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

const STATES = [
  {
    mode: 'scan',
    playerPos: [1, 4],
    crates: [[3, 2], [4, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 0,
    remainingCrates: 2,
    deadlockRisk: 'low',
    summary: 'Inspect room and identify crate-goal pairs.'
  },
  {
    mode: 'scan',
    playerPos: [2, 4],
    crates: [[3, 2], [4, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 0,
    remainingCrates: 2,
    deadlockRisk: 'low',
    summary: 'Confirm the easier crate can be routed along the right corridor.'
  },
  {
    mode: 'setup',
    playerPos: [2, 3],
    crates: [[3, 2], [4, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 0,
    remainingCrates: 2,
    deadlockRisk: 'low',
    summary: 'Path to the upper crate is open; move into pushing position.'
  },
  {
    mode: 'setup',
    playerPos: [2, 2],
    crates: [[3, 2], [4, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 0,
    remainingCrates: 2,
    deadlockRisk: 'low',
    summary: 'Finish alignment behind the upper crate.'
  },
  {
    mode: 'push',
    playerPos: [3, 2],
    crates: [[4, 2], [4, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 0,
    remainingCrates: 2,
    deadlockRisk: 'low',
    summary: 'Push the upper crate one tile toward its goal lane.'
  },
  {
    mode: 'push',
    playerPos: [4, 2],
    crates: [[5, 2], [4, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 1,
    remainingCrates: 1,
    deadlockRisk: 'low',
    summary: 'Complete the first goal placement.'
  },
  {
    mode: 'setup',
    playerPos: [4, 3],
    crates: [[5, 2], [4, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 1,
    remainingCrates: 1,
    deadlockRisk: 'medium',
    summary: 'Rotate around the lower crate for a clean push angle.'
  },
  {
    mode: 'push',
    playerPos: [4, 4],
    crates: [[5, 2], [5, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 1,
    remainingCrates: 1,
    deadlockRisk: 'medium',
    summary: 'Advance the lower crate into the right corridor.'
  },
  {
    mode: 'recover',
    playerPos: [5, 5],
    crates: [[5, 2], [5, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 1,
    remainingCrates: 1,
    deadlockRisk: 'high',
    summary: 'Avoid cornering the lower crate; back out and re-route.'
  },
  {
    mode: 'setup',
    playerPos: [4, 5],
    crates: [[5, 2], [5, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 1,
    remainingCrates: 1,
    deadlockRisk: 'medium',
    summary: 'Re-enter from below to preserve a legal push line.'
  },
  {
    mode: 'setup',
    playerPos: [5, 5],
    crates: [[5, 2], [5, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 1,
    remainingCrates: 1,
    deadlockRisk: 'medium',
    summary: 'Align behind the lower crate for the final corridor push.'
  },
  {
    mode: 'push',
    playerPos: [5, 4],
    crates: [[5, 2], [6, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 2,
    remainingCrates: 0,
    deadlockRisk: 'none',
    summary: 'Push the lower crate onto its goal tile.'
  },
  {
    mode: 'finish',
    playerPos: [5, 4],
    crates: [[5, 2], [6, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 2,
    remainingCrates: 0,
    deadlockRisk: 'none',
    summary: 'All crates placed; finalize level state.'
  },
  {
    mode: 'finish',
    playerPos: [5, 4],
    crates: [[5, 2], [6, 4]],
    goals: [[5, 2], [6, 4]],
    cratesSolved: 2,
    remainingCrates: 0,
    deadlockRisk: 'none',
    summary: 'Stable solved state.'
  }
];

function buildSokobanStatus(state) {
  const status = {};

  status.root_sokoban = 'running';

  status.seq_finish = 'running';
  status.cond_solved = state.mode === 'finish' ? 'success' : 'failure';
  status.act_finish = state.mode === 'finish' ? 'running' : null;

  if (state.mode === 'finish') {
    status.seq_recover = null;
    status.cond_deadlock = null;
    status.act_recover = null;
    status.seq_push = null;
    status.cond_push_ready = null;
    status.act_push = null;
    status.seq_setup = null;
    status.cond_path_ready = null;
    status.act_setup = null;
    status.seq_scan = null;
    status.act_scan = null;
    return status;
  }

  status.seq_recover = 'running';
  status.cond_deadlock = state.mode === 'recover' ? 'success' : 'failure';
  status.act_recover = state.mode === 'recover' ? 'running' : null;

  if (state.mode === 'recover') {
    status.seq_push = null;
    status.cond_push_ready = null;
    status.act_push = null;
    status.seq_setup = null;
    status.cond_path_ready = null;
    status.act_setup = null;
    status.seq_scan = null;
    status.act_scan = null;
    return status;
  }

  status.seq_push = 'running';
  status.cond_push_ready = state.mode === 'push' ? 'success' : 'failure';
  status.act_push = state.mode === 'push' ? 'running' : null;

  if (state.mode === 'push') {
    status.seq_setup = null;
    status.cond_path_ready = null;
    status.act_setup = null;
    status.seq_scan = null;
    status.act_scan = null;
    return status;
  }

  status.seq_setup = 'running';
  status.cond_path_ready = state.mode === 'setup' ? 'success' : 'failure';
  status.act_setup = state.mode === 'setup' ? 'running' : null;

  if (state.mode === 'setup') {
    status.seq_scan = null;
    status.act_scan = null;
    return status;
  }

  status.seq_scan = 'running';
  status.act_scan = 'running';
  return status;
}

const LOGS = STATES.map((state, tick) => ({
  tick,
  env: {
    mode: state.mode,
    playerPos: state.playerPos,
    crates: state.crates,
    goals: state.goals,
    cratesSolved: state.cratesSolved,
    remainingCrates: state.remainingCrates,
    deadlockRisk: state.deadlockRisk,
    summary: state.summary
  },
  agentStatus: {
    sokoban: buildSokobanStatus(state)
  }
}));