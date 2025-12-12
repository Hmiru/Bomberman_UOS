from collections import deque
from random import shuffle

import numpy as np

import settings as s


def look_for_targets(free_space, start, targets, logger=None):
    """Find direction of closest target that can be reached via free tiles.

    Performs a breadth-first search of the reachable free tiles until a target is encountered.
    If no target can be reached, the path that takes the agent closest to any target is chosen.

    Args:
        free_space: Boolean numpy array. True for free tiles and False for obstacles.
        start: the coordinate from which to begin the search.
        targets: list or array holding the coordinates of all target tiles.
        logger: optional logger object for debugging.
    Returns:
        coordinate of first step towards closest target or towards tile closest to any target.
    """
    if len(targets) == 0: return None

    frontier = [start]
    parent_dict = {start: start}
    dist_so_far = {start: 0}
    best = start
    best_dist = np.sum(np.abs(np.subtract(targets, start)), axis=1).min()

    while len(frontier) > 0:
        current = frontier.pop(0)
        # Find distance from current position to all targets, track closest
        d = np.sum(np.abs(np.subtract(targets, current)), axis=1).min()
        if d + dist_so_far[current] <= best_dist:
            best = current
            best_dist = d + dist_so_far[current]
        if d == 0:
            # Found path to a target's exact position, mission accomplished!
            best = current
            break
        # Add unexplored free neighboring tiles to the queue in a random order
        x, y = current
        neighbors = [(x, y) for (x, y) in [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)] if free_space[x, y]]
        shuffle(neighbors)
        for neighbor in neighbors:
            if neighbor not in parent_dict:
                frontier.append(neighbor)
                parent_dict[neighbor] = current
                dist_so_far[neighbor] = dist_so_far[current] + 1
    if logger: logger.debug(f'Suitable target found at {best}')
    # Determine the first step towards the best found target tile
    current = best
    while True:
        if parent_dict[current] == start: return current
        current = parent_dict[current]


def setup(self):
    """Called once before a set of games to initialize data structures etc.

    The 'self' object passed to this method will be the same in all other
    callback methods. You can assign new properties (like bomb_history below)
    here or later on and they will be persistent even across multiple games.
    You can also use the self.logger object at any time to write to the log
    file for debugging (see https://docs.python.org/3.7/library/logging.html).
    """
    self.logger.debug('Successfully entered setup code')
    np.random.seed()
    # Fixed length FIFO queues to avoid repeating the same actions
    self.bomb_history = deque([], 5)
    self.coordinate_history = deque([], 20)
    # While this timer is positive, agent will not hunt/attack opponents
    self.ignore_others_timer = 0
    self.current_round = 0


def reset_self(self):
    self.bomb_history = deque([], 5)
    self.coordinate_history = deque([], 20)
    # While this timer is positive, agent will not hunt/attack opponents
    self.ignore_others_timer = 0


