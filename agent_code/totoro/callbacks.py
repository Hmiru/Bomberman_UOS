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
    
def act(self, game_state: dict):
    # 1. 정보 수집 (변수 정리)
    arena = game_state['field']
    _, score, bombs_left, (x, y) = game_state['self']
    bombs = game_state['bombs']
    bomb_xys = [xy for (xy, t) in bombs]
    others = [xy for (n, s, b, xy) in game_state['others']]
    coins = game_state['coins']
    
    # 2. 내 이름 및 팀 확인
    my_name = game_state['self'][0]
    # 팀 이름이 포함되지 않은 에이전트만 적(enemies)으로 간주
    team_prefix = "totoro" 
    enemies = [xy for (n, s, b, xy) in game_state['others'] if team_prefix not in n]

    # 3. 안전한 이동 방향 계산 (생존 본능) - rule_based_agent 로직 차용
    bomb_map = np.ones(arena.shape) * 5
    for (xb, yb), t in bombs:
        for (i, j) in [(xb + h, yb) for h in range(-3, 4)] + [(xb, yb + h) for h in range(-3, 4)]:
            if (0 < i < bomb_map.shape[0]) and (0 < j < bomb_map.shape[1]):
                bomb_map[i, j] = min(bomb_map[i, j], t)

    directions = [(x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    valid_tiles, valid_actions = [], []
    for d in directions:
        if ((arena[d] == 0) and
                (game_state['explosion_map'][d] < 1) and
                (bomb_map[d] > 0) and
                (not d in others) and
                (not d in bomb_xys)):
            valid_tiles.append(d)

    if (x - 1, y) in valid_tiles: valid_actions.append('LEFT')
    if (x + 1, y) in valid_tiles: valid_actions.append('RIGHT')
    if (x, y - 1) in valid_tiles: valid_actions.append('UP')
    if (x, y + 1) in valid_tiles: valid_actions.append('DOWN')
    if (x, y) in valid_tiles: valid_actions.append('WAIT')
    
    # 폭탄 설치 가능 여부 체크
    if (bombs_left > 0) and (x, y) not in self.bomb_history: 
        valid_actions.append('BOMB')

    # 4. 역할 분담
    if my_name.endswith('_0'):
        role = 'KILLER'
        # 킬러 로직 호출 (필요한 정보를 인자로 넘겨줌)
        action = act_as_killer(self, game_state, valid_actions, enemies, bomb_xys)
    elif my_name.endswith('_1'):
        role = 'LURER'
        # 미끼 로직 호출
        action = act_as_lurer(self, game_state, valid_actions, enemies, bomb_xys)
    
    self.logger.info(f"I am {my_name}, acting as {role}. Chosen action: {action}")
    return action

def is_safe_to_bomb(game_state, x, y):
    arena = game_state['field']
    bombs = game_state['bombs']
    # 현재 위치에 폭탄이 있다고 가정하고 시뮬레이션
    simulated_bombs = bombs + [((x, y), 3)] 
    
    # 도망갈 수 있는지 탐색 (BFS)
    # 4스텝(폭발 시간) 내에 안전지대(폭발 범위 밖)로 갈 수 있는가?
    queue = deque([(x, y, 0)]) # x, y, steps
    visited = set([(x, y)])
    
    while queue:
        cx, cy, step = queue.popleft()
        
        # 4스텝 이상 도망갔으면 일단 생존 가능성 높음 (간단한 판별)
        # 더 정확히는 해당 위치가 폭발 범위가 아니어야 함
        if step >= 4: 
            return True
            
        # 4방향 탐색
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            # 맵 범위 안이고, 벽/상자가 아니고, 방문 안 했고
            if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and 
                arena[nx, ny] == 0 and (nx, ny) not in visited):
                
                # 다른 폭탄의 예비 폭발 구역인지 체크는 생략 (복잡도 때문)
                # 단순히 이동 가능하면 큐에 추가
                visited.add((nx, ny))
                queue.append((nx, ny, step + 1))
                
    # 큐가 빌 때까지 4스텝 이상 못 가면 위험
    return False

def act_as_killer(self, game_state, valid_actions, enemies, bomb_xys):
    action_ideas = ['UP', 'DOWN', 'LEFT', 'RIGHT']
    shuffle(action_ideas)
    
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    coins = game_state['coins']
    
    # 폭탄 위치와 적 위치는 장애물로 간주 (안전한 길찾기 위해)
    free_space = arena == 0
    for bx, by in bomb_xys:
        free_space[bx, by] = False
    
    # -----------------------------------------------------------
    # [1. 이동 목표(d) 설정]
    # 적 -> 코인 순서로만 이동. (상자는 이동 목표가 아니라 파괴 목표임)
    # -----------------------------------------------------------
    
    # 1순위: 적 추격
    active_enemies = [e for e in enemies if e not in bomb_xys]
    d = look_for_targets(free_space, (x, y), active_enemies, self.logger)
    
    # 2순위: 코인 (적이 멀거나 없으면 파밍)
    if d is None:
        d = look_for_targets(free_space, (x, y), coins, self.logger)

    # -----------------------------------------------------------
    # [2. 스택 쌓기 (LIFO: 나중에 넣을수록 중요함)]
    # 순서: 랜덤 < 이동(d) < 폭탄설치 < 생존회피
    # -----------------------------------------------------------

    # (1) 목표를 향한 이동
    if d == (x, y - 1): action_ideas.append('UP')
    if d == (x, y + 1): action_ideas.append('DOWN')
    if d == (x - 1, y): action_ideas.append('LEFT')
    if d == (x + 1, y): action_ideas.append('RIGHT')
    if d is None: action_ideas.append('WAIT') # 갈 곳 없으면 대기 (하지만 아래 BOMB에 덮어씌워질 수 있음)

    # (2) 폭탄 설치 판단 (공격 또는 탈출)
    should_bomb = False
    
    # 상황 A: 적을 잡을 수 있을 때 (거리 2칸 이내)
    if enemies:
        dist_to_enemy = min([abs(ex - x) + abs(ey - y) for ex, ey in enemies])
        if dist_to_enemy <= 2:
            should_bomb = True
            
    # 상황 B: [핵심 수정] 갈 곳이 없는데(d is None) 바로 옆에 상자가 있을 때 (갇힘 탈출)
    if d is None:
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]:
                # 내 옆에 상자(1)가 있으면 폭파
                if arena[nx, ny] == 1:
                    should_bomb = True
                    break

    # 폭탄 설치 실행 (안전 확인 필수)
    if should_bomb and 'BOMB' in valid_actions:
        if is_safe_to_bomb(game_state, (x, y)):
             action_ideas.append('BOMB') # WAIT보다 나중에 넣어서 덮어씌움!

    # (3) [생존] 최우선 회피 (가장 마지막에 넣어 최우선 실행)
    escape_moves = get_escape_actions(x, y, game_state['bombs'])
    if escape_moves:
        action_ideas.extend(escape_moves)
    
    # 최종 행동 결정
    while len(action_ideas) > 0:
        a = action_ideas.pop()
        if a in valid_actions:
            if a == 'BOMB': self.bomb_history.append((x, y))
            return a
            
    return 'WAIT'

