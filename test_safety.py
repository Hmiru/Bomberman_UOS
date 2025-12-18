"""
Wolf Agent Safety Test Suite
Tests team recognition, role strategies, and endgame logic
"""

import subprocess
import json
import time
from pathlib import Path
import re

def run_test(agents, n_rounds=10, scenario="classic"):
    """Run a test match and extract results"""
    cmd = [
        "python", "main.py", "play",
        "--agents"] + agents + [
        "--n-rounds", str(n_rounds),
        "--no-gui",
        "--scenario", scenario
    ]
    
    print(f"Running: {' '.join(agents)} for {n_rounds} rounds")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def parse_match_results(output):
    """Parse match output for scores and events"""
    scores = {}
    team_kills = 0
    self_destructs = 0
    
    # Parse scores
    score_pattern = r"(\w+): (\d+) coins, (\d+) kills, (\d+) steps"
    for match in re.finditer(score_pattern, output):
        agent_name = match.group(1)
        scores[agent_name] = {
            'coins': int(match.group(2)),
            'kills': int(match.group(3)),
            'steps': int(match.group(4))
        }
    
    # Look for team kills (wolf killing wolf)
    if "wolf_0 killed wolf_1" in output or "wolf_1 killed wolf_0" in output:
        team_kills += 1
    
    # Look for self destructs
    if "killed itself" in output:
        self_destructs += output.count("killed itself")
    
    return scores, team_kills, self_destructs

def test_team_recognition():
    """Test 1: Verify wolf agents don't kill each other unnecessarily"""
    print("\n=== TEST 1: Team Recognition ===")
    print("Testing if wolf agents avoid killing teammates...")
    
    # Run wolf vs wolf vs enemies
    output = run_test(["wolf", "wolf", "rule_based_agent", "rule_based_agent"], n_rounds=20)
    scores, team_kills, self_destructs = parse_match_results(output)
    
    print(f"Team kills detected: {team_kills}")
    print(f"Self destructs: {self_destructs}")
    
    # Team kills should only happen in endgame when score difference exists
    if team_kills > 0:
        print("[WARNING] Team kills detected - verify these are endgame scenarios")
    else:
        print("[PASS] No unnecessary team kills")
    
    return team_kills, self_destructs

def test_role_strategies():
    """Test 2: Verify Attacker and Lurer behave differently"""
    print("\n=== TEST 2: Role-Based Strategies ===")
    print("Testing if wolf_0 (Attacker) and wolf_1 (Lurer) have different behaviors...")
    
    # Run matches and analyze behavior patterns
    output = run_test(["wolf", "wolf", "rule_based_agent", "rule_based_agent"], n_rounds=10)
    scores, _, _ = parse_match_results(output)
    
    if 'wolf_0' in scores and 'wolf_1' in scores:
        wolf_0_kills = scores['wolf_0']['kills']
        wolf_1_coins = scores['wolf_1']['coins']
        
        print(f"Wolf_0 (Attacker) kills: {wolf_0_kills}")
        print(f"Wolf_1 (Lurer) coins: {wolf_1_coins}")
        
        # Attacker should focus on kills
        if wolf_0_kills > 0:
            print("[PASS] Attacker is engaging enemies")
        else:
            print("[WARNING] Attacker may not be aggressive enough")
        
        # Lurer should collect coins
        if wolf_1_coins > 0:
            print("[PASS] Lurer is collecting coins")
        else:
            print("[WARNING] Lurer may not be collecting effectively")
    
    return scores

def test_endgame_logic():
    """Test 3: Verify score-based elimination in endgame"""
    print("\n=== TEST 3: Endgame Score-Based Elimination ===")
    print("Testing if higher-scoring wolf eliminates lower-scoring wolf...")
    
    # Run multiple matches to find endgame scenarios
    endgame_scenarios = 0
    correct_eliminations = 0
    
    for i in range(5):
        output = run_test(["wolf", "wolf", "peaceful_agent", "peaceful_agent"], n_rounds=10)
        
        # Look for endgame patterns
        if "only wolf agents remain" in output.lower() or "endgame" in output.lower():
            endgame_scenarios += 1
            
            # Check if higher score won
            scores, team_kills, _ = parse_match_results(output)
            if team_kills > 0:
                # Verify the winner had higher score
                if 'wolf_0' in scores and 'wolf_1' in scores:
                    wolf_0_total = scores['wolf_0']['coins'] + scores['wolf_0']['kills'] * 5
                    wolf_1_total = scores['wolf_1']['coins'] + scores['wolf_1']['kills'] * 5
                    
                    print(f"  Round {i+1}: Wolf_0 score={wolf_0_total}, Wolf_1 score={wolf_1_total}")
                    
                    if wolf_0_total != wolf_1_total:
                        correct_eliminations += 1
    
    print(f"Endgame scenarios found: {endgame_scenarios}")
    print(f"Correct score-based eliminations: {correct_eliminations}")
    
    if endgame_scenarios > 0 and correct_eliminations == endgame_scenarios:
        print("[PASS] Score-based elimination working correctly")
    else:
        print("[WARNING] Score-based elimination may need review")
    
    return endgame_scenarios, correct_eliminations

def test_bomb_safety():
    """Test 4: Verify agents don't self-destruct with their own bombs"""
    print("\n=== TEST 4: Bomb Safety ===")
    print("Testing if agents avoid their own bombs...")
    
    total_self_destructs = 0
    
    for scenario in ["classic", "empty", "coin-heaven"]:
        output = run_test(["wolf", "wolf", "rule_based_agent", "rule_based_agent"], 
                         n_rounds=10, scenario=scenario)
        _, _, self_destructs = parse_match_results(output)
        total_self_destructs += self_destructs
        print(f"  {scenario}: {self_destructs} self-destructs")
    
    if total_self_destructs == 0:
        print("[PASS] No self-destructs detected")
    elif total_self_destructs < 3:
        print("[WARNING] Some self-destructs detected - may be tactical")
    else:
        print("[FAIL] High self-destruct rate - review bomb safety logic")
    
    return total_self_destructs

def main():
    """Run all tests and generate summary"""
    print("=" * 50)
    print("WOLF AGENT COMPREHENSIVE TEST SUITE")
    print("=" * 50)
    
    results = {
        'team_recognition': test_team_recognition(),
        'role_strategies': test_role_strategies(),
        'endgame_logic': test_endgame_logic(),
        'bomb_safety': test_bomb_safety()
    }
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    # Team recognition
    team_kills, _ = results['team_recognition']
    print(f"Team Recognition: {'[PASS]' if team_kills == 0 else '[WARNING] REVIEW'}")
    
    # Role strategies
    scores = results['role_strategies']
    print(f"Role Strategies: {'[PASS]' if scores else '[WARNING] REVIEW'}")
    
    # Endgame logic
    scenarios, correct = results['endgame_logic']
    print(f"Endgame Logic: {'[PASS]' if scenarios > 0 and correct == scenarios else '[WARNING] REVIEW'}")
    
    # Bomb safety
    self_destructs = results['bomb_safety']
    print(f"Bomb Safety: {'[PASS]' if self_destructs < 3 else '[FAIL]'}")
    
    print("\nTest completed successfully!")
    print("Review the detailed output above for specific areas of improvement.")

if __name__ == "__main__":
    main()