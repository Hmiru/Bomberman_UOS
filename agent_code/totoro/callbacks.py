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
    self.ignore_others_timer = 0
    self.current_round = 0
    

def reset_self(self):
    """Reset agent state at the beginning of each round."""
    self.bomb_history = deque([], 5)
    self.coordinate_history = deque([], 20)
    self.ignore_others_timer = 0


def act(self, game_state: dict):
    """Main decision function."""
    # 1. 정보 수집
    arena = game_state['field']
    _, my_score, bombs_left, (x, y) = game_state['self']
    bombs = game_state['bombs']
    bomb_xys = [xy for (xy, t) in bombs]
    others = [xy for (n, s, b, xy) in game_state['others']]
    coins = game_state['coins']
    explosion_map = game_state['explosion_map']
    
    # 2. 팀 구분
    my_name = game_state['self'][0]
    team_prefix = "totoro" 
    enemies = [xy for (n, s, b, xy) in game_state['others'] if team_prefix not in n]
    enemy_scores = [s for (n, s, b, xy) in game_state['others'] if team_prefix not in n]
    
    # 3. 1대1 상황 체크 및 전략적 자폭
    alive_enemies = len(enemies)
    if alive_enemies == 1 and len(game_state['others']) == 1:
        # 1대1 상황에서 점수가 앞서고 있다면
        if enemy_scores and my_score > max(enemy_scores):
            # 적과 가까이 있을 때 자폭
            enemy_dist = abs(enemies[0][0] - x) + abs(enemies[0][1] - y)
            if enemy_dist <= 3 and bombs_left > 0:
                self.bomb_history.append((x, y))
                return 'BOMB'
    
    # 4. 개선된 안전 지역 계산
    bomb_map = np.ones(arena.shape) * 5
    for (xb, yb), t in bombs:
        for (i, j) in [(xb + h, yb) for h in range(-3, 4)] + [(xb, yb + h) for h in range(-3, 4)]:
            if (0 < i < bomb_map.shape[0]) and (0 < j < bomb_map.shape[1]):
                bomb_map[i, j] = min(bomb_map[i, j], t)

    # 5. 위험 감지 개선
    # 현재 위치가 위험한지 즉시 체크
    in_danger = False
    if bomb_map[x, y] <= 1 or explosion_map[x, y] > 0:
        in_danger = True
    
    # 6. 유효한 행동 계산
    directions = [(x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    valid_tiles, valid_actions = [], []
    
    for d in directions:
        if ((arena[d] == 0) and
            (explosion_map[d] < 1) and
            (bomb_map[d] > 0) and
            (not d in others) and
            (not d in bomb_xys)):
            valid_tiles.append(d)

    if (x - 1, y) in valid_tiles: valid_actions.append('LEFT')
    if (x + 1, y) in valid_tiles: valid_actions.append('RIGHT')
    if (x, y - 1) in valid_tiles: valid_actions.append('UP')
    if (x, y + 1) in valid_tiles: valid_actions.append('DOWN')
    if (x, y) in valid_tiles: valid_actions.append('WAIT')
    
    # 7. 폭탄 설치 가능 여부
    if bombs_left > 0 and (x, y) not in self.bomb_history: 
        valid_actions.append('BOMB')
    
    # 8. 긴급 탈출 모드
    if in_danger:
        escape_action = emergency_escape(x, y, valid_actions, bomb_map, arena)
        if escape_action:
            return escape_action
    
    # 9. 역할별 행동
    if my_name.endswith('_0'):
        action = act_as_killer(self, game_state, valid_actions, enemies, bomb_xys, coins)
    else:
        action = act_as_lurer(self, game_state, valid_actions, enemies, bomb_xys, coins)
    
    self.logger.info(f"Agent {my_name}: action {action}")
    return action


def emergency_escape(x, y, valid_actions, bomb_map, arena):
    """긴급 탈출 로직"""
    # 가장 안전한 방향 선택
    safety_scores = {}
    
    for action in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
        if action not in valid_actions:
            continue
        
        dx, dy = 0, 0
        if action == 'UP': dy = -1
        elif action == 'DOWN': dy = 1
        elif action == 'LEFT': dx = -1
        elif action == 'RIGHT': dx = 1
        
        nx, ny = x + dx, y + dy
        if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]:
            # 안전도 계산 (폭탄까지 남은 시간)
            safety_scores[action] = bomb_map[nx, ny]
    
    if safety_scores:
        # 가장 안전한 방향 선택
        return max(safety_scores, key=safety_scores.get)
    
    return 'WAIT' if 'WAIT' in valid_actions else None


def is_safe_to_bomb(game_state, x, y):
    """폭탄 설치 후 안전하게 탈출 가능한지 체크 - 강화된 버전"""
    arena = game_state['field']
    bombs = game_state['bombs']
    others = game_state['others']
    
    # 시뮬레이션: 현재 위치에 폭탄 설치
    simulated_bombs = bombs + [((x, y), s.BOMB_TIMER)]
    
    # 폭발 범위 계산 (모든 폭탄 고려)
    danger_zones = set()
    for (bx, by), t in simulated_bombs:
        danger_zones.add((bx, by))
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            for i in range(1, s.BOMB_POWER + 1):
                nx, ny = bx + dx * i, by + dy * i
                if not (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]):
                    break
                if arena[nx, ny] == -1:  # 벽에 막힘
                    break
                danger_zones.add((nx, ny))
    
    # BFS로 안전지대까지의 경로 탐색
    queue = deque([(x, y, 0)])
    visited = set([(x, y)])
    safe_paths_found = 0
    
    while queue:
        cx, cy, steps = queue.popleft()
        
        # 폭탄 타이머보다 많은 스텝은 무의미
        if steps > s.BOMB_TIMER:
            continue
        
        # 안전지대 도달 확인
        if (cx, cy) not in danger_zones and steps > 0:
            safe_paths_found += 1
            # 빠른 탈출 경로가 있으면 즉시 True 반환
            if steps <= 2:  # 2스텝 이내 안전지대 도달 가능
                return True
            # 여러 경로가 있으면 안전
            if safe_paths_found >= 2:
                return True
        
        # 다음 위치 탐색
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            
            # 이동 가능 체크
            if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and 
                arena[nx, ny] == 0 and (nx, ny) not in visited):
                
                # 다른 폭탄 위치는 피함
                if any((nx, ny) == bomb_xy for bomb_xy, _ in simulated_bombs):
                    continue
                
                # 다른 에이전트 위치도 피함
                if any((nx, ny) == xy for n, s, b, xy in others):
                    continue
                
                visited.add((nx, ny))
                queue.append((nx, ny, steps + 1))
    
    # 안전 경로가 전혀 없으면 False
    return safe_paths_found > 0


