import re
from collections import defaultdict

def analyze_log_file(log_file="logs/game.log", last_n_lines=1000):
    """Analyze the game log to determine winners"""
    
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    # Get last N lines
    recent_lines = lines[-last_n_lines:] if len(lines) > last_n_lines else lines
    
    rounds = []
    current_round = None
    agents_in_round = set()
    deaths_in_round = []
    scores = defaultdict(int)
    
    for line in recent_lines:
        # Detect round start
        if "STARTING ROUND" in line:
            if current_round:
                rounds.append({
                    'round': current_round,
                    'agents': list(agents_in_round),
                    'deaths': deaths_in_round,
                    'survivors': list(agents_in_round - set(deaths_in_round))
                })
            match = re.search(r'ROUND #(\d+)', line)
            if match:
                current_round = int(match.group(1))
                agents_in_round = set()
                deaths_in_round = []
        
        # Detect agents
        if "Agent <" in line and "chose action" in line:
            match = re.search(r'Agent <([^>]+)>', line)
            if match:
                agents_in_round.add(match.group(1))
        
        # Detect deaths
        if "killed" in line.lower() or "died" in line.lower():
            match = re.search(r'<([^>]+)>', line)
            if match:
                agent = match.group(1)
                deaths_in_round.append(agent)
                print(f"Death detected: {agent}")
        
        # Detect scores
        if "score" in line.lower():
            match = re.search(r'([^:]+).*score[:\s]+(\d+)', line, re.IGNORECASE)
            if match:
                agent = match.group(1).strip()
                score = int(match.group(2))
                scores[agent] = score
        
        # Round wrap up
        if "WRAPPING UP ROUND" in line and current_round:
            rounds.append({
                'round': current_round,
                'agents': list(agents_in_round),
                'deaths': deaths_in_round,
                'survivors': list(agents_in_round - set(deaths_in_round))
            })
            current_round = None
    
    # Analyze results
    print("\n=== MATCH ANALYSIS ===")
    print(f"Total rounds analyzed: {len(rounds)}")
    
    totoro_survivals = 0
    rule_based_survivals = 0
    totoro_rounds_won = 0
    rule_based_rounds_won = 0
    
    for r in rounds:
        print(f"\nRound {r['round']}:")
        print(f"  Participants: {', '.join(r['agents'])}")
        print(f"  Deaths: {', '.join(r['deaths']) if r['deaths'] else 'None'}")
        print(f"  Survivors: {', '.join(r['survivors']) if r['survivors'] else 'None'}")
        
        # Count survivors by team
        totoro_alive = sum(1 for s in r['survivors'] if 'totoro' in s)
        rule_based_alive = sum(1 for s in r['survivors'] if 'rule_based' in s)
        
        if totoro_alive > rule_based_alive:
            print(f"  Round Winner: TOTORO TEAM ({totoro_alive} vs {rule_based_alive})")
            totoro_rounds_won += 1
        elif rule_based_alive > totoro_alive:
            print(f"  Round Winner: RULE-BASED TEAM ({rule_based_alive} vs {totoro_alive})")
            rule_based_rounds_won += 1
        else:
            print(f"  Round Result: DRAW ({totoro_alive} vs {rule_based_alive})")
        
        totoro_survivals += totoro_alive
        rule_based_survivals += rule_based_alive
    
    print("\n=== FINAL STATISTICS ===")
    print(f"Totoro rounds won: {totoro_rounds_won}/{len(rounds)}")
    print(f"Rule-based rounds won: {rule_based_rounds_won}/{len(rounds)}")
    print(f"Draws: {len(rounds) - totoro_rounds_won - rule_based_rounds_won}/{len(rounds)}")
    print(f"Total Totoro survivals: {totoro_survivals}")
    print(f"Total Rule-based survivals: {rule_based_survivals}")
    
    if scores:
        print("\n=== SCORES ===")
        for agent, score in scores.items():
            print(f"{agent}: {score}")
    
    win_rate = (totoro_rounds_won / len(rounds) * 100) if rounds else 0
    print(f"\nTotoro Win Rate: {win_rate:.1f}%")
    
    return win_rate

if __name__ == "__main__":
    win_rate = analyze_log_file()
    
    if win_rate >= 50:
        print("\nSUCCESS! Target of 50% achieved!")
    else:
        print(f"\nNeed {50-win_rate:.1f}% more improvement to reach target")