from collections import deque
from random import shuffle
import numpy as np
import settings as s

def look_for_targets(free_space, start, targets, logger=None):
    """Find direction of closest target that can be reached via free tiles."""
    if len(targets) == 0: 
        return None

    frontier = [start]
    parent_dict = {start: start}
    dist_so_far = {start: 0}
    best = start
    best_dist = np.sum(np.abs(np.subtract(targets, start)), axis=1).min()

    while len(frontier) > 0:
        current = frontier.pop(0)
        d = np.sum(np.abs(np.subtract(targets, current)), axis=1).min()
        if d + dist_so_far[current] <= best_dist:
            best = current
            best_dist = d + dist_so_far[current]
        if d == 0:
            best = current
            break
        x, y = current
        neighbors = [(x, y) for (x, y) in [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)] if free_space[x, y]]
        shuffle(neighbors)
        for neighbor in neighbors:
            if neighbor not in parent_dict:
                frontier.append(neighbor)
                parent_dict[neighbor] = current
                dist_so_far[neighbor] = dist_so_far[current] + 1
    
    if logger: 
        logger.debug(f'Suitable target found at {best}')
    
    current = best
    while True:
        if parent_dict[current] == start: 
            return current
        current = parent_dict[current]


def setup(self):
    """Initialize agent data structures."""
    self.logger.debug('Successfully entered setup code')
    np.random.seed()
    self.bomb_history = deque([], 5)
    self.coordinate_history = deque([], 20)
    self.current_round = 0
    self.last_bomb_time = 0
    self.coins_collected = 0
    self.enemies_killed = 0
    

def reset_self(self):
    """Reset agent state at the beginning of each round."""
    self.bomb_history = deque([], 5)
    self.coordinate_history = deque([], 20)
    self.last_bomb_time = 0
    self.coins_collected = 0
    self.enemies_killed = 0


def act(self, game_state: dict):
    """점수 최대화 중심 전략"""
    arena = game_state['field']
    _, my_score, bombs_left, (x, y) = game_state['self']
    bombs = game_state['bombs']
    bomb_xys = [xy for (xy, t) in bombs]
    others = [xy for (n, s, b, xy) in game_state['others']]
    coins = game_state['coins']
    explosion_map = game_state['explosion_map']
    step = game_state['step']
    
    # 팀 구분
    my_name = game_state['self'][0]
    team_prefix = "totoro" 
    enemies = [xy for (n, s, b, xy) in game_state['others'] if team_prefix not in n]
    enemy_scores = [s for (n, s, b, xy) in game_state['others'] if team_prefix not in n]
    
    # 안전 지역 계산
    bomb_map = calculate_bomb_danger(arena, bombs)
    
    # 긴급 회피가 필요한지 체크
    if bomb_map[x, y] <= 1 or explosion_map[x, y] > 0:
        action = emergency_escape_score_focused(x, y, arena, bomb_map, explosion_map, others, bomb_xys)
        if action:
            return action
    
    # 유효 행동 계산
    valid_actions = get_valid_actions(x, y, arena, explosion_map, bomb_map, others, bomb_xys, bombs_left)
    
    # 역할 결정: 점수 중심
    if my_name.endswith('_0'):
        return score_maximizer_strategy(self, game_state, valid_actions, enemies, coins, bomb_map, step)
    else:
        return support_scorer_strategy(self, game_state, valid_actions, enemies, coins, bomb_map, step)


def calculate_bomb_danger(arena, bombs):
    """폭탄 위험도 맵 계산"""
    bomb_map = np.ones(arena.shape) * 10
    for (xb, yb), t in bombs:
        for (i, j) in [(xb + h, yb) for h in range(-s.BOMB_POWER, s.BOMB_POWER+1)] + \
                      [(xb, yb + h) for h in range(-s.BOMB_POWER, s.BOMB_POWER+1)]:
            if (0 <= i < bomb_map.shape[0]) and (0 <= j < bomb_map.shape[1]):
                if check_explosion_path(arena, xb, yb, i, j):
                    bomb_map[i, j] = min(bomb_map[i, j], t)
    return bomb_map


