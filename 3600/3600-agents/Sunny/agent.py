from collections.abc import Callable
from typing import List, Tuple
from game import board
from game.enums import Direction, MoveType, loc_after_direction

class PlayerAgent:

    def __init__(self, board: board.Board, time_left: Callable):
        self.trap_even = 0.0
        self.trap_odd  = 0.0
        self.visit = {}   # <--- record visit

    def trap_danger(self, sensor):
        heard, felt = sensor
        return (0.5 if heard else 0.0) + (1.0 if felt else 0.0)

    def corner(self, pos):
        return pos in [(0,0),(0,7),(7,0),(7,7)]

    def play(
        self,
        board_state: board.Board,
        sensor_data: List[Tuple[bool, bool]],
        time_left: Callable
    ):

        my  = board_state.chicken_player
        my_loc = my.get_location()
        my_parity = my.even_chicken   

        valid_moves = board_state.get_valid_moves()

        # Update visit count 
        self.visit[my_loc] = self.visit.get(my_loc, 0) + 1

        # Update trap beliefs
        self.trap_even = 0.7*self.trap_even + 0.3*self.trap_danger(sensor_data[0])
        self.trap_odd  = 0.7*self.trap_odd  + 0.3*self.trap_danger(sensor_data[1])

        best_score = -1e18
        best_move  = None

        for (direction, mtype) in valid_moves:
            newpos = loc_after_direction(my_loc, direction)
            x, y = newpos
            score = 0.0

            # 1. Egg reward
            if mtype == MoveType.EGG:
                score += 3.0 if self.corner(my_loc) else 1.5

            # 2. Staying in own color is good
            if (x + y) % 2 == my_parity:
                score += 0.4

            # 3. Prefer center
            if 1 <= x <= 6 and 1 <= y <= 6:
                score += 0.2

            # 4. Avoid enemy turd zone
            if board_state.is_cell_in_enemy_turd_zone(newpos):
                score -= 3.0

            # 5. Trapdoor danger
      
            trap_signal = self.trap_even if (x+y) % 2 == 0 else self.trap_odd
            
            dist_to_center = abs(x - 3.5) + abs(y - 3.5) 
            
            distance_factor = max(0, 5 - dist_to_center) / 5   
            
            trap_penalty = trap_signal * (2 + 8 * distance_factor)

            score -= trap_penalty

            # 6. Avoid repeating positions 
            score -= self.visit.get(newpos, 0) * 0.6

            if score > best_score:
                best_score = score
                best_move = (direction, mtype)

        return best_move