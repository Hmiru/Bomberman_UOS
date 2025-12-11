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
    self.last_bomb_time = 0  # 마지막 폭탄 설치 시간
    

def reset_self(self):
    """Reset agent state at the beginning of each round."""
    self.bomb_history = deque([], 5)
    self.coordinate_history = deque([], 20)
    self.ignore_others_timer = 0
    self.last_bomb_time = 0


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
    step = game_state['step']
    
    # 2. 팀 구분 및 팀원 위치 추적
    my_name = game_state['self'][0]
    team_prefix = "totoro" 
    enemies = [xy for (n, s, b, xy) in game_state['others'] if team_prefix not in n]
    enemy_scores = [s for (n, s, b, xy) in game_state['others'] if team_prefix not in n]
    
    # 팀원 위치 추적
    teammate_pos = None
    teammate_score = 0
    for n, s, b, xy in game_state['others']:
        if team_prefix in n and n != my_name:
            teammate_pos = xy
            teammate_score = s
            break
    
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
    
    # 7. 폭탄 설치 가능 여부 (쿨다운 감소)
    if bombs_left > 0 and (x, y) not in self.bomb_history:
        # 최소 3스텝 간격으로만 폭탄 설치 (더 공격적으로)
        if step - self.last_bomb_time >= 3:
            valid_actions.append('BOMB')
    
    # 8. 긴급 탈출 모드
    if in_danger:
        escape_action = emergency_escape(x, y, valid_actions, bomb_map, arena)
        if escape_action:
            return escape_action
    
    # 9. 동적 역할 결정 및 행동
    # 상황에 따라 역할 전환
    should_be_aggressive = False
    
    # 코인이 많고 적이 멀면 누구든 코인 수집
    if len(coins) > 3 and (not enemies or min(abs(ex - x) + abs(ey - y) for ex, ey in enemies) > 5):
        should_be_aggressive = False
    # 적이 가깝고 유리한 위치면 누구든 공격
    elif enemies and min(abs(ex - x) + abs(ey - y) for ex, ey in enemies) <= 3:
        should_be_aggressive = True
    # 기본적으로 역할 유지
    else:
        should_be_aggressive = my_name.endswith('_0')
    
    # 팀원과의 협동 고려
    if should_be_aggressive:
        action = act_as_killer(self, game_state, valid_actions, enemies, bomb_xys, coins, teammate_pos)
    else:
        action = act_as_lurer(self, game_state, valid_actions, enemies, bomb_xys, coins, teammate_pos)
    
    # 폭탄 설치 시 시간 기록
    if action == 'BOMB':
        self.last_bomb_time = step
    
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


def is_safe_to_bomb_strict(game_state, x, y, role="killer"):
    """폭탄 설치 안전성 체크 (덜 엄격하게)"""
    arena = game_state['field']
    bombs = game_state['bombs']
    others = game_state['others']
    
    # 이미 다른 폭탄이 많으면 설치 금지 (3개까지 허용)
    if len(bombs) >= 3:
        return False
    
    # 현재 위치가 이미 위험하면 금지
    for (bx, by), t in bombs:
        if t <= 2:  # 곧 터질 폭탄이 있으면
            if (bx == x and abs(by - y) <= s.BOMB_POWER) or \
               (by == y and abs(bx - x) <= s.BOMB_POWER):
                return False
    
    # 시뮬레이션: 현재 위치에 폭탄 설치
    simulated_bombs = bombs + [((x, y), s.BOMB_TIMER)]
    
    # 폭발 범위 계산
    danger_zones = set()
    for (bx, by), t in simulated_bombs:
        danger_zones.add((bx, by))
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            for i in range(1, s.BOMB_POWER + 1):
                nx, ny = bx + dx * i, by + dy * i
                if not (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]):
                    break
                if arena[nx, ny] == -1:
                    break
                danger_zones.add((nx, ny))
    
    # 즉시 접근 가능한 안전한 곳이 있는지 확인
    safe_neighbors = 0
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and 
            arena[nx, ny] == 0 and (nx, ny) not in danger_zones):
            # 다른 장애물이 없는지 확인
            if not any((nx, ny) == bomb_xy for bomb_xy, _ in simulated_bombs):
                if not any((nx, ny) == xy for n, s, b, xy in others):
                    safe_neighbors += 1
    
    # 역할별 안전 기준 (더 공격적으로)
    if role == "lurer":
        return safe_neighbors >= 1  # Lurer도 1개만 있어도 OK
    else:
        return safe_neighbors >= 1


