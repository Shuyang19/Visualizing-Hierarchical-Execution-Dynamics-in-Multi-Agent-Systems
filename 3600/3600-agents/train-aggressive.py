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
TRAINEE = "Pawbert"        # 正在训练的 Agent
OPPONENT = "Fuzzby"       # 陪练
CONFIG_FILE = os.path.join(current_dir, f"{TRAINEE}/config.py")
ROUNDS = 20             # 每一轮打多少局
EPOCHS = 100            # 训练多少轮
# ============

# === 静音工具类 ===
class SilentContext:
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
        f.write(f"# {TRAINEE} 进化中的参数\n")
        f.write("PARAMS = {\n")
        for k, v in params.items():
            f.write(f"    '{k}': {v},\n")
        f.write("}\n")

# ==================================================
# 🔥 核心升级：更智能的变异逻辑 🔥
# ==================================================
def mutate(params):
    """
    高斯混合变异：
    1. 随机决定修改 1-3 个参数 (不再单一)
    2. 使用高斯分布 (正态分布) 进行数值调整，更自然
    """
    new_params = params.copy()
    keys = list(new_params.keys())
    
    # 决定这次改几个参数？(30%概率改1个, 50%概率改2个, 20%概率改3个)
    num_changes = random.choices([1, 2, 3], weights=[30, 50, 20])[0]
    
    # 随机选出要改的参数
    targets = random.sample(keys, min(num_changes, len(keys)))
    
    change_log = []

    for key in targets:
        val = new_params[key]
        
        # 高斯噪音: 均值为0，标准差为当前值的 15%
        # 这意味着大多数变动在 +/- 15% 之间，但偶尔会有大跳跃
        sigma = max(val * 0.15, 0.05) 
        change = random.gauss(0, sigma)
        
        new_val = round(val + change, 4)
        if new_val < 0: new_val = 0.0 # 保证参数不为负
        
        new_params[key] = new_val
        change_log.append(f"{key[:8]}..:{val}->{new_val}")

    return " | ".join(change_log), new_params

def evaluate(rounds):
    """跑分 (完全静音)"""
    score_diff_total = 0
    wins = 0
    
    with SilentContext():
        try:
            for r in range(rounds):
                p1, p2 = (TRAINEE, OPPONENT) if r % 2 == 0 else (OPPONENT, TRAINEE)
                try:
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
    print(f"🧬 {TRAINEE} 智能进化程序启动 (vs {OPPONENT})")
    
    if not os.path.exists(CONFIG_FILE):
        print(f"错误: 找不到 {CONFIG_FILE}")
        return

    curr_params = load_params()
    
    print("正在评估当前水平 (Baseline)... ", end="", flush=True)
    wins, score = evaluate(ROUNDS)
    best_score = score
    print(f"完成! \n初始战绩: 胜场 {wins}/{ROUNDS} | 净胜分: {score}\n")
    print("-" * 70)

    for i in range(EPOCHS):
        # 1. 智能变异
        log_str, test_params = mutate(curr_params)
        save_params(test_params)
        
        # 2. 打印
        print(f"[{i+1}/{EPOCHS}] 尝试: {log_str} ... ", end="", flush=True)
        
        # 3. 测试
        wins, score = evaluate(ROUNDS)
        
        # 4. 评估
        if score > best_score:
            print(f"✅ 成功! (分: {score}, 胜: {wins})")
            best_score = score
            curr_params = test_params
            
            # [额外] 如果变强了，立刻再存一次，以防下次变异失败回滚时丢失
            save_params(curr_params)
        else:
            print(f"❌ 失败 (分: {score})")
            # 这里的 curr_params 还是旧的，下次循环会自动用旧的继续变异
            # 这一步是为了让 config.py 回滚到最佳状态，防止被失败的参数覆盖
            save_params(curr_params)

    print("\n" + "="*70)
    print(f"🏆 训练结束，{TRAINEE} 最终参数如下：")
    print(curr_params)

if __name__ == "__main__":
    main()