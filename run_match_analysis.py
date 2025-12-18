import subprocess
import json
import csv
from datetime import datetime
import os
import re

def run_match(round_num):
    """Run a single match and capture the results"""
    cmd = [
        "python", "main.py", "play",
        "--agents", "rule_based_agent", "wolf", "rule_based_agent", "wolf",
        "--no-gui",
        "--n-rounds", "10",
        "--silence-errors"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse the output to extract scores
    output = result.stdout
    
    # Initialize scores
    scores = {
        "rule_based_agent_0": 0,
        "wolf_0": 0,
        "rule_based_agent_1": 0,
        "wolf_1": 0
    }
    
    # Look for final scores in the output
    lines = output.split('\n')
    for line in lines:
        # Look for lines containing final scores
        if "final" in line.lower() or "score" in line.lower():
            # Try different patterns for score extraction
            # Pattern 1: "Agent name (id) score: X"
            match = re.search(r'(\w+(?:_\w+)*)\s*\((\d+)\)[:\s]*score[:\s]*(-?\d+)', line, re.IGNORECASE)
            if not match:
                # Pattern 2: "name (id): X points"
                match = re.search(r'(\w+(?:_\w+)*)\s*\((\d+)\)[:\s]*(-?\d+)\s*points?', line, re.IGNORECASE)
            
            if match:
                agent_type = match.group(1)
                agent_id = int(match.group(2))
                score = int(match.group(3))
                
                if "rule_based" in agent_type.lower():
                    if agent_id == 0:
                        scores["rule_based_agent_0"] = score
                    else:
                        scores["rule_based_agent_1"] = score
                elif "wolf" in agent_type.lower():
                    if agent_id == 0:
                        scores["wolf_0"] = score
                    else:
                        scores["wolf_1"] = score
    
    # Check for winner in output
    winner = None
    for line in lines:
        if "wins" in line.lower() or "winner" in line.lower():
            if "rule_based_agent" in line.lower():
                winner = "rule_based_agent"
            elif "wolf" in line.lower():
                winner = "wolf"
            elif "draw" in line.lower() or "tie" in line.lower():
                winner = "draw"
    
    return {
        "round": round_num,
        "rule_based_agent_0_score": scores["rule_based_agent_0"],
        "rule_based_agent_1_score": scores["rule_based_agent_1"],
        "wolf_0_score": scores["wolf_0"],
        "wolf_1_score": scores["wolf_1"],
        "rule_based_total": scores["rule_based_agent_0"] + scores["rule_based_agent_1"],
        "wolf_total": scores["wolf_0"] + scores["wolf_1"],
        "winner": winner
    }

def main():
    print("Starting matches between rule_based_agent and wolf_agent...")
    print("-" * 50)
    
    results = []
    
    # Run 10 rounds
    for round_num in range(1, 11):
        print(f"Running round {round_num}/10...")
        match_result = run_match(round_num)
        results.append(match_result)
        
        print(f"Round {round_num} complete:")
        print(f"  Rule-based agents total: {match_result['rule_based_total']}")
        print(f"  Wolf agents total: {match_result['wolf_total']}")
        if match_result['winner']:
            print(f"  Winner: {match_result['winner']}")
        print()
    
    # Save results to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"match_results_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = [
            'round', 
            'rule_based_agent_0_score', 
            'wolf_0_score',
            'rule_based_agent_1_score',
            'wolf_1_score',
            'rule_based_total',
            'wolf_total',
            'winner'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print("-" * 50)
    print(f"Results saved to {csv_filename}")
    
    # Calculate statistics
    rule_based_wins = sum(1 for r in results if r['winner'] == 'rule_based_agent')
    wolf_wins = sum(1 for r in results if r['winner'] == 'wolf')
    draws = sum(1 for r in results if r['winner'] == 'draw')
    
    total_rule_based_score = sum(r['rule_based_total'] for r in results)
    total_wolf_score = sum(r['wolf_total'] for r in results)
    
    print("\nSummary Statistics:")
    print(f"  Rule-based agent wins: {rule_based_wins}")
    print(f"  Wolf agent wins: {wolf_wins}")
    print(f"  Draws: {draws}")
    print(f"  Total rule-based score: {total_rule_based_score}")
    print(f"  Total wolf score: {total_wolf_score}")
    print(f"  Average rule-based score per round: {total_rule_based_score/10:.1f}")
    print(f"  Average wolf score per round: {total_wolf_score/10:.1f}")

if __name__ == "__main__":
    main()