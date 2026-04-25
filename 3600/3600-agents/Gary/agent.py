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

        # Prior (Gary 的核心优势: 数学概率)
        self.even_belief = self._init_prior(0)
        self.odd_belief  = self._init_prior(1)

        self.visit = {}

    # -------------------------------
    # 1. Prior Initialization 
    # -------------------------------
    def _init_prior(self, parity):
        grid = np.zeros((self.map_size, self.map_size))
        total_weight = 0
        
        for x in range(self.map_size):
            for y in range(self.map_size):
                if (x + y) % 2 != parity: continue
                
                dist_x = min(x, 7 - x)
                dist_y = min(y, 7 - y)
                dist_edge = min(dist_x, dist_y)
                
                weight = 0.0
                if dist_edge == 0 or dist_edge == 1: weight = 0.001 
                elif dist_edge == 2: weight = 1.0
                elif dist_edge >= 3: weight = 2.0
                
                grid[x][y] = weight
                total_weight += weight

        if total_weight > 0: grid /= total_weight
        return grid

    # -------------------------------
    # 2. Update Beliefs 
    # -------------------------------
    def _update_beliefs(self, board_state, sensor_data):
        for parity in [0, 1]:
            belief = self.even_belief if parity == 0 else self.odd_belief
            heard, felt = sensor_data[parity]

            current_loc = board_state.chicken_player.get_location()
            bx, by = current_loc
            if (bx + by) % 2 == parity:
                belief[bx][by] = 0.0
            
            for x in range(self.map_size):
                for y in range(self.map_size):
                    if belief[x][y] == 0: continue
                    p_hear, p_feel = board_state.chicken_player.prob_senses_if_trapdoor_were_at(
                        heard, felt, x, y
                    )
                    belief[x][y] *= (p_hear * p_feel)

            total = np.sum(belief)
            if total > 0: belief /= total

    # -------------------------------
    # Utility Functions
    # -------------------------------
    def is_corner(self, pos):
        return pos in [(0,0),(0,7),(7,0),(7,7)]

    def get_manhattan_dist(self, p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    # -------------------------------
    # Voronoi Territory Evaluation 



    # -------------------------------
    def evaluate_territory(self, board_state, my_pos, opp_pos):
        q = deque()
        q.append((my_pos, 0, 'me'))
        q.append((opp_pos, 0, 'opp'))
        
        visited = {} 
        my_territory = 0
        
        blocked = set()
        for c in board_state.eggs_player | board_state.eggs_enemy | \
                 board_state.turds_player | board_state.turds_enemy:
            blocked.add(c)
        
        while q:
            curr, dist, owner = q.popleft()
            
            if curr in visited: continue
            visited[curr] = (dist, owner)
            
            if owner == 'me': my_territory += 1
            
            if dist > 6: continue # 限制搜索深度以提高性能

            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = curr[0]+dx, curr[1]+dy
                nxt = (nx, ny)
                if not board_state.is_valid_cell(nxt): continue
                if nxt in blocked: continue
                if nxt in visited: continue
                q.append((nxt, dist+1, owner))
                
        return my_territory

    # -------------------------------
    # Main Play Logic
    # -------------------------------
    def play(self, board_state: board.Board, sensor_data: List[Tuple[bool, bool]], time_left: Callable):
        
        my = board_state.chicken_player
        my_loc = my.get_location()
        my_parity = my.even_chicken
        opp = board_state.chicken_enemy
        opp_loc = opp.get_location()
        valid_moves = board_state.get_valid_moves()
        
        # update visit
        self.visit[my_loc] = self.visit.get(my_loc, 0) + 1
        self._update_beliefs(board_state, sensor_data)
        
        best_move = None
        best_score = -float('inf')

        dist_to_enemy = self.get_manhattan_dist(my_loc, opp_loc)
        P = self.params # 简写引用

        for (direction, mtype) in valid_moves:
            newpos = loc_after_direction(my_loc, direction)
            nx, ny = newpos
            score = 0.0
            
            # --- (Survival) ---
            target_belief = self.even_belief if (nx + ny) % 2 == 0 else self.odd_belief
            trap_prob = target_belief[nx][ny]
            
            if trap_prob > 0.15: score -= P["TRAP_PENALTY_HARD"] # <--- 参数
            score -= trap_prob * P["TRAP_PENALTY_SOFT"]          # <--- 参数

            # --- (Territory) ---
            # Voronoi: 仅在前中期计算
            if len(self.visit) < 15: 
                territory_score = self.evaluate_territory(board_state, newpos, opp_loc)
                score += territory_score * P["TERRITORY_WEIGHT"] # <--- 参数
            
            # --- (Egg Strategy) ---
            if mtype == MoveType.EGG:
                base_reward = P["EGG_BASE_REWARD"] # <--- 参数
                if self.is_corner(my_loc):
                    # 如果敌人就在旁边，去角落很危险
                    if dist_to_enemy <= 2:
                        score -= P["CORNER_DANGER_PENALTY"] # <--- 参数
                    else:
                        base_reward += P["CORNER_BONUS"] # <--- 参数
                
                score += base_reward
                
                # 连连看奖励
                neighbors = [(my_loc[0]+dx, my_loc[1]+dy) for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]]
                for n in neighbors:
                    if n in board_state.eggs_player:
                        score += P["EGG_CONNECT_BONUS"] # <--- 参数

            # --- (Efficiency) ---
            visit_count = self.visit.get(newpos, 0)
            score -= visit_count * P["VISIT_PENALTY"] # <--- 参数
            if visit_count >= 2:
                score -= P["VISIT_HEAVY_PENALTY"] # <--- 参数

            # --- (Enemy Interaction) ---
            new_dist_to_enemy = self.get_manhattan_dist(newpos, opp_loc)
            
            if mtype == MoveType.PLAIN:
                if len(board_state.eggs_enemy) > len(board_state.eggs_player):
                     # 落后要追
                     score -= new_dist_to_enemy * P["CHASE_WEIGHT"] # <--- 参数
                else:
                    # 领先要风筝 (Kiting)
                    if new_dist_to_enemy < 3:
                        score -= P["KITE_PENALTY"] # <--- 参数

            # --- (Turd Strategy: Defensive) ---
            if mtype == MoveType.TURD:
                if not my.has_turds_left():
                    score -= P["DEATH_PENALTY"] # <--- 参数
                else:
                    if (my_loc[0] + my_loc[1]) % 2 == my_parity:
                        score -= P["TURD_WASTE_PENALTY"] # <--- 参数
                    else:
                        neighbors = [(my_loc[0]+dx, my_loc[1]+dy) for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]]
                        has_my_egg_neighbor = any(n in board_state.eggs_player for n in neighbors)
                        
                        # 保护自己的蛋 (Gary 特色)
                        if has_my_egg_neighbor:
                            score += P["TURD_DEFENSE_BONUS"] # <--- 参数
                        
                        # 阻挡敌人
                        if new_dist_to_enemy > dist_to_enemy: 
                             if dist_to_enemy <= 3:
                                 score += P["TURD_BLOCK_BONUS"] # <--- 参数

            # --- (Dead End Check) ---
            free_neighbors = 0
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx2, ny2 = nx+dx, ny+dy
                if board_state.is_valid_cell((nx2, ny2)) and \
                   (nx2, ny2) not in board_state.turds_enemy and \
                   (nx2, ny2) not in board_state.turds_player:
                    free_neighbors += 1
            
            if free_neighbors <= 1:
                score -= P["DEAD_END_PENALTY"] # <--- 参数

            if score > best_score:
                best_score = score
                best_move = (direction, mtype)

        return best_move