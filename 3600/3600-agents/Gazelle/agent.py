from collections.abc import Callable
from typing import List, Tuple
import numpy as np
from collections import deque
import importlib 
from game import board
from game.enums import Direction, MoveType, loc_after_direction

# 引入配置文件
from . import config

class PlayerAgent:

    def __init__(self, board_instance: board.Board, time_left: Callable):
        self.map_size = board_instance.game_map.MAP_SIZE
        
        # === 热加载参数 ===
        importlib.reload(config)
        self.params = config.PARAMS
        # =================

        # [Gary 的大脑] 使用符合规则的概率计算
        self.even_belief = self._init_prior(0)
        self.odd_belief  = self._init_prior(1)

        self.visit = {}

    # -------------------------------
    # 1. 陷阱计算 (Gary)
    # -------------------------------
    def _init_prior(self, parity):
        grid = np.zeros((self.map_size, self.map_size))
        total_weight = 0
        for x in range(self.map_size):
            for y in range(self.map_size):
                if (x + y) % 2 != parity: continue
                
                # 规则: Edge=0, Inner=0, Inner=1, Center=2
                d_edge = min(min(x, 7-x), min(y, 7-y))
                w = 0.001
                if d_edge == 2: w = 1.0
                elif d_edge >= 3: w = 2.0
                
                grid[x][y] = w
                total_weight += w
                
        if total_weight > 0: grid /= total_weight
        return grid

    # -------------------------------
    # 2. 贝叶斯更新
    # -------------------------------
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

    # -------------------------------
    # 辅助函数
    # -------------------------------
    def corner(self, pos):
        return pos in [(0,0),(0,7),(7,0),(7,7)]
    
    def get_manhattan_dist(self, p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    # --- [Judy 的双腿] Flood Fill ---
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
        LIMIT = 35 

        while q and count < LIMIT:
            cx, cy = q.popleft()
            count += 1
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                n = (cx+dx, cy+dy)
                if n not in visited and not is_blocked(n):
                    visited.add(n)
                    q.append(n)
        return count

    # -------------------------------
    # 3. 核心决策逻辑 (参数化)
    # -------------------------------
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
        
        dist_to_enemy = self.get_manhattan_dist(my_loc, opp_loc)
        P = self.params # 简写引用

        for (direction, mtype) in valid_moves:
            newpos = loc_after_direction(my_loc, direction)
            x, y = newpos
            score = 0.0
            
            # --- [Gary] 风险评估 ---
            target_belief = self.even_belief if (x + y) % 2 == 0 else self.odd_belief
            trap_prob = target_belief[x][y]

            # 陷阱回避
            if trap_prob > 0.15: score -= P["TRAP_PENALTY_HARD"]
            score -= trap_prob * P["TRAP_PENALTY_SOFT"]

            # 避免自杀
            curr_trap_prob = self.even_belief[my_loc[0]][my_loc[1]] if (my_loc[0]+my_loc[1])%2==0 else self.odd_belief[my_loc[0]][my_loc[1]]
            if mtype in [MoveType.EGG, MoveType.TURD] and curr_trap_prob > 0.20:
                score -= P["SUICIDE_PENALTY"]

            # --- [Judy] 移动逻辑 (Flood Fill) ---
            open_space = 10 
            if len(self.visit) < 20 or self.visit.get(my_loc, 0) > 1:
                open_space = self.count_open_area((x,y), board_state)
                score += open_space * P["OPEN_SPACE_WEIGHT"]
                if open_space < 3: score -= P["DEAD_END_PENALTY"]

            # --- 常规加分 ---
            if mtype == MoveType.EGG:
                is_safe_corner = self.corner(my_loc) and open_space > 5
                score += P["CORNER_BONUS"] if is_safe_corner else P["EGG_BASE_REWARD"]
                
                neighbors = [(my_loc[0]+dx, my_loc[1]+dy) for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]]
                if any(n in board_state.eggs_player for n in neighbors):
                    score += P["EGG_CONNECT_BONUS"]
            
            # Parity 偏好
            if (x + y) % 2 == my_parity: score += P["PARITY_BONUS"]
            
            # 避开敌人屎区
            if board_state.is_cell_in_enemy_turd_zone(newpos): score -= P["ENEMY_TURD_PENALTY"]

            # 访问惩罚
            v = self.visit.get(newpos, 0)
            score -= v * P["VISIT_PENALTY"]
            if v >= 3: score -= P["VISIT_HEAVY_PENALTY"]
            
            # 敌人交互 (风筝)
            new_dist_to_enemy = self.get_manhattan_dist(newpos, opp_loc)
            if mtype != MoveType.EGG and trap_prob < 0.05:
                 score += max(0, 6 - new_dist_to_enemy) * P["KITE_WEIGHT"]

            # ==========================================
            # [折中版拉屎逻辑] (Hybrid Turd)
            # ==========================================
            if mtype == MoveType.TURD:
                if not my.has_turds_left():
                    score -= 99999
                else:
                    # 1. 绝对原则：如果在自己能下蛋的格子上，别拉 (除非被迫)
                    if (my_loc[0] + my_loc[1]) % 2 == my_parity:
                        score -= P["TURD_PARITY_PENALTY"]
                    else:
                        turd_score = 0
                        
                        # [折中点 1] 防御 (Gary-Lite)
                        neighbors = [(my_loc[0]+dx, my_loc[1]+dy) for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]]
                        has_my_egg_neighbor = any(n in board_state.eggs_player for n in neighbors)
                        
                        if has_my_egg_neighbor:
                            # 只有当敌人离得比较近 (5步以内) 才有必要防御
                            if dist_to_enemy <= 5:
                                turd_score += P["TURD_DEFENSE_HIGH"]
                            else:
                                turd_score += P["TURD_DEFENSE_LOW"]
                        
                        # [折中点 2] 进攻 (Nick-Lite)
                        if (my_loc[0] + my_loc[1]) % 2 == opp.even_chicken:
                            turd_score += P["TURD_OFFENSE_BONUS"]
                        
                        # [折中点 3] 阻挡
                        dist_opp_to_me = abs(opp_loc[0] - my_loc[0]) + abs(opp_loc[1] - my_loc[1])
                        if dist_opp_to_me < dist_to_enemy:
                            turd_score += P["TURD_BLOCK_BONUS"]

                        # 安全修正
                        if trap_prob > 0.15: turd_score -= P["TURD_TRAP_PENALTY"]
                        
                        score += turd_score

            if score > best_score:
                best_score = score
                best_move = (direction, mtype)

        return best_move