def check_explosion_path(arena, x1, y1, x2, y2):
    """폭발이 도달할 수 있는지 확인"""
    if x1 == x2:
        y_min, y_max = min(y1, y2), max(y1, y2)
        for y in range(y_min, y_max + 1):
            if arena[x1, y] == -1:
                return False
    elif y1 == y2:
        x_min, x_max = min(x1, x2), max(x1, x2)
        for x in range(x_min, x_max + 1):
            if arena[x, y1] == -1:
                return False
    return True


def emergency_escape_score_focused(x, y, arena, bomb_map, explosion_map, others, bomb_xys):
    """점수 중심 긴급 탈출 - 더 공격적"""
    directions = [('UP', 0, -1), ('DOWN', 0, 1), ('LEFT', -1, 0), ('RIGHT', 1, 0)]
    best_actions = []
    
    for action, dx, dy in directions:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and 
            arena[nx, ny] == 0 and (nx, ny) not in others and 
            (nx, ny) not in bomb_xys and explosion_map[nx, ny] == 0):
            safety = bomb_map[nx, ny]
            best_actions.append((action, safety))
    
    if best_actions:
        best_actions.sort(key=lambda x: x[1], reverse=True)
        return best_actions[0][0]
    
    # 더 위험해도 이동 (점수를 위해 리스크 감수)
    for action, dx, dy in directions:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and 
            arena[nx, ny] == 0 and (nx, ny) not in others):
            return action
    
    return 'WAIT'


def get_valid_actions(x, y, arena, explosion_map, bomb_map, others, bomb_xys, bombs_left):
    """유효한 행동 리스트"""
    actions = []
    
    # 이동 가능한 방향
    for action, dx, dy in [('UP', 0, -1), ('DOWN', 0, 1), ('LEFT', -1, 0), ('RIGHT', 1, 0)]:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and
            arena[nx, ny] == 0 and explosion_map[nx, ny] == 0 and
            bomb_map[nx, ny] > 0 and (nx, ny) not in others and
            (nx, ny) not in bomb_xys):
            actions.append(action)
    
    # 대기 가능
    if explosion_map[x, y] == 0 and bomb_map[x, y] > 1:
        actions.append('WAIT')
    
    # 폭탄 설치 가능 (더 공격적으로)
    if bombs_left > 0:
        actions.append('BOMB')
    
    return actions


def score_maximizer_strategy(self, game_state, valid_actions, enemies, coins, bomb_map, step):
    """메인 점수 획득 전략"""
    arena = game_state['field']
    _, _, bombs_left, (x, y) = game_state['self']
    bombs = game_state['bombs']
    
    # 1순위: 코인 수집 (1점)
    if coins:
        action = collect_coins_aggressively(x, y, coins, arena, valid_actions)
        if action:
            self.logger.info(f"Collecting coin for score")
            return action
    
    # 2순위: 적 처치 기회 (5점)
    if enemies:
        action = hunt_enemies_for_score(self, x, y, enemies, arena, valid_actions, bombs_left, bomb_map, step)
        if action:
            return action
    
    # 3순위: 상자 파괴로 코인 생성
    action = destroy_crates_for_coins(self, x, y, arena, valid_actions, bombs_left, bomb_map, step)
    if action:
        return action
    
    # 4순위: 적 찾아다니기
    if enemies:
        action = seek_enemies(x, y, enemies, arena, valid_actions)
        if action:
            return action
    
    # 기본 이동
    return random_move(valid_actions)


