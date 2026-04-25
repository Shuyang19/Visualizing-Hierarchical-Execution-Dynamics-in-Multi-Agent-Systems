from game import board as game_board

class ChokeAnalyzer:
    def __init__(self):
        pass

    def opponent_free_moves(self, board: game_board.Board):
        """Count opponent legal moves."""
        return len(board.get_valid_moves(enemy=True))

    def is_choke_move(self, board: game_board.Board, move):
        """
        True if this move reduces opponent legal moves.
        """
        next_board = board.forecast_move(move[0], move[1])
        if next_board is None:
            return False

        before = self.opponent_free_moves(board)
        after = self.opponent_free_moves(next_board)

        return after < before