def is_safe_to_bomb(game_state, my_pos):
    """
    수정된 버전: (x, y) 튜플을 하나의 인자(my_pos)로 받도록 변경
    """
    x, y = my_pos # [중요] 여기서 튜플을 풉니다
    arena = game_state['field']
    bombs = game_state['bombs']
    
    # 1. 이미 위험한 자리면 설치 불가 (연쇄 폭발 방지)
    current_mask = get_blast_mask(arena, bombs)
    if current_mask[x, y]: return False

    # 2. 미래 시뮬레이션
    simulated_bombs = bombs + [((x, y), 4)] # BOMB_TIMER default 4
    future_mask = get_blast_mask(arena, simulated_bombs)
    
    # BFS로 안전지대 도달 가능 여부 확인
    queue = deque([(x, y, 0)])
    visited = set([(x, y)])
    
    while queue:
        cx, cy, step = queue.popleft()
        
        # 4초(폭발시간) 안에 안전지대(폭발 범위 밖)로 나갈 수 있으면 OK
        if not future_mask[cx, cy]: return True
        
        if step >= 4: continue # 4초 지나도 못 나갔으면 의미 없음

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and 
                arena[nx, ny] == 0 and (nx, ny) not in visited):
                
                # 폭탄 위는 지나갈 수 없음
                if is_blocked_by_bomb((nx, ny), bombs): continue
                
                visited.add((nx, ny))
                queue.append((nx, ny, step + 1))
                
    return False