def act_as_killer(self, game_state, valid_actions, enemies, bomb_xys, coins):
    """킬러 전략 - 적 추적 및 제거 (안전 강화)"""
    action_ideas = []
    
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    
    # 폭탄 회피 최우선
    escape_actions = get_escape_actions(x, y, game_state['bombs'], arena)
    if escape_actions:
        # 위험한 상황이면 즉시 탈출
        for action in escape_actions:
            if action in valid_actions:
                self.logger.info(f"Killer emergency escape: {action}")
                return action
    
    # 초반 탈출 개선: 상자에 둘러싸여 있는지 체크
    surrounded_by_crates = 0
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]:
            if arena[nx, ny] == 1:
                surrounded_by_crates += 1
    
    # 상자에 많이 둘러싸여 있으면 폭탄 (안전 체크 필수)
    if surrounded_by_crates >= 3 and 'BOMB' in valid_actions:
        # 탈출 경로가 확실한 경우만 폭탄 설치
        if is_safe_to_bomb(game_state, x, y):
            self.bomb_history.append((x, y))
            self.logger.info(f"Killer placing bomb to escape crates (safe)")
            return 'BOMB'
        else:
            # 탈출 불가능하면 이동 시도
            for action in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
                if action in valid_actions:
                    self.logger.info(f"Killer moving instead of bombing: {action}")
                    return action
    
    # 타겟 설정
    free_space = arena == 0
    
    # 1순위: 적 추적
    if enemies:
        d = look_for_targets(free_space, (x, y), enemies, self.logger)
        if d:
            if d == (x, y - 1): action_ideas.append('UP')
            elif d == (x, y + 1): action_ideas.append('DOWN')
            elif d == (x - 1, y): action_ideas.append('LEFT')
            elif d == (x + 1, y): action_ideas.append('RIGHT')
            
            # 적이 가까이 있으면 폭탄 (안전 확인 강화)
            min_enemy_dist = min(abs(ex - x) + abs(ey - y) for ex, ey in enemies)
            if min_enemy_dist <= 2 and 'BOMB' in valid_actions:
                # 더 엄격한 안전 체크
                if is_safe_to_bomb(game_state, x, y):
                    self.logger.info(f"Killer attacking enemy at distance {min_enemy_dist}")
                    action_ideas.append('BOMB')
                else:
                    self.logger.info(f"Killer skipping bomb - unsafe")
    
    # 2순위: 상자 파괴 (길 뚫기)
    cols = range(1, arena.shape[0] - 1)
    rows = range(1, arena.shape[1] - 1)
    crates = [(r, c) for r in rows for c in cols if arena[r, c] == 1]
    
    if not action_ideas and crates:
        d = look_for_targets(free_space, (x, y), crates, self.logger)
        if d:
            if d == (x, y - 1): action_ideas.append('UP')
            elif d == (x, y + 1): action_ideas.append('DOWN')
            elif d == (x - 1, y): action_ideas.append('LEFT')
            elif d == (x + 1, y): action_ideas.append('RIGHT')
    
    # 상자 옆에 있으면 폭탄 (안전 확인 필수)
    crate_nearby = False
    for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
        if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and arena[nx, ny] == 1:
            crate_nearby = True
            break
    
    if crate_nearby and 'BOMB' in valid_actions:
        # 탈출 경로 확실히 확보된 경우만
        if is_safe_to_bomb(game_state, x, y):
            action_ideas.append('BOMB')
            self.logger.info("Killer placing bomb near crate (safe)")
        else:
            self.logger.info("Killer avoiding bomb near crate - unsafe")
    
    # 3순위: 코인 수집
    if coins and not action_ideas:
        d = look_for_targets(free_space, (x, y), coins, self.logger)
        if d:
            if d == (x, y - 1): action_ideas.append('UP')
            elif d == (x, y + 1): action_ideas.append('DOWN')
            elif d == (x - 1, y): action_ideas.append('LEFT')
            elif d == (x + 1, y): action_ideas.append('RIGHT')
    
    # 유효한 행동 선택
    for a in action_ideas:
        if a in valid_actions:
            if a == 'BOMB':
                self.bomb_history.append((x, y))
            return a
    
    # 기본 행동
    if valid_actions:
        shuffle(valid_actions)
        for a in valid_actions:
            if a != 'WAIT':
                return a
    
    return 'WAIT'


