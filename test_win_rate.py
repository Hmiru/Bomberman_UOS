import subprocess
import re
from collections import defaultdict

def run_match(n_rounds=10):
    """Run a match and extract results"""
    cmd = ["python", "main.py", "play", 
           "--agents", "totoro", "totoro", "rule_based_agent", "rule_based_agent",
           "--n-rounds", str(n_rounds), "--no-gui"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def parse_results(output):
    """Parse match results from output"""
    wins = defaultdict(int)
    scores = defaultdict(list)
    
    # Find winner patterns in output
    lines = output.split('\n')
    for line in lines:
        if 'wins' in line.lower() or 'winner' in line.lower():
            # Extract winner information
            if 'totoro' in line:
                wins['totoro'] += 1
            elif 'rule_based' in line:
                wins['rule_based'] += 1
    
    return wins, scores

def calculate_win_rate(n_matches=10, rounds_per_match=10):
    """Calculate win rate over multiple matches"""
    totoro_wins = 0
    rule_based_wins = 0
    draws = 0
    
    print(f"Running {n_matches} matches with {rounds_per_match} rounds each...")
    
    for i in range(n_matches):
        print(f"Match {i+1}/{n_matches}...", end=' ')
        output = run_match(rounds_per_match)
        
        # Simple heuristic: check which team appears more in the logs
        totoro_count = output.count('totoro')
        rule_based_count = output.count('rule_based')
        
        # Assuming the team that survives longer appears more in logs
        if totoro_count > rule_based_count * 1.1:  # 10% margin
            totoro_wins += 1
            print("Totoro team wins!")
        elif rule_based_count > totoro_count * 1.1:
            rule_based_wins += 1
            print("Rule-based team wins!")
        else:
            draws += 1
            print("Draw!")
    
    print("\n" + "="*50)
    print("RESULTS:")
    print(f"Totoro wins: {totoro_wins}/{n_matches} ({totoro_wins/n_matches*100:.1f}%)")
    print(f"Rule-based wins: {rule_based_wins}/{n_matches} ({rule_based_wins/n_matches*100:.1f}%)")
    print(f"Draws: {draws}/{n_matches} ({draws/n_matches*100:.1f}%)")
    print("="*50)
    
    win_rate = totoro_wins / n_matches * 100
    print(f"\nTotoro win rate: {win_rate:.1f}%")
    if win_rate >= 50:
        print("TARGET ACHIEVED! Win rate >= 50%")
    else:
        print(f"Need {50-win_rate:.1f}% more to reach target")
    
    return win_rate

if __name__ == "__main__":
    # Run test with 10 matches
    win_rate = calculate_win_rate(n_matches=10, rounds_per_match=5)