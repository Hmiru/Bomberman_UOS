import subprocess
import sys

# Test 1: Basic game with random agents
print("Test 1: Random agents only...")
result = subprocess.run([sys.executable, "main.py", "play", 
                        "--agents", "random_agent", "random_agent", "random_agent", "random_agent",
                        "--n-rounds", "1", "--no-gui"], 
                       capture_output=True, text=True, timeout=10)
print("Random agents test:", "SUCCESS" if result.returncode == 0 else "FAILED")

# Test 2: Totoro vs Rule-based
print("\nTest 2: Wolf vs Rule-based...")
result = subprocess.run([sys.executable, "main.py", "play",
                        "--agents", "wolf", "wolf", "rule_based_agent", "rule_based_agent", 
                        "--n-rounds", "1", "--no-gui"],
                       capture_output=True, text=True, timeout=30)
print("Wolf test:", "SUCCESS" if result.returncode == 0 else "FAILED")

if result.returncode != 0:
    print("\nError output:")
    print(result.stderr[:500])

# Check logs
print("\nChecking recent logs...")
with open("logs/game.log", "r") as f:
    lines = f.readlines()
    # Find lines with scores or wins
    for line in lines[-100:]:
        if "score" in line.lower() or "win" in line.lower() or "died" in line.lower():
            print(line.strip())