from collections.abc import Callable
from typing import List, Tuple
import numpy as np
from collections import deque
import importlib
from game import board
from game.enums import Direction, MoveType, loc_after_direction

# 引入 Nibbles 的配置
from . import config

class PlayerAgent:

    def __init__(self, board_instance: board.Board, time_left: Callable):
        self.map_size = board_instance.game_map.MAP_SIZE
        
        # 加载 Nibbles 的参数
        importlib.reload(config)
        self.params = config.PARAMS

        # [大脑] 依然使用 Gary 的概率计算
        self.even_belief = self._init_prior(0)
        self.odd_belief  = self._init_prior(1)
        self.visit = {}

    def _init_prior(self, parity):
        grid = np.zeros((self.map_size, self.map_size))
        total_weight = 0
        for x in range(self.map_size):
            for y in range(self.map_size):
                if (x + y) % 2 != parity: continue
                d_edge = min(min(x, 7-x), min(y, 7-y))
                w = 0.001
                if d_edge == 2: w = 1.0
                elif d_edge >= 3: w = 2.0
                grid[x][y] = w
                total_weight += w
        if total_weight > 0: grid /= total_weight
        return grid

    def _update_beliefs(self, board_state, sensor_data):
        for parity in [0, 1]:
            belief = self.even_belief if parity == 0 else self.odd_belief
            heard, felt = sensor_data[parity]
            curr = board_state.chicken_player.get_location()
            if (curr[0] + curr[1]) % 2 == parity:
                belief[curr[0]][curr[1]] = 0.0
            for x in range(self.map_size):
                for y in range(self.map_size):
                    if belief[x][y] == 0: continue
                    p_hear, p_feel = board_state.chicken_player.prob_senses_if_trapdoor_were_at(
                        heard, felt, x, y
                    )
                    belief[x][y] *= (p_hear * p_feel)
            s = np.sum(belief)
            if s > 0: belief /= s

    def corner(self, pos):
        return pos in [(0,0),(0,7),(7,0),(7,7)]

    # [Judy 的腿] Flood Fill
    def count_open_area(self, start, board_state):
        def is_blocked(loc):
            if not board_state.is_valid_cell(loc): return True
            if loc == board_state.chicken_enemy.get_location(): return True
            if loc in board_state.eggs_player or loc in board_state.eggs_enemy: return True
            if loc in board_state.turds_player or loc in board_state.turds_enemy: return True
            if board_state.is_cell_in_enemy_turd_zone(loc): return True
            if loc in board_state.found_trapdoors: return True
            return False
        if is_blocked(start): return 0
        q = deque([start])
        visited = {start}
        count = 0
        LIMIT = 30 
        while q and count < LIMIT:
            cx, cy = q.popleft()
            count += 1
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                n = (cx+dx, cy+dy)
                if n not in visited and not is_blocked(n):
                    visited.add(n)
                    q.append(n)
        return count

    # 3. 主逻辑 (细化版拉屎)
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
        P = self.params 

        for (direction, mtype) in valid_moves:
            newpos = loc_after_direction(my_loc, direction)
            x, y = newpos
            score = 0.0
            
            # --- 陷阱回避 ---
            target_belief = self.even_belief if (x + y) % 2 == 0 else self.odd_belief
            trap_prob = target_belief[x][y]
            
            if trap_prob > 0.20: score -= 9999
            score -= trap_prob * P['TRAP_PENALTY']

            # 避免自杀
            if mtype in [MoveType.EGG, MoveType.TURD] and trap_prob > 0.25:
                score -= 99999

            # --- 寻找空地 (Flood Fill) ---
            if len(self.visit) < 15 or self.visit.get(my_loc, 0) > 1:
                open_space = self.count_open_area((x,y), board_state)
                score += open_space * P['OPEN_SPACE_WEIGHT']

            # --- 奖励计算 ---
            if mtype == MoveType.EGG:
                score += P['CORNER_BONUS'] if self.corner(my_loc) else P['EGG_BONUS']

            if (x + y) % 2 == my_parity: score += P['PARITY_BONUS']
            if 1 <= x <= 6 and 1 <= y <= 6: score += P['CENTER_BONUS']

            if board_state.is_cell_in_enemy_turd_zone(newpos):
                score -= P['ENEMY_TURD_PENALTY']

            # 访问惩罚
            v = self.visit.get(newpos, 0)
            score -= v * P['VISIT_PENALTY']
            if v >= 3: score -= 10
            
            # 敌人交互
            dist_to_enemy = abs(x - opp_loc[0]) + abs(y - opp_loc[1])
            new_dist_to_enemy = abs(newpos[0] - opp_loc[0]) + abs(newpos[1] - opp_loc[1]) # 预计算
            
            if mtype != MoveType.EGG and trap_prob < 0.05:
                score += max(0, 5 - dist_to_enemy) * P['CHASE_WEIGHT']
            
            # --- [细化版] 拉屎逻辑 ---
            if mtype == MoveType.TURD:
                if not my.has_turds_left():
                    score -= 99999
                else:
                    # 1. 绝对原则：能下蛋别拉屎 (除非被迫)
                    if (my_loc[0] + my_loc[1]) % 2 == my_parity:
                        score -= 200 # 惩罚
                    else:
                        turd_score = 0
                        
                        # [新] 防御逻辑：保护蛋 (但要克制)
                        neighbors = [(my_loc[0]+dx, my_loc[1]+dy) for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]]
                        has_my_egg_neighbor = any(n in board_state.eggs_player for n in neighbors)
                        if has_my_egg_neighbor:
                            # 只有当敌人靠近时才值得防御 (5步以内)
                            if dist_to_enemy <= 5:
                                turd_score += 100 
                            else:
                                turd_score += 20 # 稍微鼓励一下
                        
                        # [旧] 进攻逻辑：封敌人颜色
                        if (x + y) % 2 == opp.even_chicken:
                            turd_score += P['TURD_BLOCK_BONUS'] # 从参数读取 +4.0
                        
                        # [新] 阻挡逻辑：封敌人路
                        # 如果我比敌人更靠近这个格子，且这个格子在敌人前方
                        if abs(opp_loc[0] - x) + abs(opp_loc[1] - y) < dist_to_enemy:
                             turd_score += P['TURD_OFFENSE_BONUS'] # 从参数读取 +3.0

                        # 安全修正
                        if trap_prob > 0.1: turd_score -= 50
                        if self.corner((x,y)): turd_score -= 10
                        
                        score += turd_score

            if score > best_score:
                best_score = score
                best_move = (direction, mtype)

        return best_move