def act_as_killer(self, game_state, valid_actions, enemies, bomb_xys, coins, teammate_pos=None):
    """킬러 전략 - 적 추적 및 제거 (팀 협동 강화)"""
    action_ideas = []
    
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    
    # 팀원과의 협동 공격 체크
    if teammate_pos and enemies:
        # 가장 가까운 적 찾기
        closest_enemy = min(enemies, key=lambda e: abs(e[0] - x) + abs(e[1] - y))
        my_dist = abs(closest_enemy[0] - x) + abs(closest_enemy[1] - y)
        teammate_dist = abs(closest_enemy[0] - teammate_pos[0]) + abs(closest_enemy[1] - teammate_pos[1])
        
        # 팀원과 함께 포위 공격
        if my_dist <= 4 and teammate_dist <= 4:
            self.logger.info(f"Killer: Coordinating attack with teammate!")
            # 다른 방향에서 접근
            if closest_enemy[0] > x and teammate_pos[0] < closest_enemy[0]:
                action_ideas.append('RIGHT')  # 나는 왼쪽에서
            elif closest_enemy[0] < x and teammate_pos[0] > closest_enemy[0]:
                action_ideas.append('LEFT')   # 나는 오른쪽에서
            if closest_enemy[1] > y and teammate_pos[1] < closest_enemy[1]:
                action_ideas.append('DOWN')   # 나는 위에서
            elif closest_enemy[1] < y and teammate_pos[1] > closest_enemy[1]:
                action_ideas.append('UP')     # 나는 아래에서
    
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
        if is_safe_to_bomb_strict(game_state, x, y, "killer"):
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
            
            # 적이 가까이 있으면 폭탄 (더 공격적으로)
            min_enemy_dist = min(abs(ex - x) + abs(ey - y) for ex, ey in enemies)
            if min_enemy_dist <= 3 and 'BOMB' in valid_actions:  # 거리 증가
                # 더 엄격한 안전 체크
                if is_safe_to_bomb_strict(game_state, x, y, "killer"):
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
        if is_safe_to_bomb_strict(game_state, x, y, "killer"):
            action_ideas.append('BOMB')
            self.logger.info("Killer placing bomb near crate (safe)")
        else:
            self.logger.info("Killer avoiding bomb near crate - unsafe")
    
    # 3순위: 코인 수집
    if coins and not action_ideas:
        d = look_for_targets(free_space, (x, y), coins, self.logger)
        if d and d != (x, y):  # 이미 코인 위치에 있는 경우 제외
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


