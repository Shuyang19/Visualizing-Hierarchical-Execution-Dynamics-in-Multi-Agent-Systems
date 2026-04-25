from collections.abc import Callable
from typing import List, Tuple
import numpy as np
from collections import deque
from game import board
from game.enums import Direction, MoveType, loc_after_direction

class PlayerAgent:

    def __init__(self, board_instance: board.Board, time_left: Callable):
        self.map_size = board_instance.game_map.MAP_SIZE
        
        # [改进点 1] 使用 Gary 的精准概率计算，替换 Judy 的硬编码
        self.even_belief = self._init_prior(0)
        self.odd_belief  = self._init_prior(1)

        self.visit = {}

    # -------------------------------
    # 1. Prior (使用 PDF 规则的数学计算)
    # -------------------------------
    def _init_prior(self, parity):
        grid = np.zeros((self.map_size, self.map_size))
        total_weight = 0
        for x in range(self.map_size):
            for y in range(self.map_size):
                if (x + y) % 2 != parity: continue
                
                # 规则: Edge(0), Inner(0), Inner(1), Center(2)
                d_edge = min(min(x, 7-x), min(y, 7-y))
                w = 0.001
                if d_edge == 2: w = 1.0
                elif d_edge >= 3: w = 2.0
                
                grid[x][y] = w
                total_weight += w
                
        if total_weight > 0: grid /= total_weight
        return grid

    # -------------------------------
    # 2. Update Beliefs (标准贝叶斯)
    # -------------------------------
    def _update_beliefs(self, board_state, sensor_data):
        for parity in [0, 1]:
            belief = self.even_belief if parity == 0 else self.odd_belief
            heard, felt = sensor_data[parity]

            # 只要我还活着踩在某格子上，那个格子绝对安全
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
    # Utility
    # -------------------------------
    def corner(self, pos):
        return pos in [(0,0),(0,7),(7,0),(7,7)]

    # [Judy 的核心引擎] Flood Fill - 找空地
    def count_open_area(self, start, board_state):
        # 简单的阻挡判断
        def is_blocked(loc):
            if not board_state.is_valid_cell(loc): return True
            if loc == board_state.chicken_enemy.get_location(): return True
            # 蛋和屎都是墙
            if loc in board_state.eggs_player or loc in board_state.eggs_enemy: return True
            if loc in board_state.turds_player or loc in board_state.turds_enemy: return True
            # 敌人的屎区绝对不去
            if board_state.is_cell_in_enemy_turd_zone(loc): return True
            if loc in board_state.found_trapdoors: return True
            return False

        if is_blocked(start): return 0
        
        q = deque([start])
        visited = {start}
        count = 0
        LIMIT = 30 # 看得不用太远，够用就行

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
    # 3. Main Logic (基于 Judy 的贪心)
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

        for (direction, mtype) in valid_moves:
            newpos = loc_after_direction(my_loc, direction)
            x, y = newpos
            score = 0.0
            
            # --- 基础风险评估 ---
            target_belief = self.even_belief if (x + y) % 2 == 0 else self.odd_belief
            trap_prob = target_belief[x][y]

            # 1. 陷阱回避 (Judy 的参数，Gary 的概率)
            if trap_prob > 0.20: 
                score -= 9999
            score -= trap_prob * 200

            # 2. 避免自杀
            if mtype in [MoveType.EGG, MoveType.TURD] and trap_prob > 0.25:
                score -= 99999

            # --- Judy 的核心移动逻辑 ---
            
            # 3. 寻找开阔地 (Flood Fill)
            # 在前中期或者感觉拥挤时启用
            if len(self.visit) < 15 or self.visit.get(my_loc, 0) > 1:
                open_space = self.count_open_area((x,y), board_state)
                score += open_space * 0.6
                if open_space < 3: score -= 500 # 死路一条

            # 4. 下蛋逻辑
            if mtype == MoveType.EGG:
                score += 3.0 if self.corner(my_loc) else 1.5
            
            # 5. 位置偏好
            if (x + y) % 2 == my_parity: score += 0.4 # 走到能下蛋的格子上
            if 1 <= x <= 6 and 1 <= y <= 6: score += 0.2 # 稍微喜欢中心一点点
            
            # 6. 避开敌人屎区
            if board_state.is_cell_in_enemy_turd_zone(newpos):
                score -= 10.0 # 加大一点惩罚

            # 7. 访问惩罚 (防止原地踏步)
            v = self.visit.get(newpos, 0)
            score -= v * 3
            if v >= 3: score -= 50

            # 8. 敌人交互 (风筝)
            dist_to_enemy = abs(x - opp_loc[0]) + abs(y - opp_loc[1])
            if mtype != MoveType.EGG and trap_prob < 0.05:
                # 保持一个暧昧的距离 (5步左右)
                score += max(0, 5 - dist_to_enemy) * 0.3

            # --- Judy 的拉屎逻辑 (封路为主) ---
            if mtype == MoveType.TURD and my.has_turds_left():
                # 绝对不在能下蛋的地方拉屎
                if board_state.can_lay_egg_at_loc(my_loc):
                    score -= 99999
                else:
                    # 只有当：比敌人更近 (封路)
                    if abs(opp_loc[0] - x) + abs(opp_loc[1] - y) < dist_to_enemy:
                        score += 3.0
                    else:
                        score -= 5.0 # 否则别浪费

                    # 封敌人的蛋位
                    if (x + y) % 2 == opp.even_chicken:
                        score += 4.0
                    
                    if trap_prob > 0.1: score -= 50
                    if len(self.visit) < 4: score -= 10
                    if self.corner((x,y)): score -= 6

            if score > best_score:
                best_score = score
                best_move = (direction, mtype)

        return best_move