def act_as_lurer(self, game_state, valid_actions, enemies, bomb_xys, coins):
    """루러 전략 - 코인 수집 최우선 (안전 강화)"""
    action_ideas = []
    
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    
    # 폭탄 회피 최우선
    escape_actions = get_escape_actions(x, y, game_state['bombs'], arena)
    if escape_actions:
        for action in escape_actions:
            if action in valid_actions:
                self.logger.info(f"Lurer emergency escape: {action}")
                return action
    
    # 초반 탈출
    surrounded_by_crates = 0
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]:
            if arena[nx, ny] == 1:
                surrounded_by_crates += 1
    
    if surrounded_by_crates >= 3 and 'BOMB' in valid_actions:
        if is_safe_to_bomb(game_state, x, y):
            self.bomb_history.append((x, y))
            self.logger.info(f"Lurer placing bomb to escape crates (safe)")
            return 'BOMB'
        else:
            # 탈출 불가능하면 이동
            for action in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
                if action in valid_actions:
                    self.logger.info(f"Lurer moving instead of bombing: {action}")
                    return action
    
    free_space = arena == 0
    
    # 1순위: 코인 수집 (개선된 로직)
    if coins:
        # 가장 가까운 코인 찾기
        d = look_for_targets(free_space, (x, y), coins, self.logger)
        if d:
            if d == (x, y - 1): action_ideas.append('UP')
            elif d == (x, y + 1): action_ideas.append('DOWN')
            elif d == (x - 1, y): action_ideas.append('LEFT')
            elif d == (x + 1, y): action_ideas.append('RIGHT')
    
    # 2순위: 상자 파괴 (코인 생성)
    if not coins:
        cols = range(1, arena.shape[0] - 1)
        rows = range(1, arena.shape[1] - 1)
        crates = [(r, c) for r in rows for c in cols if arena[r, c] == 1]
        
        if crates:
            d = look_for_targets(free_space, (x, y), crates, self.logger)
            if d:
                if d == (x, y - 1): action_ideas.append('UP')
                elif d == (x, y + 1): action_ideas.append('DOWN')
                elif d == (x - 1, y): action_ideas.append('LEFT')
                elif d == (x + 1, y): action_ideas.append('RIGHT')
        
        # 상자 옆에 있으면 폭탄 (안전 체크)
        if any(arena[nx, ny] == 1 for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
               if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]):
            if 'BOMB' in valid_actions and is_safe_to_bomb(game_state, x, y):
                action_ideas.append('BOMB')
    
    # 3순위: 적 회피
    if enemies:
        # 가장 가까운 적으로부터 도망
        min_enemy = min(enemies, key=lambda e: abs(e[0] - x) + abs(e[1] - y))
        if abs(min_enemy[0] - x) + abs(min_enemy[1] - y) <= 3:
            # 반대 방향으로 도망
            if min_enemy[0] > x and 'LEFT' in valid_actions: action_ideas.append('LEFT')
            elif min_enemy[0] < x and 'RIGHT' in valid_actions: action_ideas.append('RIGHT')
            if min_enemy[1] > y and 'UP' in valid_actions: action_ideas.append('UP')
            elif min_enemy[1] < y and 'DOWN' in valid_actions: action_ideas.append('DOWN')
    
    # 유효한 행동 선택
    for a in action_ideas:
        if a in valid_actions:
            if a == 'BOMB':
                self.bomb_history.append((x, y))
            return a
    
    # 기본 행동
    if valid_actions:
        shuffle(valid_actions)
        for a in valid_actions:
            if a != 'WAIT':
                return a
    
    return 'WAIT'


