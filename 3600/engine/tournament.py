import os
import pathlib
import sys
import time
from collections import defaultdict

# 尝试导入引擎模块
try:
    from board_utils import get_history_json
    from gameplay import play_game
    # 尝试导入 Result 枚举，如果不行就用字符串判断
    from game.enums import Result 
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), 'engine'))
    from board_utils import get_history_json
    from gameplay import play_game
    from game.enums import Result

# === 配置区 ===
AGENTS = ["Fuzzby", "Pawbert", "Judy", "Goat"] 
ROUNDS = 50 
# =============

def get_winner(board, err_a, err_b):
    """根据返回的 board 和 错误信息判断赢家"""
    # 1. 判崩溃
    if err_a: return "B" # A 崩了
    if err_b: return "A" # B 崩了
    
    # 2. 判分数 (这是修正点！)
    # 不能只数 board.eggs_player (那是物理蛋数)
    # 必须用 get_eggs_laid() (这是包含角落加分、堵死奖励的总分)
    score_a = board.chicken_player.get_eggs_laid()
    score_b = board.chicken_enemy.get_eggs_laid()
    
    if score_a > score_b: return "A"
    if score_b > score_a: return "B"
    
    # 双重保险：检查 board.winner 属性
    if board.winner == Result.PLAYER: return "A"
    if board.winner == Result.ENEMY: return "B"
    
    return "Draw"

def main():
    top_level = pathlib.Path(__file__).parent.parent.resolve()
    play_directory = os.path.join(top_level, "3600-agents")
    
    if not os.path.exists(os.path.join(play_directory, AGENTS[0])):
        play_directory = os.getcwd()

    stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "crashes": 0})
    
    print(f"🥊 开始大乱斗 (修正计分版)！参赛: {AGENTS}")
    print(f"🔄 每组: {ROUNDS} 局\n")

    start_time = time.perf_counter()

    for i in range(len(AGENTS)):
        for j in range(i + 1, len(AGENTS)):
            agent1 = AGENTS[i]
            agent2 = AGENTS[j]
            
            print(f"⚔️  {agent1} vs {agent2} ...", end=" ", flush=True)
            
            for r in range(ROUNDS):
                # 轮流先手
                if r % 2 == 0:
                    player_a, player_b = agent1, agent2
                else:
                    player_a, player_b = agent2, agent1

                try:
                    final_board, trapdoors, spawns, err_a, err_b = play_game(
                        play_directory,
                        play_directory,
                        player_a,
                        player_b,
                        display_game=False,  
                        delay=0.0,
                        clear_screen=False,
                        record=True,        # 必须为 True
                        limit_resources=False,
                    )

                    result = get_winner(final_board, err_a, err_b)
                    
                    winner_name = None
                    if result == "A":
                        winner_name = player_a
                    elif result == "B":
                        winner_name = player_b
                    
                    if winner_name:
                        stats[winner_name]["wins"] += 1
                        loser = player_b if winner_name == player_a else player_a
                        stats[loser]["losses"] += 1
                    else:
                        stats[player_a]["draws"] += 1
                        stats[player_b]["draws"] += 1
                        
                    if err_a: stats[player_a]["crashes"] += 1
                    if err_b: stats[player_b]["crashes"] += 1
                    
                except Exception as e:
                    print(f"\n! 错误: {e}")

            print("完成")

    duration = time.perf_counter() - start_time
    
    print("\n" + "="*50)
    print(f"🏆 最终榜单 (Score-Based) 耗时{duration:.1f}s 🏆")
    print("="*50)
    print(f"{'选手':<10} | {'胜率':<8} | {'胜':<4} {'负':<4} {'平':<4} | {'崩溃':<4}")
    print("-" * 50)
    
    sorted_agents = sorted(AGENTS, key=lambda x: stats[x]["wins"], reverse=True)
    
    for agent in sorted_agents:
        s = stats[agent]
        total = s['wins'] + s['losses'] + s['draws']
        rate = (s['wins'] / total * 100) if total > 0 else 0.0
        print(f"{agent:<12} | {rate:.1f}%    | {s['wins']:<4} {s['losses']:<4} {s['draws']:<4} | {s['crashes']:<4}")

if __name__ == "__main__":
    main()