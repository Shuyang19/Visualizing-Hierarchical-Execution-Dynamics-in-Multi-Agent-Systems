// ─────────────────────────────────────────────────────────────────────────────
// mockData.js
// Simulated multi-agent behavior tree execution logs
// ─────────────────────────────────────────────────────────────────────────────

const AGENT_DEFINITIONS = [
  {
    key: 'A',
    title: 'Agent A',
    subtitle: 'Patrol & Attack',
    dotClass: 'dot-a',
    accent: '#1D9E75',
    tree: {
      id: 'root',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_attack',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_enemy', label: 'Enemy visible?', type: 'condition', children: [] },
            { id: 'act_attack', label: 'Attack', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_patrol',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_patrol', label: 'Patrol', type: 'action', children: [] },
            { id: 'act_idle_a', label: 'Idle', type: 'action', children: [] }
          ]
        }
      ]
    }
  },
  {
    key: 'B',
    title: 'Agent B',
    subtitle: 'Guard & Retreat',
    dotClass: 'dot-b',
    accent: '#534AB7',
    tree: {
      id: 'rootB',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_guard',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_threat', label: 'Threat nearby?', type: 'condition', children: [] },
            { id: 'act_guard', label: 'Guard', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_retreat',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_health', label: 'Low health?', type: 'condition', children: [] },
            { id: 'act_retreat', label: 'Retreat', type: 'action', children: [] },
            { id: 'act_idle_b', label: 'Idle', type: 'action', children: [] }
          ]
        }
      ]
    }
  },
  {
    key: 'C',
    title: 'Agent C',
    subtitle: 'Scan & Support',
    dotClass: 'dot-c',
    accent: '#C05D12',
    tree: {
      id: 'rootC',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_assist',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_ally', label: 'Ally under fire?', type: 'condition', children: [] },
            { id: 'act_assist', label: 'Assist ally', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_scan',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_scan', label: 'Scan area', type: 'action', children: [] },
            { id: 'cond_signal', label: 'Signal found?', type: 'condition', children: [] },
            { id: 'act_report', label: 'Report', type: 'action', children: [] }
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

function generateLogs(tickCount) {
  const logs = [];

  for (let t = 0; t < tickCount; t++) {
    const enemyVisible = t >= 5 && t <= 10;
    const threatNearby = t >= 8 && t <= 14;
    const lowHealth = t >= 15;
    const allyUnderFire = t >= 4 && t <= 7;
    const signalFound = t >= 10 && t <= 13;

    const agentStatus = {};

    const A = {};
    A.root = 'running';
    if (enemyVisible) {
      A.seq_attack = 'running';
      A.cond_enemy = 'success';
      A.act_attack = t < 9 ? 'running' : 'success';
      A.seq_patrol = null;
      A.act_patrol = null;
      A.act_idle_a = null;
    } else {
      A.seq_attack = 'running';
      A.cond_enemy = 'failure';
      A.act_attack = null;
      A.seq_patrol = 'running';
      A.act_patrol = t % 4 < 2 ? 'running' : 'success';
      A.act_idle_a = t % 4 >= 2 ? 'running' : null;
    }
    agentStatus.A = A;

    const B = {};
    B.rootB = 'running';
    if (threatNearby) {
      B.seq_guard = 'running';
      B.cond_threat = 'success';
      B.act_guard = t < 12 ? 'running' : 'success';
      B.seq_retreat = null;
      B.cond_health = null;
      B.act_retreat = null;
      B.act_idle_b = null;
    } else if (lowHealth) {
      B.seq_guard = 'running';
      B.cond_threat = 'failure';
      B.act_guard = null;
      B.seq_retreat = 'running';
      B.cond_health = 'success';
      B.act_retreat = t < 17 ? 'running' : 'success';
      B.act_idle_b = null;
    } else {
      B.seq_guard = 'running';
      B.cond_threat = 'failure';
      B.act_guard = null;
      B.seq_retreat = 'running';
      B.cond_health = 'failure';
      B.act_retreat = null;
      B.act_idle_b = 'running';
    }
    agentStatus.B = B;

    const C = {};
    C.rootC = 'running';
    if (allyUnderFire) {
      C.seq_assist = 'running';
      C.cond_ally = 'success';
      C.act_assist = t < 7 ? 'running' : 'success';
      C.seq_scan = null;
      C.act_scan = null;
      C.cond_signal = null;
      C.act_report = null;
    } else {
      C.seq_assist = 'running';
      C.cond_ally = 'failure';
      C.act_assist = null;
      C.seq_scan = 'running';
      C.act_scan = t < 10 ? 'running' : 'success';
      C.cond_signal = t < 10 ? null : (signalFound ? 'success' : 'failure');
      C.act_report = signalFound ? (t < 13 ? 'running' : 'success') : null;
    }
    agentStatus.C = C;

    logs.push({
      tick: t,
      env: { enemyVisible, threatNearby, lowHealth, allyUnderFire, signalFound },
      agentStatus
    });
  }

  return logs;
}

const LOGS = generateLogs(20);