def act(self, game_state):
    """
    Called each game step to determine the agent's next action.

    You can find out about the state of the game environment via game_state,
    which is a dictionary. Consult 'get_state_for_agent' in environment.py to see
    what it contains.
    """
    self.logger.info('Picking action according to rule set')
    # Check if we are in a different round
    if game_state["round"] != self.current_round:
        reset_self(self)
        self.current_round = game_state["round"]
    
    # Gather information about the game state
    arena = game_state['field']
    my_name, score, bombs_left, (x, y) = game_state['self']
    bombs = game_state['bombs']
    bomb_xys = [xy for (xy, t) in bombs]
    coins = game_state['coins']
    
    # ROLE ASSIGNMENT: Attacker (wolf_0) vs Lurer (wolf_1)
    is_attacker = my_name.endswith('_0')
    role = "ATTACKER" if is_attacker else "LURER"
    self.logger.info(f'Agent {my_name} acting as {role}')
    
    # TEAM RECOGNITION FEATURE
    # Identify team prefix from agent name (e.g., "wolf_0", "wolf_1" -> team "wolf")
    team_prefix = "wolf"  # Our team name
    
    # Separate teammates and enemies based on name prefix
    teammates = []
    enemies = []
    all_others = []
    
    for (n, s, b, xy) in game_state['others']:
        # Check if this agent is on our team
        if team_prefix in n:
            teammates.append((n, s, b, xy))
            self.logger.debug(f'Teammate detected: {n} at {xy}')
        else:
            enemies.append(xy)
            self.logger.debug(f'Enemy detected: {n} at {xy}')
        all_others.append(xy)
    
    # Extract teammate positions for collision avoidance
    teammate_positions = [xy for (n, s, b, xy) in teammates]
    
    # Log team information
    self.logger.info(f'Agent {my_name}: {len(teammates)} teammates, {len(enemies)} enemies')
    
    # ENDGAME SCENARIOS
    # Scenario 1: Only one wolf remains (no teammates) - act like rule_based
    if len(teammates) == 0:
        # Single survivor mode - both roles act normally
        self.logger.info(f'{role} {my_name}: Last wolf standing, switching to standard mode')
        # Continue with normal rule_based logic (no special behavior)
    
    # Scenario 2: Two wolves remain with enemies - both hunt enemies
    elif len(enemies) > 0 and len(teammates) > 0:
        # Both wolves should hunt enemies aggressively
        if not is_attacker:
            # LURER also becomes aggressive in endgame with enemies
            self.logger.info(f'ENDGAME: LURER {my_name} switching to aggressive mode')
            # Will use normal target prioritization but be more aggressive
    
    # Scenario 3: Only teammates remain (no enemies) - score-based sacrifice
    elif len(enemies) == 0 and len(teammates) > 0:
        # Compare scores to determine who sacrifices
        my_score = score  # My score from game_state
        
        # Find teammate's score
        teammate_score = -1
        teammate_name = None
        teammate_pos = None
        for n, s, b, xy in teammates:
            teammate_score = s
            teammate_name = n
            teammate_pos = xy
            break
        
        self.logger.info(f'ENDGAME: {my_name} (score: {my_score}) vs {teammate_name} (score: {teammate_score})')
        
        # Higher score hunts, lower score sacrifices
        if my_score > teammate_score:
            # I have higher score - hunt teammate
            self.logger.info(f'ENDGAME: {my_name} has higher score ({my_score} > {teammate_score}), hunting {teammate_name}')
            if teammate_pos:
                enemies.append(teammate_pos)
                # Continue with normal logic to hunt
        elif my_score < teammate_score:
            # I have lower score - sacrifice
            self.logger.info(f'ENDGAME: {my_name} has lower score ({my_score} < {teammate_score}), sacrificing')
            return 'WAIT'  # Just wait to be eliminated
        else:
            # Tied score - use role as tiebreaker (ATTACKER sacrifices)
            if is_attacker:
                self.logger.info(f'ENDGAME: Tied score, ATTACKER {my_name} sacrificing')
                return 'WAIT'
            else:
                self.logger.info(f'ENDGAME: Tied score, LURER {my_name} hunting')
                if teammate_pos:
                    enemies.append(teammate_pos)
    
    # Calculate bomb danger map
    bomb_map = np.ones(arena.shape) * 5
    for (xb, yb), t in bombs:
        for (i, j) in [(xb + h, yb) for h in range(-3, 4)] + [(xb, yb + h) for h in range(-3, 4)]:
            if (0 < i < bomb_map.shape[0]) and (0 < j < bomb_map.shape[1]):
                bomb_map[i, j] = min(bomb_map[i, j], t)

    # If agent has been in the same location three times recently, it's a loop
    if self.coordinate_history.count((x, y)) > 2:
        self.ignore_others_timer = 5
    else:
        self.ignore_others_timer -= 1
    self.coordinate_history.append((x, y))

    # Check which moves make sense at all
    directions = [(x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    valid_tiles, valid_actions = [], []
    for d in directions:
        if ((arena[d] == 0) and
                (game_state['explosion_map'][d] < 1) and
                (bomb_map[d] > 0) and
                (not d in all_others) and  # Avoid all other agents
                (not d in bomb_xys)):
            valid_tiles.append(d)
    
    if (x - 1, y) in valid_tiles: valid_actions.append('LEFT')
    if (x + 1, y) in valid_tiles: valid_actions.append('RIGHT')
    if (x, y - 1) in valid_tiles: valid_actions.append('UP')
    if (x, y + 1) in valid_tiles: valid_actions.append('DOWN')
    if (x, y) in valid_tiles: valid_actions.append('WAIT')
    # Disallow the BOMB action if agent dropped a bomb in the same spot recently
    if (bombs_left > 0) and (x, y) not in self.bomb_history: valid_actions.append('BOMB')
    self.logger.debug(f'Valid actions: {valid_actions}')

    # Collect basic action proposals in a queue
    # Later on, the last added action that is also valid will be chosen
    action_ideas = ['UP', 'DOWN', 'LEFT', 'RIGHT']
    shuffle(action_ideas)

    # Compile a list of 'targets' the agent should head towards based on role
    cols = range(1, arena.shape[0] - 1)
    rows = range(1, arena.shape[0] - 1)
    dead_ends = [(x, y) for x in cols for y in rows if (arena[x, y] == 0)
                 and ([arena[x + 1, y], arena[x - 1, y], arena[x, y + 1], arena[x, y - 1]].count(0) == 1)]
    crates = [(x, y) for x in cols for y in rows if (arena[x, y] == 1)]
    
    # ROLE-BASED TARGET PRIORITIZATION
    # Check if in aggressive endgame mode (2 wolves + enemies remain)
    aggressive_endgame = len(enemies) > 0 and len(teammates) == 1  # Exactly 2 wolves, some enemies
    
    if is_attacker or (not is_attacker and len(teammates) == 0):
        # ATTACKER: Always hunt enemies
        # OR single wolf survivor: act like attacker
        targets = []
        if enemies:
            targets = enemies.copy()  # Enemies are top priority
            self.logger.debug(f'{role} {my_name}: Hunting {len(enemies)} enemies')
        else:
            # No enemies, help with crates
            targets = crates[:5] + dead_ends[:3]
            if coins:
                targets.extend(coins)  # Also collect coins if available
    elif not is_attacker and aggressive_endgame:
        # LURER in aggressive endgame: Also hunt enemies
        targets = []
        if enemies:
            targets = enemies.copy()  # Switch to hunting enemies
            self.logger.debug(f'LURER {my_name}: AGGRESSIVE MODE - Hunting {len(enemies)} enemies')
        if coins and len(targets) < 3:
            targets.extend(coins)  # Still collect coins if easy
        targets.extend(crates[:3])
    else:
        # LURER: Normal mode - Focus on collecting coins
        targets = []
        if coins:
            targets = coins.copy()  # Coins are top priority
            self.logger.debug(f'LURER {my_name}: Collecting {len(coins)} coins')
        else:
            # No coins, work on crates to find more
            targets = crates[:5] + dead_ends[:2]
        
        # Lurer avoids enemies unless cornered
        if self.ignore_others_timer > 0 or len(coins) > 0:
            # Don't add enemies to targets
            pass
        elif len(crates) + len(coins) == 0:
            # Only hunt if no other options
            targets.extend(enemies)

    # Exclude targets that are currently occupied by a bomb
    targets = [targets[i] for i in range(len(targets)) if targets[i] not in bomb_xys]

    # Take a step towards the most immediately interesting target
    free_space = arena == 0
    
    # Mark teammate positions as obstacles to avoid them during pathfinding
    # BUT in endgame, LURER should not avoid ATTACKER
    is_endgame = len(enemies) > 0 and any(xy in teammate_positions for xy in enemies)
    if not (is_endgame and not is_attacker):
        for tp in teammate_positions:
            if 0 <= tp[0] < free_space.shape[0] and 0 <= tp[1] < free_space.shape[1]:
                free_space[tp] = False
    
    # Also avoid enemies when in ignore mode
    if self.ignore_others_timer > 0:
        for o in enemies:
            free_space[o] = False
    
    d = look_for_targets(free_space, (x, y), targets, self.logger)
    if d == (x, y - 1): action_ideas.append('UP')
    if d == (x, y + 1): action_ideas.append('DOWN')
    if d == (x - 1, y): action_ideas.append('LEFT')
    if d == (x + 1, y): action_ideas.append('RIGHT')
    if d is None:
        self.logger.debug('All targets gone, nothing to do anymore')
        action_ideas.append('WAIT')

    # Add proposal to drop a bomb if at dead end
    if (x, y) in dead_ends:
        action_ideas.append('BOMB')
    
    # Role-based bombing strategy
    if len(enemies) > 0:
        min_enemy_dist = min(abs(xy[0] - x) + abs(xy[1] - y) for xy in enemies)
        
        # Check game state
        aggressive_endgame = len(enemies) > 0 and len(teammates) == 1
        single_survivor = len(teammates) == 0
        
        if is_attacker or single_survivor:
            # ATTACKER or single survivor: Aggressive bombing
            if min_enemy_dist <= 1:
                action_ideas.append('BOMB')
                self.logger.info(f'{role} {my_name}: Enemy adjacent, bombing!')
        else:
            # LURER: Context-dependent bombing
            if min_enemy_dist <= 1:
                # Check if this is sacrifice endgame (targeting teammate)
                is_sacrifice_endgame = any(xy in teammate_positions for xy in enemies)
                
                if is_sacrifice_endgame:
                    action_ideas.append('BOMB')
                    self.logger.info(f'LURER {my_name}: Eliminating ATTACKER teammate!')
                elif aggressive_endgame:
                    # Aggressive mode: bomb enemies like attacker
                    action_ideas.append('BOMB')
                    self.logger.info(f'LURER {my_name}: AGGRESSIVE - Bombing enemy!')
                elif len(valid_actions) <= 2:
                    # Normal mode: only bomb if cornered
                    action_ideas.append('BOMB')
                    self.logger.info(f'LURER {my_name}: Cornered by enemy, defensive bomb!')
    
    # Add proposal to drop a bomb if arrived at target and touching crate
    if d == (x, y) and ([arena[x + 1, y], arena[x - 1, y], arena[x, y + 1], arena[x, y - 1]].count(1) > 0):
        action_ideas.append('BOMB')

    # Add proposal to run away from any nearby bomb about to blow
    for (xb, yb), t in bombs:
        if (xb == x) and (abs(yb - y) < 4):
            # Run away
            if (yb > y): action_ideas.append('UP')
            if (yb < y): action_ideas.append('DOWN')
            # If possible, turn a corner
            action_ideas.append('LEFT')
            action_ideas.append('RIGHT')
        if (yb == y) and (abs(xb - x) < 4):
            # Run away
            if (xb > x): action_ideas.append('LEFT')
            if (xb < x): action_ideas.append('RIGHT')
            # If possible, turn a corner
            action_ideas.append('UP')
            action_ideas.append('DOWN')
    
    # Try random direction if directly on top of a bomb
    for (xb, yb), t in bombs:
        if xb == x and yb == y:
            action_ideas.extend(action_ideas[:4])

    # Pick last action added to the proposals list that is also valid
    while len(action_ideas) > 0:
        a = action_ideas.pop()
        if a in valid_actions:
            # Keep track of chosen action for cycle detection
            if a == 'BOMB':
                self.bomb_history.append((x, y))
            
            # Log the chosen action with team context
            self.logger.info(f'Agent {my_name} ({role}) choosing action: {a}')
            return a