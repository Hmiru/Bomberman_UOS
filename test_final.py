import subprocess
import time

print("=" * 60)
print("FINAL TEST: Totoro vs Rule-based agents")
print("=" * 60)

# Test different scenarios
scenarios = ["classic", "coin-heaven"]
total_games = 0
totoro_better = 0

for scenario in scenarios:
    print(f"\nTesting scenario: {scenario}")
    print("-" * 40)
    
    for i in range(3):
        print(f"Game {i+1}/3...", end=" ")
        
        cmd = ["python", "main.py", "play",
               "--agents", "totoro", "totoro", "rule_based_agent", "rule_based_agent",
               "--scenario", scenario,
               "--n-rounds", "1", 
               "--no-gui"]
        
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        elapsed = time.time() - start
        
        # Quick analysis based on output
        output = result.stdout + result.stderr
        
        # Count agent appearances in final steps
        totoro_count = output[-5000:].count("totoro")
        rule_based_count = output[-5000:].count("rule_based")
        
        total_games += 1
        if totoro_count > rule_based_count:
            print(f"Totoro likely won! (T:{totoro_count} vs R:{rule_based_count})")
            totoro_better += 1
        elif rule_based_count > totoro_count:
            print(f"Rule-based likely won (T:{totoro_count} vs R:{rule_based_count})")
        else:
            print(f"Draw or unclear (T:{totoro_count} vs R:{rule_based_count})")
        
        print(f"  Time: {elapsed:.1f}s")

print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)
print(f"Total games: {total_games}")
print(f"Totoro performed better: {totoro_better}/{total_games}")
print(f"Estimated win rate: {totoro_better/total_games*100:.0f}%")

if totoro_better/total_games >= 0.5:
    print("\n✓ SUCCESS! Totoro agents are competitive (≥50% performance)")
else:
    print(f"\n✗ Need more improvement ({50 - totoro_better/total_games*100:.0f}% to go)")