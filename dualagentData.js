

const AGENT_DEFINITIONS = [
  {
    key: 'player',
    title: 'Player',
    subtitle: 'Run / Idle / Attack / Heal / Switch Weapon',
    dotClass: 'dot-player',
    accent: '#4A90E2',
    tree: {
      id: 'root_player',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_switch',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_switch', label: 'Need switch?', type: 'condition', children: [] },
            { id: 'act_switch', label: 'Switch weapon', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_heal',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_heal', label: 'Need heal?', type: 'condition', children: [] },
            { id: 'act_heal', label: 'Heal', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_attack',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_enemy', label: 'Enemy in range?', type: 'condition', children: [] },
            { id: 'act_attack', label: 'Attack', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_run',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_move', label: 'Need move?', type: 'condition', children: [] },
            { id: 'act_run', label: 'Run', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_idle',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_idle', label: 'Idle', type: 'action', children: [] }
          ]
        }
      ]
    }
  },
  {
    key: 'golem',
    title: 'Golem',
    subtitle: 'Awake / Chase / Attack / Hit / Dead',
    dotClass: 'dot-golem',
    accent: '#8B6B4A',
    tree: {
      id: 'root_golem',
      label: 'Selector',
      type: 'selector',
      children: [
        {
          id: 'seq_dead_golem',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_dead_golem', label: 'Health <= 0?', type: 'condition', children: [] },
            { id: 'act_dead_golem', label: 'Dead', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_attack_golem',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_attack_golem', label: 'Player nearby?', type: 'condition', children: [] },
            { id: 'act_attack_golem', label: 'Attack', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_chase_golem',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'cond_chase_golem', label: 'Player detected?', type: 'condition', children: [] },
            { id: 'act_chase_golem', label: 'Chase', type: 'action', children: [] }
          ]
        },
        {
          id: 'seq_awake_golem',
          label: 'Sequence',
          type: 'sequence',
          children: [
            { id: 'act_awake_golem', label: 'Awake', type: 'action', children: [] }
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

function getPlayerState(t) {
  let mode = 'idle';
  let damaged = false;
  let healing = false;
  let switchWeapon = false;

  if (t >= 0 && t <= 1) mode = 'run';

  if (t === 2) mode = 'idle';

  if (t === 3) mode = 'attack';

  if (t >= 4 && t <= 6) {
    mode = 'attack';
    damaged = true;
  }

  if (t >= 7 && t <= 11) {
    mode = 'run';
    healing = true;
  }

  if (t === 10 || t === 11) {
    switchWeapon = true;
  }

  if (t === 12 || t === 13) mode = 'attack';

  if (t >= 14 && t <= 15) mode = 'run';

  if (t === 16 || t === 17) mode = 'attack';

  return { mode, damaged, healing, switchWeapon };
}

function getGolemState(t) {
  let mode = 'idle';
  let hit = false;

  if (t >= 0 && t <= 1) mode = 'awake';

  if (t === 2) mode = 'chase';

  if (t === 3) {
    mode = 'chase';
    hit = true;
  }

  if (t >= 4 && t <= 6) mode = 'attack';

  if (t >= 7 && t <= 11) mode = 'chase';

  if (t === 12) {
    mode = 'chase';
    hit = true;
  }

  if (t === 13) {
    mode = 'attack';
    hit = true;
  }

  if (t >= 14 && t <= 15) mode = 'chase';

  if (t === 16) {
    mode = 'chase';
    hit = true;
  }

  if (t === 17) mode = 'dead';

  return { mode, hit };
}

function buildPlayerStatus(player) {
  const S = {};
  S.root_player = 'running';

  S.seq_switch = 'running';
  S.cond_switch = player.switchWeapon ? 'success' : 'failure';
  S.act_switch = player.switchWeapon ? 'running' : null;

  S.seq_heal = player.switchWeapon ? null : 'running';
  S.cond_heal = player.switchWeapon
    ? null
    : (player.healing ? 'success' : 'failure');
  S.act_heal = player.healing && !player.switchWeapon ? 'running' : null;

  S.seq_attack = (player.switchWeapon || player.healing) ? null : 'running';
  S.cond_enemy = (player.switchWeapon || player.healing)
    ? null
    : (player.mode === 'attack' ? 'success' : 'failure');
  S.act_attack = player.mode === 'attack' && !player.switchWeapon && !player.healing
    ? 'running'
    : null;

  S.seq_run = (player.switchWeapon || player.healing || player.mode === 'attack')
    ? null
    : 'running';
  S.cond_move = (player.switchWeapon || player.healing || player.mode === 'attack')
    ? null
    : (player.mode === 'run' ? 'success' : 'failure');
  S.act_run = player.mode === 'run' && !player.switchWeapon && !player.healing
    ? 'running'
    : null;

  S.seq_idle = (
    player.switchWeapon ||
    player.healing ||
    player.mode === 'attack' ||
    player.mode === 'run'
  ) ? null : 'running';
  S.act_idle = player.mode === 'idle' ? 'running' : null;

  return S;
}

function buildGolemStatus(golem) {
  const S = {};
  S.root_golem = 'running';

  S.seq_dead_golem = 'running';
  S.cond_dead_golem = golem.mode === 'dead' ? 'success' : 'failure';
  S.act_dead_golem = golem.mode === 'dead' ? 'running' : null;

  S.seq_attack_golem = golem.mode === 'dead' ? null : 'running';
  S.cond_attack_golem = golem.mode === 'dead'
    ? null
    : (golem.mode === 'attack' ? 'success' : 'failure');
  S.act_attack_golem = golem.mode === 'attack' ? 'running' : null;

  S.seq_chase_golem = (golem.mode === 'dead' || golem.mode === 'attack') ? null : 'running';
  S.cond_chase_golem = (golem.mode === 'dead' || golem.mode === 'attack')
    ? null
    : (golem.mode === 'chase' ? 'success' : 'failure');
  S.act_chase_golem = golem.mode === 'chase' ? 'running' : null;

  S.seq_awake_golem = (
    golem.mode === 'dead' ||
    golem.mode === 'attack' ||
    golem.mode === 'chase'
  ) ? null : 'running';
  S.act_awake_golem = golem.mode === 'awake' ? 'running' : null;

  return S;
}

function generateLogs(tickCount) {
  const logs = [];

  for (let t = 0; t < tickCount; t++) {
    const player = getPlayerState(t);
    const golem = getGolemState(t);

    logs.push({
      tick: t,
      env: {
        playerMode: player.mode,
        playerDamaged: player.damaged,
        playerHealing: player.healing,
        playerSwitchWeapon: player.switchWeapon,
        golemMode: golem.mode,
        golemHit: golem.hit
      },
      agentStatus: {
        player: buildPlayerStatus(player),
        golem: buildGolemStatus(golem)
      }
    });
  }

  return logs;
}

const LOGS = generateLogs(20);