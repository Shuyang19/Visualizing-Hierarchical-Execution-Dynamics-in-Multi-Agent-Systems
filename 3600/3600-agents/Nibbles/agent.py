from collections.abc import Callable
from typing import List, Tuple
import numpy as np
from collections import deque
import importlib # 用于热加载参数
from game import board
from game.enums import Direction, MoveType, loc_after_direction

# 动态导入配置
from . import config

class PlayerAgent:

    def __init__(self, board_instance: board.Board, time_left: Callable):
        self.map_size = board_instance.game_map.MAP_SIZE
        
        # === 关键：热加载参数 ===
        # 这样训练脚本修改 config.py 后，Agent 不需要重启就能读到新数据
        importlib.reload(config)
        self.params = config.PARAMS
        # =====================

        self.even_belief = self._init_prior(0)
        self.odd_belief  = self._init_prior(1)
        self.visit = {}

    # -------------------------------
    # 1. prior (保持原版 Judy 的直觉)
    # -------------------------------
    def _init_prior(self, parity):
        grid = np.zeros((self.map_size, self.map_size))
        for x in range(self.map_size):
            for y in range(self.map_size):
                if (x + y) % 2 != parity: continue
                if x in [3, 4] and y in [3, 4]: grid[x][y] = 2.0
                elif x in [2, 3, 4, 5] and y in [2, 3, 4, 5]: grid[x][y] = 1.0
                else: grid[x][y] = 0.1  
        s = np.sum(grid)
        if s > 0: grid /= s
        return grid

    def _update_beliefs(self, board_state, sensor_data):
        for parity in [0, 1]:
            belief = self.even_belief if parity == 0 else self.odd_belief
            heard, felt = sensor_data[parity]
            for x in range(self.map_size):
                for y in range(self.map_size):
                    if belief[x][y] == 0: continue
                    p_hear, p_feel = board_state.chicken_player.prob_senses_if_trapdoor_were_at(
                        heard, felt, x, y
                    )
                    belief[x][y] *= (p_hear * p_feel)
            total = np.sum(belief)
            if total > 0: belief /= total

    def corner(self, pos):
        return pos in [(0,0),(0,7),(7,0),(7,7)]

    def play(self, board_state: board.Board, sensor_data: List[Tuple[bool, bool]], time_left: Callable):
        my = board_state.chicken_player
        my_loc = my.get_location()
        my_parity = my.even_chicken
        opp = board_state.chicken_enemy
        opp_loc = opp.get_location()
        
        valid_moves = board_state.get_valid_moves()
        self.visit[my_loc] = self.visit.get(my_loc, 0) + 1
        self._update_beliefs(board_state, sensor_data)

        best_move = None
        best_score = -1e18

        for (direction, mtype) in valid_moves:
            newpos = loc_after_direction(my_loc, direction)
            x, y = newpos
            score = 0.0
            
            # 陷阱概率
            mx, myy = my_loc
            my_belief = self.even_belief if (mx + myy) % 2 == 0 else self.odd_belief
            my_trap_prob = my_belief[mx][myy]

            # 自杀判定
            if my_trap_prob > 0.25:
                if mtype == MoveType.EGG or mtype == MoveType.TURD:
                    score -= 99999 
                else:
                    score += 2000 

            # --- 核心：参数化 ---
            
            # 1. Open Space (Flood Fill)
            if len(self.visit) < 8:
                # (这里省略了内部函数定义，保持原样即可，为了节省篇幅)
                from collections import deque
                def is_blocked_for_area(loc):
                    if not board_state.is_valid_cell(loc): return True
                    if loc == board_state.chicken_enemy.get_location(): return True
                    if loc in board_state.eggs_player or loc in board_state.eggs_enemy: return True
                    if loc in board_state.turds_player or loc in board_state.turds_enemy: return True
                    if board_state.is_cell_in_enemy_turd_zone(loc): return True
                    if loc in board_state.found_trapdoors: return True
                    return False

                def count_open_area(start):
                    if is_blocked_for_area(start): return 0
                    q = deque([start])
                    visited = set([start])
                    count = 0
                    LIMIT = 30
                    while q and count < LIMIT:
                        cx, cy = q.popleft()
                        count += 1
                        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                            nx, ny = cx + dx, cy + dy
                            nxt = (nx, ny)
                            if nxt in visited or is_blocked_for_area(nxt): continue
                            visited.add(nxt)
                            q.append(nxt)
                    return count

                open_space = count_open_area((x, y))
                score += open_space * self.params["OPEN_SPACE_WEIGHT"] # <--- 参数化

            # 2. Egg Reward
            if mtype == MoveType.EGG:
                score += self.params["CORNER_BONUS"] if self.corner(my_loc) else self.params["EGG_BONUS"] # <--- 参数化

            # 3. Parity
            if (x + y) % 2 == my_parity:
                score += self.params["PARITY_BONUS"] # <--- 参数化

            # 4. Center
            if 1 <= x <= 6 and 1 <= y <= 6:
                score += self.params["CENTER_BONUS"] # <--- 参数化

            # 5. Avoid Enemy Turd
            if board_state.is_cell_in_enemy_turd_zone(newpos):
                score -= self.params["ENEMY_TURD_PENALTY"] # <--- 参数化

            # 6. Trap
            target_belief = self.even_belief if (x + y) % 2 == 0 else self.odd_belief
            trap_prob = target_belief[x][y]
            if trap_prob > 0.20: score -= 9999
            score -= trap_prob * self.params["TRAP_PENALTY"] # <--- 参数化

            # 7. Visit Penalty
            v = self.visit.get(newpos, 0)
            score -= v * self.params["VISIT_PENALTY"] # <--- 参数化
            if v >= 3: score -= 10 
            
            # 8. Chase Enemy
            dist_to_enemy = abs(x - opp_loc[0]) + abs(y - opp_loc[1])
            if mtype != MoveType.EGG and trap_prob < 0.05:
                score += max(0, 5 - dist_to_enemy) * self.params["CHASE_WEIGHT"] # <--- 参数化
            
            # 9. Turd Logic
            if mtype == MoveType.TURD and my.has_turds_left():
                if board_state.can_lay_egg_at_loc(my_loc):
                    score -= 99999
                else:
                    if abs(opp_loc[0] - x) + abs(opp_loc[1] - y) < dist_to_enemy:
                        score += self.params["TURD_OFFENSE_BONUS"] # <--- 参数化
                    else:
                        score -= 5

                    if (x + y) % 2 == opp.even_chicken:
                        score += self.params["TURD_BLOCK_BONUS"] # <--- 参数化

                    if trap_prob > 0.1: score -= 50
                    if len(self.visit) < 4: score -= 10
                    if self.corner((x,y)): score -= 6

            if score > best_score:
                best_score = score
                best_move = (direction, mtype)

        return best_move