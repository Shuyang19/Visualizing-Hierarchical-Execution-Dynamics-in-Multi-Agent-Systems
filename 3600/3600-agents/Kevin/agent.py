from collections.abc import Callable
from typing import List, Tuple
import numpy as np
from game import board as game_board
from game.enums import Direction, MoveType

class SearchTimeout(Exception):
    pass

class PlayerAgent:
    def __init__(self, board: game_board.Board, time_left: Callable):
        self.map_size = board.game_map.MAP_SIZE
        self.even_belief = self._initialize_priors(0)
        self.odd_belief = self._initialize_priors(1)

    def _initialize_priors(self, parity):
        grid = np.zeros((self.map_size, self.map_size))
        for x in range(self.map_size):
            for y in range(self.map_size):
                if (x + y) % 2 != parity: continue 
                if x in [3, 4] and y in [3, 4]: grid[x][y] = 2.0
                elif x in [2, 3, 4, 5] and y in [2, 3, 4, 5]: grid[x][y] = 1.0
                else: grid[x][y] = 0.0 
        total = np.sum(grid)
        if total > 0: grid /= total
        return grid

    def update_beliefs(self, board, sensor_data):
        for parity in [0, 1]:
            prior_grid = self.even_belief if parity == 0 else self.odd_belief
            heard, felt = sensor_data[parity]
            for x in range(self.map_size):
                for y in range(self.map_size):
                    if prior_grid[x][y] == 0: continue
                    probs = board.chicken_player.prob_senses_if_trapdoor_were_at(heard, felt, x, y)
                    prior_grid[x][y] *= (probs[0] * probs[1])
            total = np.sum(prior_grid)
            if total > 0: prior_grid /= total

    def heuristic(self, board: game_board.Board):
        score = 0
        
        # --- 1. PRIMARY OBJECTIVE: EGG COUNT ---
        # If we can lay an egg, DO IT.
        my_eggs = board.chicken_player.get_eggs_laid()
        opp_eggs = board.chicken_enemy.get_eggs_laid()
        score += (my_eggs - opp_eggs) * 10000 

        # --- 2. TRAPDOOR SAFETY ---
        my_loc = board.chicken_player.get_location()
        
        if (my_loc[0] + my_loc[1]) % 2 == 0:
            risk = self.even_belief[my_loc]
        else:
            risk = self.odd_belief[my_loc]
            
        if risk > 0.05: 
            score -= risk * 50000

        # --- 3. POSITION QUALITY (The Fix) ---
        # Am I on a useful square?
        is_even_loc = (my_loc[0] + my_loc[1]) % 2 == 0
        is_my_parity = (is_even_loc == (board.chicken_player.even_chicken == 0))
        
        if is_my_parity:
            # Good Parity (I can theoretically lay here)
            # CRITICAL CHECK: Is there already an egg here?
            if my_loc in board.eggs_player:
                # I am standing on my own egg. This is USELESS.
                # Penalize this so I leave to find an empty square.
                score -= 300 
            else:
                # Empty useful square. This is HEAVEN.
                score += 200 
        else:
            # Bad Parity (Odd square). Just a transition spot.
            score -= 50 

        # --- 4. TIE BREAKERS ---
        # Move towards center to avoid getting stuck on edges
        dist_to_center = abs(my_loc[0] - 3.5) + abs(my_loc[1] - 3.5)
        score -= dist_to_center * 10

        return score

    def minimax(self, board, depth, alpha, beta, maximizing_player, time_left, stop_time, check_timer=True):
        # Only check timer if allowed (skips check for Depth 1)
        if check_timer and time_left() < stop_time: 
            raise SearchTimeout()

        if depth == 0 or board.is_game_over():
            return self.heuristic(board)
        
        valid_moves = board.get_valid_moves(enemy=not maximizing_player)
        
        # Optimization: Sort moves to look at EGGs first (Alpha-Beta works better)
        valid_moves.sort(key=lambda m: m[1] == MoveType.EGG, reverse=True)

        if maximizing_player:
            max_eval = -float('inf')
            for move in valid_moves:
                next_board = board.forecast_move(move[0], move[1])
                if next_board is None: continue
                eval = self.minimax(next_board, depth - 1, alpha, beta, False, time_left, stop_time, check_timer)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha: break
            return max_eval
        else:
            min_eval = float('inf')
            for move in valid_moves:
                next_board = board.forecast_move(move[0], move[1])
                if next_board is None: continue
                eval = self.minimax(next_board, depth - 1, alpha, beta, True, time_left, stop_time, check_timer)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha: break
            return min_eval

    def play(self, board, sensor_data, time_left):
        self.update_beliefs(board, sensor_data)
        
        valid_moves = board.get_valid_moves()
        if not valid_moves: return (Direction.UP, MoveType.PLAIN)

        # CRITICAL FIX 1: Sort valid_moves so EGG is first. 
        # If we time out instantly, we default to valid_moves[0], which will now be an EGG.
        valid_moves.sort(key=lambda m: m[1] == MoveType.EGG, reverse=True)
        best_move = valid_moves[0]
        
        # Time Management
        time_limit = 0.8
        if time_left() < 10.0: time_limit = 0.2
        stop_time = time_left() - time_limit 

        # CRITICAL FIX 2: Guarantee Depth 1 runs without timeout
        # We manually run the first level of recursion to ensure we never return a default blindly.
        try:
            current_best_move = None
            alpha = -float('inf')
            beta = float('inf')
            best_val = -float('inf')

            for move in valid_moves:
                next_board = board.forecast_move(move[0], move[1])
                if next_board is None: continue
                
                # Call minimax with depth=0 (Leaf evaluation) and check_timer=False
                val = self.minimax(next_board, 0, alpha, beta, False, time_left, stop_time, check_timer=False)
                
                if val > best_val:
                    best_val = val
                    current_best_move = move
                alpha = max(alpha, best_val)
            
            if current_best_move:
                best_move = current_best_move

        except Exception:
            pass # Should not happen with check_timer=False

        # Depth 2+ (Iterative Deepening with Timer)
        max_depth = 2
        try:
            while True:
                current_best_move = None
                alpha = -float('inf')
                beta = float('inf')
                best_val = -float('inf')

                for move in valid_moves:
                    next_board = board.forecast_move(move[0], move[1])
                    if next_board is None: continue
                    
                    # check_timer=True for deeper searches
                    val = self.minimax(next_board, max_depth-1, alpha, beta, False, time_left, stop_time, check_timer=True)
                    
                    if val > best_val:
                        best_val = val
                        current_best_move = move
                    alpha = max(alpha, best_val)

                if current_best_move:
                    best_move = current_best_move
                
                max_depth += 1
                if max_depth > 5: break
                    
        except SearchTimeout:
            pass # Timeout is fine, we have a safe best_move from Depth 1
        
        return best_move