def support_scorer_strategy(self, game_state, valid_actions, enemies, coins, bomb_map, step):
    """보조 점수 획득 전략"""
    arena = game_state['field']
    _, _, bombs_left, (x, y) = game_state['self']
    
    # 1순위: 코인 우선 수집
    if coins:
        action = collect_coins_aggressively(x, y, coins, arena, valid_actions)
        if action:
            self.logger.info(f"Support collecting coin")
            return action
    
    # 2순위: 상자 파괴
    action = destroy_crates_for_coins(self, x, y, arena, valid_actions, bombs_left, bomb_map, step)
    if action:
        return action
    
    # 3순위: 적이 가까우면 공격 참여
    if enemies:
        closest_enemy = min(enemies, key=lambda e: abs(e[0] - x) + abs(e[1] - y))
        dist = abs(closest_enemy[0] - x) + abs(closest_enemy[1] - y)
        if dist <= 3:
            action = hunt_enemies_for_score(self, x, y, [closest_enemy], arena, valid_actions, bombs_left, bomb_map, step)
            if action:
                return action
    
    # 4순위: 맵 탐색
    return explore_map(x, y, arena, valid_actions)


def collect_coins_aggressively(x, y, coins, arena, valid_actions):
    """공격적 코인 수집"""
    if not coins:
        return None
    
    # 가장 가까운 코인 찾기
    closest_coin = min(coins, key=lambda c: abs(c[0] - x) + abs(c[1] - y))
    
    # 직접 이동 시도
    dx = closest_coin[0] - x
    dy = closest_coin[1] - y
    
    if dx > 0 and 'RIGHT' in valid_actions:
        return 'RIGHT'
    elif dx < 0 and 'LEFT' in valid_actions:
        return 'LEFT'
    elif dy > 0 and 'DOWN' in valid_actions:
        return 'DOWN'
    elif dy < 0 and 'UP' in valid_actions:
        return 'UP'
    
    # BFS로 경로 찾기
    free_space = arena == 0
    direction = look_for_targets(free_space, (x, y), coins)
    if direction:
        if direction == (x, y - 1) and 'UP' in valid_actions:
            return 'UP'
        elif direction == (x, y + 1) and 'DOWN' in valid_actions:
            return 'DOWN'
        elif direction == (x - 1, y) and 'LEFT' in valid_actions:
            return 'LEFT'
        elif direction == (x + 1, y) and 'RIGHT' in valid_actions:
            return 'RIGHT'
    
    return None


def hunt_enemies_for_score(self, x, y, enemies, arena, valid_actions, bombs_left, bomb_map, step):
    """적 처치로 5점 획득"""
    if not enemies:
        return None
    
    closest_enemy = min(enemies, key=lambda e: abs(e[0] - x) + abs(e[1] - y))
    dist = abs(closest_enemy[0] - x) + abs(closest_enemy[1] - y)
    
    # 매우 가까우면 즉시 폭탄 (1-2칸)
    if dist <= 2 and bombs_left > 0 and 'BOMB' in valid_actions:
        # 최소한의 안전 체크만
        if can_escape_after_bomb(x, y, arena, bomb_map):
            self.logger.info(f"Bombing enemy for 5 points! Distance: {dist}")
            self.last_bomb_time = step
            return 'BOMB'
    
    # 3칸 거리에서도 폭탄 고려
    if dist == 3 and bombs_left > 0 and 'BOMB' in valid_actions:
        # 적이 나에게 오고 있을 가능성 고려
        if can_trap_enemy(x, y, closest_enemy, arena):
            self.logger.info(f"Trap bombing for enemy")
            self.last_bomb_time = step
            return 'BOMB'
    
    # 적에게 접근
    dx = closest_enemy[0] - x
    dy = closest_enemy[1] - y
    
    if abs(dx) > abs(dy):
        if dx > 0 and 'RIGHT' in valid_actions:
            return 'RIGHT'
        elif dx < 0 and 'LEFT' in valid_actions:
            return 'LEFT'
    else:
        if dy > 0 and 'DOWN' in valid_actions:
            return 'DOWN'
        elif dy < 0 and 'UP' in valid_actions:
            return 'UP'
    
    return None


def can_escape_after_bomb(x, y, arena, bomb_map):
    """폭탄 설치 후 탈출 가능 여부 (간소화)"""
    escape_routes = 0
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and
            arena[nx, ny] == 0 and bomb_map[nx, ny] > 2):
            escape_routes += 1
    
    return escape_routes >= 1  # 1개만 있어도 OK


