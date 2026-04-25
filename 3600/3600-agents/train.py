import os
import sys
import random
import importlib.util

# ==========================================
# ⚡️ 路径修复补丁 ⚡️
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, 'engine'))

try:
    from gameplay import play_game
except ImportError:
    try:
        from engine.gameplay import play_game
    except ImportError:
        print(f"❌ 错误: 找不到 'gameplay' 模块。")
        sys.exit(1)

# === 配置 ===
TRAINEE = "Fuzzby"      
OPPONENT = "Judy"       
CONFIG_FILE = os.path.join(current_dir, f"{TRAINEE}/config.py")
ROUNDS = 20             
EPOCHS = 100            
# ============

# === 静音工具类 ===
class SilentContext:
    """一个上下文管理器，用来暂时屏蔽所有输出"""
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

def load_params():
    spec = importlib.util.spec_from_file_location("config", CONFIG_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PARAMS.copy()

def save_params(params):
    with open(CONFIG_FILE, 'w') as f:
        f.write("# Fuzzby 进化中的参数\n")
        f.write("PARAMS = {\n")
        for k, v in params.items():
            f.write(f"    '{k}': {v},\n")
        f.write("}\n")

def mutate(params):
    new_params = params.copy()
    key = random.choice(list(new_params.keys()))
    val = new_params[key]
    
    change = val * random.uniform(-0.2, 0.2)
    if abs(change) < 0.05: change = random.choice([-0.1, 0.1])
    
    new_val = round(val + change, 4)
    if new_val < 0: new_val = 0.0
    
    new_params[key] = new_val
    return key, val, new_val, new_params

def evaluate(rounds):
    """Fuzzby vs Judy 跑分 (完全静音版)"""
    score_diff_total = 0
    wins = 0
    
    # 使用静音环境运行游戏
    with SilentContext():
        try:
            for r in range(rounds):
                p1, p2 = (TRAINEE, OPPONENT) if r % 2 == 0 else (OPPONENT, TRAINEE)
                try:
                    # 这里的 print(False) 以前会漏出来，现在会被 SilentContext 吃掉
                    board, _, _, err_a, err_b = play_game(
                        os.getcwd(), os.getcwd(), p1, p2,
                        display_game=False, record=True, limit_resources=False
                    )
                    
                    if p1 == TRAINEE:
                        s1 = board.chicken_player.get_eggs_laid()
                        s2 = board.chicken_enemy.get_eggs_laid()
                        if err_a: s1 = -999
                    else:
                        s1 = board.chicken_enemy.get_eggs_laid()
                        s2 = board.chicken_player.get_eggs_laid()
                        if err_b: s1 = -999

                    score_diff_total += (s1 - s2)
                    if s1 > s2: wins += 1
                except:
                    pass
        except Exception:
            pass
        
    return wins, score_diff_total

def main():
    print(f"🧬 Fuzzby 自我进化程序启动 (vs {OPPONENT})")
    
    if not os.path.exists(CONFIG_FILE):
        print(f"错误: 找不到 {CONFIG_FILE}")
        return

    curr_params = load_params()
    
    print("正在评估当前水平 (Baseline)... ", end="", flush=True)
    wins, score = evaluate(ROUNDS)
    best_score = score
    print(f"完成! \n初始战绩: 胜场 {wins}/{ROUNDS} | 净胜分: {score}\n")
    print("-" * 60)

    for i in range(EPOCHS):
        # 1. 变异
        key, old, new, test_params = mutate(curr_params)
        save_params(test_params)
        
        # 2. 打印进度 (不换行)
        print(f"[{i+1}/{EPOCHS}] 尝试 {key}: {old} -> {new} ... ", end="", flush=True)
        
        # 3. 测试 (此时进入静音模式，不会打印 False)
        wins, score = evaluate(ROUNDS)
        
        # 4. 打印结果
        if score > best_score:
            print(f"✅ 成功! (分: {score}, 胜: {wins})")
            best_score = score
            curr_params = test_params
        else:
            print(f"❌ 失败 (分: {score})")
            
        save_params(curr_params)

    print("\n" + "="*60)
    print("🏆 训练结束，Fuzzby 最终参数如下：")
    print(curr_params)

if __name__ == "__main__":
    main()