def act_as_lurer(self, game_state, valid_actions, enemies, bomb_xys):
    # 기본 이동 아이디어
    action_ideas = ['UP', 'DOWN', 'LEFT', 'RIGHT']
    shuffle(action_ideas)
    
    # 정보 추출
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    coins = game_state['coins']

    # [전략] 미끼는 '코인'과 '막다른 길(안전지대)'을 추적함. 적은 피함.
    cols = range(1, arena.shape[0] - 1)
    rows = range(1, arena.shape[0] - 1)
    crates = [(r, c) for r in cols for c in rows if (arena[r, c] == 1)]
    dead_ends = [(r, c) for r in cols for c in rows if (arena[r, c] == 0)
                 and ([arena[r+1,c], arena[r-1,c], arena[r,c+1], arena[r,c-1]].count(0) == 1)]
    
    targets = coins + dead_ends
    targets = [t for t in targets if t not in bomb_xys]

    # 타겟 이동
    free_space = arena == 0
    # 1. 코인 탐색
    d = look_for_targets(free_space, (x, y), coins, self.logger)
    # 2. 코인 경로가 없으면 -> 상자 탐색
    if d is None:
        d = look_for_targets(free_space, (x, y), crates, self.logger)
    # 3. 상자도 없으면 안전한 곳으로
    if d is None:
        dead_ends = [(r, c) for r in cols for c in rows if (arena[r, c] == 0)
                     and ([arena[r+1,c], arena[r-1,c], arena[r,c+1], arena[r,c-1]].count(0) == 1)]
        d = look_for_targets(free_space, (x, y), dead_ends, self.logger)
    if d == (x, y - 1): action_ideas.append('UP')
    if d == (x, y + 1): action_ideas.append('DOWN')
    if d == (x - 1, y): action_ideas.append('LEFT')
    if d == (x + 1, y): action_ideas.append('RIGHT')
    if d is None: action_ideas.append('WAIT')

    if ([arena[x+1,y], arena[x-1,y], arena[x,y+1], arena[x,y-1]].count(1) > 0):
        action_ideas.append('BOMB')

    # [생존] 폭탄 회피
    action_ideas.extend(get_escape_actions(x, y, game_state['bombs']))

    # 유효한 행동 선택
    while len(action_ideas) > 0:
        a = action_ideas.pop()
        if a in valid_actions:
            if a == 'BOMB': self.bomb_history.append((x, y))
            return a
    return 'WAIT'

def get_escape_actions(x, y, bombs):
    # 폭탄이 터질 것 같으면 도망가는 행동 리스트 반환
    ideas = []
    for (xb, yb), t in bombs:
        if (xb == x) and (abs(yb - y) < 4):
            if (yb > y): ideas.append('UP')
            if (yb < y): ideas.append('DOWN')
            ideas.append('LEFT')
            ideas.append('RIGHT')
        if (yb == y) and (abs(xb - x) < 4):
            if (xb > x): ideas.append('LEFT')
            if (xb < x): ideas.append('RIGHT')
            ideas.append('UP')
            ideas.append('DOWN')
    return ideas

def get_blast_mask(arena, bombs):
    """
    현재 설치된 폭탄들이 터질 정확한 위치를 계산합니다 (벽에 막히는 것 고려).
    True: 폭발 위험 있음 / False: 안전함
    """
    mask = np.zeros_like(arena, dtype=bool)
    
    for (bx, by), t in bombs:
        mask[bx, by] = True # 폭탄 위치 자체는 위험
        
        # 4방향으로 화력(3칸) 퍼짐
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            for i in range(1, 4): # 1~3칸
                nx, ny = bx + (dx * i), by + (dy * i)
                
                # 맵 밖이면 중단
                if not (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]):
                    break
                
                # 벽(-1)을 만나면 화염이 막힘 -> 즉시 중단 (벽 뒤는 안전)
                if arena[nx, ny] == -1:
                    break
                
                # 폭발 범위 마킹
                mask[nx, ny] = True
    return mask