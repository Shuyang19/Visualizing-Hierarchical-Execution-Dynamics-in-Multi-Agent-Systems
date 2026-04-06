// ─────────────────────────────────────────────────────────────────────────────
// mockData.js
// Simulated multi-agent behavior tree execution logs
//
// HOW TO USE:
//   In a plain HTML file:  <script src="mockData.js"></script>
//   In a React/Node project: export the objects and import them
//
// DATA SCHEMA:
//   TREE_A / TREE_B  — static tree structure (nodes + children)
//   LOGS             — array of 20 ticks, each with status per node per agent
//
// NODE STATUS VALUES:
//   'running'  — node is currently being evaluated
//   'success'  — node completed successfully this tick
//   'failure'  — node returned failure this tick
//   null       — node was not visited this tick (pruned by parent)
// ─────────────────────────────────────────────────────────────────────────────

// ─── Behavior Tree Structures ─────────────────────────────────────────────────
//
// NODE TYPES:
//   selector  — tries children left-to-right, stops on first SUCCESS
//   sequence  — tries children left-to-right, stops on first FAILURE
//   condition — leaf: tests an environmental condition (returns success/failure)
//   action    — leaf: executes a behavior (can return running/success/failure)

const TREE_A = {
  id: 'root', label: 'Selector', type: 'selector',
  children: [
    {
      id: 'seq_attack', label: 'Sequence', type: 'sequence',
      children: [
        { id: 'cond_enemy', label: 'Enemy visible?', type: 'condition', children: [] },
        { id: 'act_attack', label: 'Attack',         type: 'action',    children: [] }
      ]
    },
    {
      id: 'seq_patrol', label: 'Sequence', type: 'sequence',
      children: [
        { id: 'act_patrol',  label: 'Patrol', type: 'action', children: [] },
        { id: 'act_idle_a',  label: 'Idle',   type: 'action', children: [] }
      ]
    }
  ]
};

const TREE_B = {
  id: 'rootB', label: 'Selector', type: 'selector',
  children: [
    {
      id: 'seq_guard', label: 'Sequence', type: 'sequence',
      children: [
        { id: 'cond_threat', label: 'Threat nearby?', type: 'condition', children: [] },
        { id: 'act_guard',   label: 'Guard',          type: 'action',    children: [] }
      ]
    },
    {
      id: 'seq_retreat', label: 'Sequence', type: 'sequence',
      children: [
        { id: 'cond_health', label: 'Low health?', type: 'condition', children: [] },
        { id: 'act_retreat', label: 'Retreat',     type: 'action',    children: [] },
        { id: 'act_idle_b',  label: 'Idle',        type: 'action',    children: [] }
      ]
    }
  ]
};

// ─── Scenario Description ─────────────────────────────────────────────────────
//
// The simulation plays out over 20 ticks:
//
//  Tick  0–4   Agent A patrols. Agent B idles (no threats, full health).
//  Tick  5–10  Agent A detects an enemy → switches to Attack branch.
//              Agent B still no threat until tick 8.
//  Tick  8–14  Agent B detects a threat → switches to Guard branch.
//              Agent A finishes attack at tick 9 (success), resumes patrol.
//  Tick 15–19  No more threat for B. Agent B health drops low → Retreat branch.
//              Agent A continues patrolling.

// ─── Simulation Function ──────────────────────────────────────────────────────
function generateLogs(tickCount) {
  const logs = [];

  for (let t = 0; t < tickCount; t++) {
    // Environmental conditions per tick
    const enemyVisible = t >= 5  && t <= 10;
    const threatNearby = t >= 8  && t <= 14;
    const lowHealth    = t >= 15;

    // ── Agent A ──────────────────────────────────────────────────────────────
    const A = {};
    A['root'] = 'running';  // root Selector always evaluates

    if (enemyVisible) {
      // Attack branch succeeds → patrol branch not evaluated
      A['seq_attack']  = 'running';
      A['cond_enemy']  = 'success';
      A['act_attack']  = t < 9 ? 'running' : 'success';  // multi-tick action
      A['seq_patrol']  = null;
      A['act_patrol']  = null;
      A['act_idle_a']  = null;
    } else {
      // Attack branch fails at condition → fall through to patrol
      A['seq_attack']  = 'running';
      A['cond_enemy']  = 'failure';
      A['act_attack']  = null;
      A['seq_patrol']  = 'running';
      // Patrol alternates running/success every 2 ticks
      A['act_patrol']  = t % 4 < 2 ? 'running' : 'success';
      A['act_idle_a']  = t % 4 >= 2 ? 'running' : null;
    }

    // ── Agent B ──────────────────────────────────────────────────────────────
    const B = {};
    B['rootB'] = 'running';

    if (threatNearby) {
      // Guard branch active
      B['seq_guard']   = 'running';
      B['cond_threat'] = 'success';
      B['act_guard']   = t < 12 ? 'running' : 'success';
      B['seq_retreat'] = null;
      B['cond_health'] = null;
      B['act_retreat'] = null;
      B['act_idle_b']  = null;
    } else if (lowHealth) {
      // Retreat branch active
      B['seq_guard']   = 'running';
      B['cond_threat'] = 'failure';
      B['act_guard']   = null;
      B['seq_retreat'] = 'running';
      B['cond_health'] = 'success';
      B['act_retreat'] = t < 17 ? 'running' : 'success';
      B['act_idle_b']  = null;
    } else {
      // Both branches fail conditions → idle
      B['seq_guard']   = 'running';
      B['cond_threat'] = 'failure';
      B['act_guard']   = null;
      B['seq_retreat'] = 'running';
      B['cond_health'] = 'failure';
      B['act_retreat'] = null;
      B['act_idle_b']  = 'running';
    }

    logs.push({
      tick: t,
      // Environmental snapshot for this tick (useful for debugging / extension)
      env: { enemyVisible, threatNearby, lowHealth },
      A,
      B
    });
  }

  return logs;
}

const LOGS = generateLogs(20);

// ─── Export (for use in React/Node) ──────────────────────────────────────────
// Uncomment these lines if using as an ES module (React, Vite, etc.):
//
// export { TREE_A, TREE_B, LOGS, generateLogs };
//
// When used as a plain <script> tag in HTML, TREE_A / TREE_B / LOGS
// are available as global variables automatically.
