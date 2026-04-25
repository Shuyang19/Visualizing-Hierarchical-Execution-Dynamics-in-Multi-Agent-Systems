
from collections.abc import Callable
from typing import List, Tuple
import numpy as np
from game import board
from game.enums import Direction, MoveType, loc_after_direction


class PlayerAgent:

    def __init__(self, board: board.Board, time_left: Callable):
        self.map_size = board.game_map.MAP_SIZE
        
        # bayessian belief
        self.even_belief = self._init_prior(0)
        self.odd_belief  = self._init_prior(1)

        # record visiting
        self.visit = {}

    # -------------------------------
    # 1. prior
    # -------------------------------
    def _init_prior(self, parity):
        grid = np.zeros((self.map_size, self.map_size))

        for x in range(self.map_size):
            for y in range(self.map_size):
                if (x + y) % 2 != parity:
                    continue
                if x in [3, 4] and y in [3, 4]:
                    grid[x][y] = 2.0
                elif x in [2, 3, 4, 5] and y in [2, 3, 4, 5]:
                    grid[x][y] = 1.0
                else:
                    grid[x][y] = 0.1  

    
        s = np.sum(grid)
        if s > 0:
            grid /= s
        return grid


    # -------------------------------
    # 2. update beliefs
    # -------------------------------
    def _update_beliefs(self, board_state, sensor_data):
        for parity in [0, 1]:
            belief = self.even_belief if parity == 0 else self.odd_belief
            heard, felt = sensor_data[parity]

            for x in range(self.map_size):
                for y in range(self.map_size):
                    if belief[x][y] == 0:
                        continue
                    
                    # likelihood = P(sensor | trap at (x,y))
                    p_hear, p_feel = board_state.chicken_player.prob_senses_if_trapdoor_were_at(
                        heard, felt, x, y
                    )
                    belief[x][y] *= (p_hear * p_feel)

            # normalize
            total = np.sum(belief)
            if total > 0:
                belief /= total


    # -------------------------------
    # Utility: corner bonus
    # -------------------------------
    def corner(self, pos):
        return pos in [(0,0),(0,7),(7,0),(7,7)]
    
    # check whether close to enemy turd
    def near_enemy_turd(self, x, y, opp_turds):
        for tx, ty in opp_turds:
            if abs(tx - x) + abs(ty - y) <= 2:
                return True
        return False


    # -------------------------------
    # 3. greedy
    # -------------------------------
    def play(
        self,
        board_state: board.Board,
        sensor_data: List[Tuple[bool, bool]],
        time_left: Callable,
    ):

        my = board_state.chicken_player
        my_loc = my.get_location()
        my_parity = my.even_chicken

        opp = board_state.chicken_enemy
        opp_loc = opp.get_location()
        opp_turds = board_state.turds_enemy

        valid_moves = board_state.get_valid_moves()

        # update visit
        self.visit[my_loc] = self.visit.get(my_loc, 0) + 1

        
        self._update_beliefs(board_state, sensor_data)

        best_move = None
        best_score = -1e18

        for (direction, mtype) in valid_moves:
            newpos = loc_after_direction(my_loc, direction)
            x, y = newpos
            score = 0.0
            mx, myy = my_loc
            my_belief = self.even_belief if (mx + myy) % 2 == 0 else self.odd_belief
            my_trap_prob = my_belief[mx][myy]

            if my_trap_prob > 0.25:
                if mtype == MoveType.EGG or mtype == MoveType.TURD:
                    score -= 99999    # absolutely forbid suicidal egg/turd
                else:
                    score += 2000 

            # ------------------------------
            # Direction Open-Space Preference
            # ------------------------------
            if len(self.visit) < 8:

                from collections import deque

                def is_blocked_for_area(loc):
                    """Check if a cell blocks movement for flood-fill."""
                    if not board_state.is_valid_cell(loc):
                        return True
                    if loc == board_state.chicken_enemy.get_location():
                        return True
                    if loc in board_state.eggs_player or loc in board_state.eggs_enemy:
                        return True
                    if loc in board_state.turds_player or loc in board_state.turds_enemy:
                        return True
                    if board_state.is_cell_in_enemy_turd_zone(loc):
                        return True
                    if loc in board_state.found_trapdoors:
                        return True
                    return False

                def count_open_area(start):
                    if is_blocked_for_area(start):
                        return 0

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

                            if nxt in visited:
                                continue
                            if is_blocked_for_area(nxt):
                                continue

                            visited.add(nxt)
                            q.append(nxt)

                    return count

                open_space = count_open_area((x, y))
                score += open_space * 0.6


            # 1. Egg reward
            if mtype == MoveType.EGG:
                score += 3.0 if self.corner(my_loc) else 1.5

            # 2. Same parity (laying potential)
            if (x + y) % 2 == my_parity:
                score += 0.4

            # 3. Prefer center
            if 1 <= x <= 6 and 1 <= y <= 6:
                score += 0.2

            # 4. Avoid enemy turd zone
            if board_state.is_cell_in_enemy_turd_zone(newpos):
                score -= 1.0

            # 5. trap 
            belief = self.even_belief if (x + y) % 2 == 0 else self.odd_belief
            trap_prob = belief[x][y]

            # Hard avoid
            if trap_prob > 0.20:
                score -= 9999

            # Soft penalty
            score -= trap_prob * 200

            # 6. Visit penalty
            v = self.visit.get(newpos, 0)
            score -= v * 3      
            if v >= 3:
                score -= 10 
            
             # 7. Chase enemy (safe + not laying egg)
            dist_to_enemy = abs(x - opp_loc[0]) + abs(y - opp_loc[1])
            if mtype != MoveType.EGG and trap_prob < 0.05:
                score += max(0, 5 - dist_to_enemy) * 0.3
            
            # if (x + y) % 2 != my_parity:  # cannot lay egg here
            #     if self.near_enemy_turd(x, y, opp_turds):
            #         score -= 4.0

            

              # ------------------------------
            # 9. TURD logic 
            # ------------------------------
            if mtype == MoveType.TURD and my.has_turds_left():

   
                if board_state.can_lay_egg_at_loc(my_loc):
                    score -= 99999
                else:
                    # OK to evaluate TURD
                    # Prefer turd only if enemy is close
                    if abs(opp_loc[0] - x) + abs(opp_loc[1] - y) < dist_to_enemy:
                        score += 3
                    else:
                        score -= 5

                    # Blocking enemy egg-spot
                    if (x + y) % 2 == opp.even_chicken:
                        score += 4.0

                    # Avoid trap
                    if trap_prob > 0.1:
                        score -= 50

                    # Not too early
                    if len(self.visit) < 4:
                        score -= 10

                    # No corner
                    if (x, y) in [(0,0),(0,7),(7,0),(7,7)]:
                        score -= 6

            if score > best_score:
                best_score = score
                best_move = (direction, mtype)

        return best_move