def get_escape_actions(x, y, bombs, arena):
    """개선된 폭탄 회피 로직"""
    ideas = []
    
    for (xb, yb), t in bombs:
        # 폭탄이 임박했을 때만 회피
        if t <= 2:
            # 같은 행에 있을 때
            if xb == x and abs(yb - y) <= s.BOMB_POWER:
                # 벽에 막혔는지 확인
                blocked = False
                if yb > y:
                    for check_y in range(y + 1, yb):
                        if arena[x][check_y] == -1:
                            blocked = True
                            break
                else:
                    for check_y in range(yb + 1, y):
                        if arena[x][check_y] == -1:
                            blocked = True
                            break
                
                if not blocked:
                    # 수직으로 도망
                    ideas.extend(['UP', 'DOWN'])
                    # 멀리 도망가기
                    if yb > y:
                        ideas.append('UP')
                    else:
                        ideas.append('DOWN')
            
            # 같은 열에 있을 때
            if yb == y and abs(xb - x) <= s.BOMB_POWER:
                # 벽에 막혔는지 확인
                blocked = False
                if xb > x:
                    for check_x in range(x + 1, xb):
                        if arena[check_x][y] == -1:
                            blocked = True
                            break
                else:
                    for check_x in range(xb + 1, x):
                        if arena[check_x][y] == -1:
                            blocked = True
                            break
                
                if not blocked:
                    # 수평으로 도망
                    ideas.extend(['LEFT', 'RIGHT'])
                    # 멀리 도망가기
                    if xb > x:
                        ideas.append('LEFT')
                    else:
                        ideas.append('RIGHT')
    
    return ideas