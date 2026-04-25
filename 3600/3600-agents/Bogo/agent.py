from collections.abc import Callable
from typing import List, Tuple
import numpy as np
from collections import deque
from game import board
from game.enums import Direction, MoveType, loc_after_direction

class PlayerAgent:

    def __init__(self, board_instance: board.Board, time_left: Callable):
        self.map_size = board_instance.game_map.MAP_SIZE
        
        # [Gary 的大脑] 陷阱概率
        self.even_belief = self._init_prior(0)
        self.odd_belief  = self._init_prior(1)

        # [记忆] 记录访问
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

    # [新功能] 获取敌人下一步可能走到的所有格子
    def _get_enemy_potential_moves(self, board_state):
        opp_loc = board_state.chicken_enemy.get_location()
        potential = set()
        
        # 简单检查敌人周围 4 格
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
            nx, ny = opp_loc[0]+dx, opp_loc[1]+dy
            
            # 越界检查
            if not (0 <= nx < self.map_size and 0 <= ny < self.map_size): continue
            
            # 简单的障碍检查 (不一定非要非常精准，只需要知道他“大概”能去哪)
            if (nx, ny) in board_state.eggs_player or \
               (nx, ny) in board_state.eggs_enemy or \
               (nx, ny) in board_state.turds_player or \
               (nx, ny) in board_state.turds_enemy:
                continue
                
            potential.add((nx, ny))
            
        return potential

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

    # -------------------------------
    # 3. 核心决策逻辑 (加入敌人感知)
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
        
        # [新] 预判敌人能去哪
        enemy_reach = self._get_enemy_potential_moves(board_state)
        # 获取当前蛋数对比
        my_score = len(board_state.eggs_player)
        opp_score = len(board_state.eggs_enemy)

        best_move = None
        best_score = -1e18
        
        dist_to_enemy = self.get_manhattan_dist(my_loc, opp_loc)

        for (direction, mtype) in valid_moves:
            newpos = loc_after_direction(my_loc, direction)
            x, y = newpos
            score = 0.0
            
            # --- [Gary] 风险评估 ---
            target_belief = self.even_belief if (x + y) % 2 == 0 else self.odd_belief
            trap_prob = target_belief[x][y]

            # 陷阱回避
            if trap_prob > 0.15: score -= 9999
            score -= trap_prob * 300

            # 避免自杀
            curr_trap_prob = self.even_belief[my_loc[0]][my_loc[1]] if (my_loc[0]+my_loc[1])%2==0 else self.odd_belief[my_loc[0]][my_loc[1]]
            if mtype in [MoveType.EGG, MoveType.TURD] and curr_trap_prob > 0.20:
                score -= 5000

            # --- [Judy] 移动逻辑 (Flood Fill) ---
            open_space = 10 
            if len(self.visit) < 20 or self.visit.get(my_loc, 0) > 1:
                open_space = self.count_open_area((x,y), board_state)
                score += open_space * 0.8 
                if open_space < 3: score -= 1000 # 死路一条

            # --- [新功能] 敌人意图感知 (Enemy Prediction) ---
            if newpos in enemy_reach:
                # 1. 抢敌人蛋位 (Steal Spot)
                # 如果这个格子是敌人的颜色，他下一回合肯定想占。我先占了！
                if (x + y) % 2 == opp.even_chicken:
                    score += 150.0  # 极高的阻挡分
                
                # 2. 抢角落 (Contest Corner)
                if self.corner(newpos):
                    score += 80.0
                
                # 3. 动态攻守 (Dynamic Aggression)
                # 如果我分数落后，我要激进地去撞他，试图乱中取胜
                if my_score <= opp_score:
                    score += 30.0
                else:
                    # 如果我分数领先，我要稳健，避免和他贴脸发生意外
                    score -= 30.0

            # --- 常规加分 ---
            if mtype == MoveType.EGG:
                is_safe_corner = self.corner(my_loc) and open_space > 5
                score += 3.0 if is_safe_corner else 1.5
                neighbors = [(my_loc[0]+dx, my_loc[1]+dy) for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]]
                if any(n in board_state.eggs_player for n in neighbors):
                    score += 0.5
            
            # Parity 偏好
            if (x + y) % 2 == my_parity: score += 0.5 
            if board_state.is_cell_in_enemy_turd_zone(newpos): score -= 50.0 

            v = self.visit.get(newpos, 0)
            score -= v * 5
            if v >= 3: score -= 100
            
            # 敌人交互 (风筝)
            new_dist_to_enemy = self.get_manhattan_dist(newpos, opp_loc)
            if mtype != MoveType.EGG and trap_prob < 0.05:
                 score += max(0, 6 - new_dist_to_enemy) * 0.2

            # --- [折中版拉屎逻辑] ---
            if mtype == MoveType.TURD:
                if not my.has_turds_left():
                    score -= 99999
                else:
                    if (my_loc[0] + my_loc[1]) % 2 == my_parity:
                        score -= 200 
                    else:
                        turd_score = 0
                        neighbors = [(my_loc[0]+dx, my_loc[1]+dy) for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]]
                        has_my_egg_neighbor = any(n in board_state.eggs_player for n in neighbors)
                        
                        if has_my_egg_neighbor:
                            if dist_to_enemy <= 5: turd_score += 100
                            else: turd_score += 20
                        
                        if (my_loc[0] + my_loc[1]) % 2 == opp.even_chicken:
                            turd_score += 60 
                        
                        dist_opp_to_me = abs(opp_loc[0] - my_loc[0]) + abs(opp_loc[1] - my_loc[1])
                        if dist_opp_to_me < dist_to_enemy:
                            turd_score += 80

                        if trap_prob > 0.15: turd_score -= 100
                        score += turd_score

            if score > best_score:
                best_score = score
                best_move = (direction, mtype)

        return best_move