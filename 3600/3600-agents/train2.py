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

# === 基础配置 ===
TRAINEE = "Nibbles"     # 你的 Agent 名字
OPPONENT = "Fuzzby"       # 陪练对象
CONFIG_FILE = os.path.join(current_dir, f"{TRAINEE}/config.py")
ROUNDS = 20             
EPOCHS = 100            

# ==========================================
# 🎮 人工干预区 (根据你的策略：奖罚都加倍)
# ==========================================
DIRECTION_GUIDE = {



    'OPEN_SPACE_WEIGHT': "RANDOM",
    'CORNER_BONUS': "RANDOM",
    'EGG_BONUS': "UP",
    'PARITY_BONUS': "RANDOM",
    'CENTER_BONUS': "RANDOM",
    'TRAP_PENALTY': "UP",
    'ENEMY_TURD_PENALTY': "RANDOM",
    'VISIT_PENALTY': "UP",
    'CHASE_WEIGHT': "RANDOM",
    'TURD_OFFENSE_BONUS':  "UP",
    'TURD_BLOCK_BONUS': "RANDOM",
}
# ==========================================

# === 静音工具 ===
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
        f.write(f"# {TRAINEE} Guided Evolution Params\n")
        f.write("PARAMS = {\n")
        for k, v in params.items():
            f.write(f"    '{k}': {v},\n")
        f.write("}\n")

# ==========================================
# 🔥 核心修改：带方向的变异逻辑 🔥
# ==========================================
def mutate(params):
    new_params = params.copy()
    keys = list(new_params.keys())
    
    # 随机选 1-3 个参数修改
    num_changes = random.choices([1, 2, 3], weights=[30, 50, 20])[0]
    targets = random.sample(keys, min(num_changes, len(keys)))
    
    change_log = []

    for key in targets:
        val = new_params[key]
        direction = DIRECTION_GUIDE.get(key, "RANDOM") # 获取你的指令
        
        # 计算变动幅度 (5% - 25%)
        # 使用高斯分布，让变动更平滑
        delta = abs(val * random.uniform(0.05, 0.25))
        if delta < 0.05: delta = 0.1 # 保证最小值变化

        change = 0
        arrow = ""

        if direction == "UP":
            # 强制增加
            change = delta
            arrow = "⬆️"
        elif direction == "DOWN":
            # 强制减少
            change = -delta
            arrow = "⬇️"
        else:
            # 随机 (RANDOM)
            change = delta if random.random() > 0.5 else -delta
            arrow = "↕️"

        new_val = round(val + change, 4)
        if new_val < 0: new_val = 0.0 # 不允许负数
        
        new_params[key] = new_val
        change_log.append(f"{key[:10]} {arrow} {new_val}")

    return " | ".join(change_log), new_params

def evaluate(rounds):
    wins = 0
    score_diff = 0
    
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

                    score_diff += (s1 - s2)
                    if s1 > s2: wins += 1
                except:
                    pass
        except:
            pass
            
    return wins, score_diff

def main():
    print(f"🧬 {TRAINEE} 导向进化模式启动 (Guide Mode)")
    print(f"🎯 人工干预方向: {DIRECTION_GUIDE}\n")
    
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
        # 1. 变异 (带方向)
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
            save_params(curr_params)
        else:
            print(f"❌ 失败 (分: {score})")
            # 失败后，下一次循环会自动基于旧的 curr_params 重新生成
            # 这里如果不写回旧参数，文件里留的就是错误的参数
            # 所以为了安全，这里把它写回去
            save_params(curr_params)

    print("\n" + "="*70)
    print(f"🏆 训练结束，{TRAINEE} 最终参数如下：")
    print(curr_params)

if __name__ == "__main__":
    main()