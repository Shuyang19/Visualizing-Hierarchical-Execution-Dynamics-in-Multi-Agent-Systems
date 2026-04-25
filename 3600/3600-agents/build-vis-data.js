const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const args = {};

  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) {
      continue;
    }

    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
      continue;
    }

    args[key] = next;
    index += 1;
  }

  return args;
}

function usage() {
  console.error([
    'Usage:',
    '  node build-vis-data.js --match matches/Fuzzby_Gary_0.json --out generated/Fuzzby_Gary_0.vis.js [--focus-side a|b]',
    '',
    'Optional:',
    '  --focus-name <name>',
    '  --opponent-name <name>',
    '  --title <title>',
    '  --subtitle <subtitle>'
  ].join('\n'));
  process.exit(1);
}

function parseMatchName(matchPath) {
  const basename = path.basename(matchPath, '.json');
  const parts = basename.split('_');
  if (parts.length < 3) {
    return {
      sideAName: 'Agent A',
      sideBName: 'Agent B',
      matchId: basename
    };
  }

  return {
    sideAName: parts[0],
    sideBName: parts[1],
    matchId: parts.slice(2).join('_')
  };
}

function coordKey(position) {
  return position.join(',');
}

function normalizeMoveType(leftBehind) {
  if (leftBehind === 'egg') {
    return 'egg';
  }
  if (leftBehind === 'turd') {
    return 'turd';
  }
  return 'plain';
}

function manhattanDistance(a, b) {
  return Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);
}

function buildTree() {
  return {
    id: 'root_agent',
    label: 'Selector',
    type: 'selector',
    children: [
      {
        id: 'seq_turn_loop',
        label: 'Turn loop',
        type: 'sequence',
        children: [
          { id: 'act_update_beliefs', label: 'Update beliefs', type: 'action', children: [] },
          { id: 'act_score_moves', label: 'Score moves', type: 'action', children: [] },
          {
            id: 'sel_commit_move',
            label: 'Commit move',
            type: 'selector',
            children: [
              {
                id: 'seq_egg_plan',
                label: 'Egg plan',
                type: 'sequence',
                children: [
                  { id: 'cond_chose_egg', label: 'Chose egg?', type: 'condition', children: [] },
                  { id: 'act_expand', label: 'Expand territory', type: 'action', children: [] }
                ]
              },
              {
                id: 'seq_turd_plan',
                label: 'Turd plan',
                type: 'sequence',
                children: [
                  { id: 'cond_chose_turd', label: 'Chose turd?', type: 'condition', children: [] },
                  { id: 'act_block', label: 'Block enemy', type: 'action', children: [] }
                ]
              },
              {
                id: 'seq_move_plan',
                label: 'Move plan',
                type: 'sequence',
                children: [
                  { id: 'cond_chose_plain', label: 'Chose plain?', type: 'condition', children: [] },
                  { id: 'act_reposition', label: 'Reposition', type: 'action', children: [] }
                ]
              }
            ]
          },
          {
            id: 'seq_heuristics',
            label: 'Heuristics',
            type: 'sequence',
            children: [
              { id: 'cond_early_game', label: 'Early game?', type: 'condition', children: [] },
              { id: 'act_open_space', label: 'Open space', type: 'action', children: [] },
              { id: 'cond_good_parity', label: 'Good parity?', type: 'condition', children: [] },
              { id: 'cond_center_control', label: 'Center control?', type: 'condition', children: [] },
              { id: 'cond_revisit_penalty', label: 'Revisit penalty?', type: 'condition', children: [] },
              { id: 'cond_enemy_pressure', label: 'Enemy pressure?', type: 'condition', children: [] },
              { id: 'act_finalize', label: 'Finalize best move', type: 'action', children: [] }
            ]
          }
        ]
      }
    ]
  };
}

function collectTimelineRows(root) {
  const rows = [];

  function walk(node) {
    rows.push({ id: node.id, label: node.label });
    (node.children || []).forEach(walk);
  }

  walk(root);
  return rows;
}

function buildAgentDefinition(options) {
  const tree = buildTree();
  const definition = {
    key: options.key,
    title: options.title,
    subtitle: options.subtitle,
    dotClass: options.dotClass,
    accent: options.accent,
    tree
  };
  definition.timeline = collectTimelineRows(tree);
  return definition;
}

function createEmptyTick(agentKey) {
  return {
    agentStatus: {
      [agentKey]: {}
    },
    agentMeta: {
      [agentKey]: {
        active: false,
        moveType: null,
        ownPosition: null,
        opponentPosition: null,
        ownEggs: null,
        opponentEggs: null,
        enemyDistance: null,
        parityAligned: null,
        inCenter: null,
        revisitCount: null,
        earlyGame: null
      }
    }
  };
}

function getFocusArrays(focusSide) {
  if (focusSide === 'b') {
    return {
      eggsKey: 'b_eggs_laid',
      oppEggsKey: 'a_eggs_laid',
      spawnKey: 'spawn_b',
      oppSpawnKey: 'spawn_a'
    };
  }

  return {
    eggsKey: 'a_eggs_laid',
    oppEggsKey: 'b_eggs_laid',
    spawnKey: 'spawn_a',
    oppSpawnKey: 'spawn_b'
  };
}

function addStatus(statusMap, nodeId, status) {
  if (status) {
    statusMap[nodeId] = status;
  }
}

