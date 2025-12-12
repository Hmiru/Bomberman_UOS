import subprocess
import time

print("=" * 60)
print("SAFETY TEST: Check if totoro agents survive better")
print("=" * 60)

# Test multiple games
deaths = {"totoro": 0, "rule_based": 0}
survivals = {"totoro": 0, "rule_based": 0}

for i in range(5):
    print(f"\nGame {i+1}/5...", end=" ")
    
    cmd = ["python", "main.py", "play",
           "--agents", "totoro", "totoro", "rule_based_agent", "rule_based_agent",
           "--n-rounds", "1", 
           "--no-gui"]
    
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    elapsed = time.time() - start
    
    # Check the last part of output
    output_end = result.stdout[-3000:] + result.stderr[-3000:]
    
    # Count final appearances (agents appearing at end = survived)
    totoro_final = output_end.count("totoro")
    rule_based_final = output_end.count("rule_based")
    
    print(f"Time: {elapsed:.1f}s")
    print(f"  Final appearances - Totoro: {totoro_final}, Rule-based: {rule_based_final}")
    
    # Rough estimation: more appearances = likely survived
    if totoro_final > 0:
        survivals["totoro"] += 1
    if rule_based_final > 0:
        survivals["rule_based"] += 1

print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print(f"Totoro survivals: {survivals['totoro']}/5")
print(f"Rule-based survivals: {survivals['rule_based']}/5")

if survivals["totoro"] >= survivals["rule_based"]:
    print("\nGood! Totoro agents are surviving at least as well as rule-based")
else:
    print("\nTotoro agents need more safety improvements")