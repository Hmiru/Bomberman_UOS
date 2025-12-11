import subprocess
import json
import os
from datetime import datetime

def run_single_match():
    """Run a single match and save stats"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stats_file = f"test_stats_{timestamp}.json"
    
    cmd = ["python", "main.py", "play",
           "--agents", "totoro", "totoro", "rule_based_agent", "rule_based_agent",
           "--n-rounds", "1", "--no-gui", "--save-stats", stats_file]
    
    print("Running match...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Read the stats file if it exists
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            stats = json.load(f)
        
        print("\n=== Match Results ===")
        for agent, data in stats.items():
            if isinstance(data, dict):
                print(f"\n{agent}:")
                print(f"  Score: {data.get('score', 0)}")
                print(f"  Kills: {data.get('kills', 0)}")  
                print(f"  Coins: {data.get('coins', 0)}")
                print(f"  Survived: {data.get('survived', 'N/A')}")
        
        # Determine winner
        totoro_total = 0
        rule_based_total = 0
        
        for agent, data in stats.items():
            if isinstance(data, dict):
                score = data.get('score', 0)
                if 'totoro' in agent:
                    totoro_total += score
                elif 'rule_based' in agent:
                    rule_based_total += score
        
        print("\n=== Team Scores ===")
        print(f"Totoro Team: {totoro_total}")
        print(f"Rule-based Team: {rule_based_total}")
        
        if totoro_total > rule_based_total:
            print("Winner: TOTORO TEAM!")
            winner = "totoro"
        elif rule_based_total > totoro_total:
            print("Winner: RULE-BASED TEAM!")
            winner = "rule_based"
        else:
            print("Result: DRAW!")
            winner = "draw"
        
        # Clean up stats file
        os.remove(stats_file)
        
        return winner, totoro_total, rule_based_total
    else:
        print("No stats file generated")
        return "draw", 0, 0

def run_multiple_matches(n=10):
    """Run multiple matches and calculate statistics"""
    results = {"totoro": 0, "rule_based": 0, "draw": 0}
    score_diffs = []
    
    for i in range(n):
        print(f"\n{'='*50}")
        print(f"MATCH {i+1}/{n}")
        print('='*50)
        
        winner, totoro_score, rule_based_score = run_single_match()
        results[winner] += 1
        score_diffs.append(totoro_score - rule_based_score)
    
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print('='*60)
    print(f"Totoro Wins: {results['totoro']}/{n} ({results['totoro']/n*100:.1f}%)")
    print(f"Rule-based Wins: {results['rule_based']}/{n} ({results['rule_based']/n*100:.1f}%)")
    print(f"Draws: {results['draw']}/{n} ({results['draw']/n*100:.1f}%)")
    
    avg_diff = sum(score_diffs) / len(score_diffs) if score_diffs else 0
    print(f"\nAverage Score Difference: {avg_diff:.1f} (positive = Totoro ahead)")
    
    win_rate = results['totoro'] / n * 100
    print(f"\nTotoro Win Rate: {win_rate:.1f}%")
    if win_rate >= 50:
        print("SUCCESS! Target of 50% achieved!")
    else:
        print(f"Need {50-win_rate:.1f}% more to reach target")

if __name__ == "__main__":
    run_multiple_matches(5)  # Run 5 matches for quick test