def act_as_lurer(self, game_state, valid_actions, enemies, bomb_xys, coins, teammate_pos=None):
    """루러 전략 - 적극적 코인 수집 및 유인 (개선된 폭탄 사용)"""
    action_ideas = []
    
    arena = game_state['field']
    _, _, bombs_left, (x, y) = game_state['self']
    
    # 팀원이 적과 전투 중이면 측면 지원
    if teammate_pos and enemies:
        for enemy in enemies:
            enemy_dist_to_teammate = abs(enemy[0] - teammate_pos[0]) + abs(enemy[1] - teammate_pos[1])
            enemy_dist_to_me = abs(enemy[0] - x) + abs(enemy[1] - y)
            
            # 팀원이 적과 가까이 있고 나도 가까이 있으면
            if enemy_dist_to_teammate <= 3 and enemy_dist_to_me <= 5:
                self.logger.info(f"Lurer: Supporting teammate in combat!")
                
                # 적의 퇴로 차단 시도
                if enemy[0] > teammate_pos[0] and x < enemy[0]:
                    action_ideas.append('RIGHT')  # 적의 반대편으로
                elif enemy[0] < teammate_pos[0] and x > enemy[0]:
                    action_ideas.append('LEFT')
                if enemy[1] > teammate_pos[1] and y < enemy[1]:
                    action_ideas.append('DOWN')
                elif enemy[1] < teammate_pos[1] and y > enemy[1]:
                    action_ideas.append('UP')
                
                # 적절한 거리에서 폭탄으로 지원
                if enemy_dist_to_me == 3 and bombs_left > 0 and 'BOMB' in valid_actions:
                    if is_safe_to_bomb_strict(game_state, x, y, "lurer"):
                        action_ideas.append('BOMB')
                        self.logger.info("Lurer: Supporting with bomb!")
    
    # 폭탄 회피 최우선
    escape_actions = get_escape_actions(x, y, game_state['bombs'], arena)
    if escape_actions:
        for action in escape_actions:
            if action in valid_actions:
                self.logger.info(f"Lurer emergency escape: {action}")
                return action
    
    # 초기 상자 탈출 체크 (게임 시작 시) - 더 적극적으로
    if game_state['step'] < 20:  # 초반 더 길게
        surrounded_by_crates = 0
        free_directions = []
        for dx, dy, direction in [(0, 1, 'DOWN'), (0, -1, 'UP'), (1, 0, 'RIGHT'), (-1, 0, 'LEFT')]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]:
                if arena[nx, ny] == 1:
                    surrounded_by_crates += 1
                elif arena[nx, ny] == 0:
                    free_directions.append(direction)
        
        # 1개라도 막혔으면 폭탄 고려 (매우 적극적)
        if surrounded_by_crates >= 1 and 'BOMB' in valid_actions:
            # 안전 체크
            if is_safe_to_bomb_strict(game_state, x, y, "lurer"):
                self.bomb_history.append((x, y))
                self.logger.info(f"Lurer placing bomb - {surrounded_by_crates} sides blocked")
                return 'BOMB'
        elif surrounded_by_crates >= 2 and free_directions:
            # 탈출 가능하면 탈출
            for direction in free_directions:
                if direction in valid_actions:
                    self.logger.info(f"Lurer escaping: {direction}")
                    return direction
    
    free_space = arena == 0
    
    # 1순위: 코인 수집 (폭탄 없이)
    if coins:
        # 가장 가까운 코인 찾기
        d = look_for_targets(free_space, (x, y), coins, self.logger)
        if d and d != (x, y):  # 이미 코인 위치에 있는 경우 제외
            self.logger.info(f"Lurer found coin target at {d}, current pos ({x},{y})")
            if d == (x, y - 1): 
                action_ideas.append('UP')
                self.logger.info("Lurer moving UP for coin")
            elif d == (x, y + 1): 
                action_ideas.append('DOWN')
                self.logger.info("Lurer moving DOWN for coin")
            elif d == (x - 1, y): 
                action_ideas.append('LEFT')
                self.logger.info("Lurer moving LEFT for coin")
            elif d == (x + 1, y): 
                action_ideas.append('RIGHT')
                self.logger.info("Lurer moving RIGHT for coin")
        elif d == (x, y):
            self.logger.info(f"Lurer already at coin position, looking for next coin")
        else:
            self.logger.info(f"Lurer couldn't find path to {len(coins)} coins")
    
    # 2순위: 전략적 유인 (단순 회피 대신)
    if enemies and not action_ideas:
        min_enemy = min(enemies, key=lambda e: abs(e[0] - x) + abs(e[1] - y))
        enemy_dist = abs(min_enemy[0] - x) + abs(min_enemy[1] - y)
        
        # 적을 팀원 쪽으로 유인
        if enemy_dist <= 5 and teammate_pos:
            # 팀원 방향으로 이동하면서 적을 끌고감
            if teammate_pos[0] > x and 'RIGHT' in valid_actions:
                action_ideas.append('RIGHT')
                self.logger.info("Lurer: Luring enemy towards teammate (RIGHT)")
            elif teammate_pos[0] < x and 'LEFT' in valid_actions:
                action_ideas.append('LEFT')
                self.logger.info("Lurer: Luring enemy towards teammate (LEFT)")
            if teammate_pos[1] > y and 'DOWN' in valid_actions:
                action_ideas.append('DOWN')
                self.logger.info("Lurer: Luring enemy towards teammate (DOWN)")
            elif teammate_pos[1] < y and 'UP' in valid_actions:
                action_ideas.append('UP')
                self.logger.info("Lurer: Luring enemy towards teammate (UP)")
        elif enemy_dist <= 3:  # 너무 가까우면 회피
            # 반대 방향으로 도망
            if min_enemy[0] > x and 'LEFT' in valid_actions: 
                action_ideas.append('LEFT')
            elif min_enemy[0] < x and 'RIGHT' in valid_actions: 
                action_ideas.append('RIGHT')
            if min_enemy[1] > y and 'UP' in valid_actions: 
                action_ideas.append('UP')
            elif min_enemy[1] < y and 'DOWN' in valid_actions: 
                action_ideas.append('DOWN')
    
    # 3순위: 상자 파괴 (코인이 없을 때)
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
        
        # 상자 옆에서 폭탄 (안전할 때)
        crate_count = sum(1 for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
                         if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and arena[nx, ny] == 1)
        
        # 상자가 있고 안전할 때 더 적극적으로 폭탄 사용
        if crate_count >= 1 and 'BOMB' in valid_actions:
            # 근처에 적이 있는지 확인
            enemy_nearby = False
            if enemies:
                for ex, ey in enemies:
                    if abs(ex - x) + abs(ey - y) <= 3:  # 더 가까운 경우만
                        enemy_nearby = True
                        break
            
            # 적이 없거나 팀원이 가까이 있으면 폭탄 사용
            if (not enemy_nearby or (teammate_pos and abs(teammate_pos[0] - x) + abs(teammate_pos[1] - y) <= 5)):
                if is_safe_to_bomb_strict(game_state, x, y, "lurer"):
                    action_ideas.insert(0, 'BOMB')  # 우선순위 높임
                    self.logger.info(f"Lurer actively bombing {crate_count} crates")
    
    # 유효한 행동 선택 (폭탄은 최후의 수단)
    non_bomb_actions = [a for a in action_ideas if a != 'BOMB' and a in valid_actions]
    if non_bomb_actions:
        self.logger.info(f"Lurer executing action from ideas: {non_bomb_actions[0]}")
        return non_bomb_actions[0]
    
    # 기본 이동
    if valid_actions:
        movement_actions = [a for a in valid_actions if a in ['UP', 'DOWN', 'LEFT', 'RIGHT']]
        if movement_actions:
            shuffle(movement_actions)
            self.logger.info(f"Lurer using random movement: {movement_actions[0]} (no action ideas)")
            return movement_actions[0]
    
    # 정말 최후의 수단으로만 폭탄
    if 'BOMB' in action_ideas and 'BOMB' in valid_actions:
        # 한 번 더 안전 체크
        if is_safe_to_bomb_strict(game_state, x, y, "lurer"):
            self.bomb_history.append((x, y))
            self.logger.info("Lurer placing bomb as absolute last resort")
            return 'BOMB'
    
    return 'WAIT' if 'WAIT' in valid_actions else valid_actions[0] if valid_actions else 'WAIT'


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