def can_trap_enemy(x, y, enemy_pos, arena):
    """적을 가둘 수 있는지 확인"""
    ex, ey = enemy_pos
    
    # 적이 직선상에 있고 가까우면 True
    if x == ex and abs(y - ey) <= 3:
        return True
    if y == ey and abs(x - ex) <= 3:
        return True
    
    # 적이 코너나 좁은 공간에 있으면 True
    enemy_escape_routes = 0
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = ex + dx, ey + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and
            arena[nx, ny] == 0):
            enemy_escape_routes += 1
    
    return enemy_escape_routes <= 2


def destroy_crates_for_coins(self, x, y, arena, valid_actions, bombs_left, bomb_map, step):
    """상자 파괴로 코인 드롭 유도"""
    # 주변 상자 확인
    crates_nearby = []
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and
            arena[nx, ny] == 1):
            crates_nearby.append((nx, ny))
    
    # 상자가 2개 이상이면 폭탄
    if len(crates_nearby) >= 2 and bombs_left > 0 and 'BOMB' in valid_actions:
        if step - self.last_bomb_time >= 2:  # 쿨다운 짧게
            self.logger.info(f"Bombing {len(crates_nearby)} crates for coins")
            self.last_bomb_time = step
            return 'BOMB'
    
    # 상자가 1개라도 있으면 폭탄 고려
    if crates_nearby and bombs_left > 0 and 'BOMB' in valid_actions:
        if step - self.last_bomb_time >= 3 and can_escape_after_bomb(x, y, arena, bomb_map):
            self.logger.info(f"Bombing single crate")
            self.last_bomb_time = step
            return 'BOMB'
    
    # 상자 찾아가기
    free_space = arena == 0
    crates = [(i, j) for i in range(arena.shape[0]) for j in range(arena.shape[1]) if arena[i, j] == 1]
    if crates:
        direction = look_for_targets(free_space, (x, y), crates)
        if direction:
            if direction == (x, y - 1) and 'UP' in valid_actions:
                return 'UP'
            elif direction == (x, y + 1) and 'DOWN' in valid_actions:
                return 'DOWN'
            elif direction == (x - 1, y) and 'LEFT' in valid_actions:
                return 'LEFT'
            elif direction == (x + 1, y) and 'RIGHT' in valid_actions:
                return 'RIGHT'
    
    return None


def seek_enemies(x, y, enemies, arena, valid_actions):
    """적 추적"""
    if not enemies:
        return None
    
    free_space = arena == 0
    direction = look_for_targets(free_space, (x, y), enemies)
    if direction:
        if direction == (x, y - 1) and 'UP' in valid_actions:
            return 'UP'
        elif direction == (x, y + 1) and 'DOWN' in valid_actions:
            return 'DOWN'
        elif direction == (x - 1, y) and 'LEFT' in valid_actions:
            return 'LEFT'
        elif direction == (x + 1, y) and 'RIGHT' in valid_actions:
            return 'RIGHT'
    
    return None


def explore_map(x, y, arena, valid_actions):
    """맵 탐색"""
    # 가장 열린 공간으로 이동
    best_action = None
    max_openness = 0
    
    for action, dx, dy in [('UP', 0, -1), ('DOWN', 0, 1), ('LEFT', -1, 0), ('RIGHT', 1, 0)]:
        if action not in valid_actions:
            continue
        
        nx, ny = x + dx, y + dy
        openness = 0
        
        # 주변 열린 공간 계산
        for ddx, ddy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nnx, nny = nx + ddx, ny + ddy
            if (0 <= nnx < arena.shape[0] and 0 <= nny < arena.shape[1] and
                arena[nnx, nny] == 0):
                openness += 1
        
        if openness > max_openness:
            max_openness = openness
            best_action = action
    
    return best_action if best_action else random_move(valid_actions)


def random_move(valid_actions):
    """랜덤 이동"""
    movement = [a for a in valid_actions if a in ['UP', 'DOWN', 'LEFT', 'RIGHT']]
    if movement:
        shuffle(movement)
        return movement[0]
    
    return 'WAIT' if 'WAIT' in valid_actions else (valid_actions[0] if valid_actions else 'WAIT')