function buildLogs(history, options) {
  const logs = [];
  const focusParity = options.focusSide === 'b' ? 1 : 0;
  const keys = getFocusArrays(options.focusSide);
  const focusSpawn = history[keys.spawnKey];
  const visitedCounts = new Map();
  let focusTurnCount = 0;

  for (let turnIndex = 0; turnIndex < history.turn_count; turnIndex += 1) {
    const tick = createEmptyTick(options.key);
    const isFocusTurn = turnIndex % 2 === focusParity;

    if (!isFocusTurn) {
      logs.push(tick);
      continue;
    }

    const focusPosition = history.pos[turnIndex];
    const opponentPosition = turnIndex > 0 ? history.pos[turnIndex - 1] : history[keys.oppSpawnKey];
    const moveType = normalizeMoveType(history.left_behind[turnIndex]);
    const ownEggs = history[keys.eggsKey][turnIndex];
    const opponentEggs = history[keys.oppEggsKey][turnIndex];
    const enemyDistance = manhattanDistance(focusPosition, opponentPosition);
    const parityAligned = ((focusPosition[0] + focusPosition[1]) % 2) === ((focusSpawn[0] + focusSpawn[1]) % 2);
    const inCenter = focusPosition[0] >= 1 && focusPosition[0] <= 6 && focusPosition[1] >= 1 && focusPosition[1] <= 6;
    const earlyGame = focusTurnCount < 8;
    const visitKey = coordKey(focusPosition);
    const nextVisitCount = (visitedCounts.get(visitKey) || 0) + 1;
    const revisitPenalty = nextVisitCount > 1;
    const enemyPressure = enemyDistance <= 3 || ownEggs < opponentEggs;
    const statusMap = tick.agentStatus[options.key];

    addStatus(statusMap, 'root_agent', 'running');
    addStatus(statusMap, 'seq_turn_loop', 'running');
    addStatus(statusMap, 'act_update_beliefs', 'success');
    addStatus(statusMap, 'act_score_moves', 'success');
    addStatus(statusMap, 'sel_commit_move', 'running');

    if (moveType === 'egg') {
      addStatus(statusMap, 'seq_egg_plan', 'running');
      addStatus(statusMap, 'cond_chose_egg', 'success');
      addStatus(statusMap, 'act_expand', 'success');
    } else if (moveType === 'turd') {
      addStatus(statusMap, 'seq_turd_plan', 'running');
      addStatus(statusMap, 'cond_chose_turd', 'success');
      addStatus(statusMap, 'act_block', 'success');
    } else {
      addStatus(statusMap, 'seq_move_plan', 'running');
      addStatus(statusMap, 'cond_chose_plain', 'success');
      addStatus(statusMap, 'act_reposition', 'success');
    }

    addStatus(statusMap, 'seq_heuristics', 'running');
    addStatus(statusMap, 'cond_early_game', earlyGame ? 'success' : 'failure');
    if (earlyGame) {
      addStatus(statusMap, 'act_open_space', 'success');
    }
    addStatus(statusMap, 'cond_good_parity', parityAligned ? 'success' : 'failure');
    addStatus(statusMap, 'cond_center_control', inCenter ? 'success' : 'failure');
    addStatus(statusMap, 'cond_revisit_penalty', revisitPenalty ? 'success' : 'failure');
    addStatus(statusMap, 'cond_enemy_pressure', enemyPressure ? 'success' : 'failure');
    addStatus(statusMap, 'act_finalize', 'success');

    tick.agentMeta[options.key] = {
      active: true,
      moveType,
      ownPosition: focusPosition,
      opponentPosition,
      ownEggs,
      opponentEggs,
      enemyDistance,
      parityAligned,
      inCenter,
      revisitCount: nextVisitCount,
      earlyGame
    };

    visitedCounts.set(visitKey, nextVisitCount);
    focusTurnCount += 1;
    logs.push(tick);
  }

  return logs;
}

function buildOutputSource(payload) {
  return [
    '// Generated by 3600/3600-agents/build-vis-data.js',
    `// Source match: ${payload.matchPath}`,
    '',
    `const AGENT_DEFINITIONS = ${JSON.stringify(payload.agentDefinitions, null, 2)};`,
    '',
    `const LOGS = ${JSON.stringify(payload.logs, null, 2)};`,
    ''
  ].join('\n');
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.match || !args.out) {
    usage();
  }

  const focusSide = args['focus-side'] === 'b' ? 'b' : 'a';
  const matchPath = path.resolve(process.cwd(), args.match);
  const outputPath = path.resolve(process.cwd(), args.out);
  const matchInfo = parseMatchName(matchPath);
  const focusName = args['focus-name'] || (focusSide === 'a' ? matchInfo.sideAName : matchInfo.sideBName);
  const opponentName = args['opponent-name'] || (focusSide === 'a' ? matchInfo.sideBName : matchInfo.sideAName);
  const title = args.title || focusName;
  const subtitle = args.subtitle || `${focusName} vs ${opponentName} | match ${matchInfo.matchId}`;

  const raw = fs.readFileSync(matchPath, 'utf8');
  const history = JSON.parse(raw);
  const agentDefinitions = [
    buildAgentDefinition({
      key: focusName.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      title,
      subtitle,
      dotClass: focusSide === 'a' ? 'dot-a' : 'dot-b',
      accent: focusSide === 'a' ? '#1D9E75' : '#534AB7'
    })
  ];
  const logs = buildLogs(history, {
    key: agentDefinitions[0].key,
    focusSide
  });
  const output = buildOutputSource({
    matchPath: path.relative(process.cwd(), matchPath),
    agentDefinitions,
    logs
  });

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, output, 'utf8');

  console.log(`Wrote ${path.relative(process.cwd(), outputPath)}`);
  console.log(`Focus agent: ${focusName}`);
  console.log(`Ticks: ${logs.length}`);
}

main();