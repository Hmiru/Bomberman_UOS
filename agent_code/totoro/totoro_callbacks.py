import numpy as np
from collections import deque
from random import shuffle
import settings as s

def setup(self):
    """에이전트 초기화"""
    self.logger.debug('Successfully entered setup code')
    np.random.seed()
    self.bomb_history = deque([], 5)
    self.coordinate_history = deque([], 20)
    self.ignore_others_timer = 0
    self.current_round = 0

def act(self, game_state: dict):
    """메인 행동 결정 함수"""
    # 1. 정보 수집
    arena = game_state['field']
    _, score, bombs_left, (x, y) = game_state['self']
    bombs = game_state['bombs']
    bomb_xys = [xy for (xy, t) in bombs]
    
    my_name = game_state['self'][0]
    team_prefix = "totoro"
    enemies = [xy for (n, s, b, xy) in game_state['others'] if team_prefix not in n]

    # 2. [핵심 수정] 정밀한 위험 지도 생성 (폭발 예정지 포함)
    # safety_margin=1: 당장 터지거나(0), 1턴 뒤에 터질(1) 폭탄의 범위를 위험지대로 설정
    unsafe_map = get_unsafe_map(game_state, safety_margin=1)
    
    # 3. 이동 가능한 타일 계산
    directions = [(x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    valid_tiles = []
    
    for d in directions:
        if ((0 <= d[0] < arena.shape[0]) and (0 <= d[1] < arena.shape[1]) and # 맵 내부
            (arena[d] == 0) and      # 벽/상자 아님
            (not unsafe_map[d]) and  # [중요] 곧 터질 곳 이동 불가
            (d not in bomb_xys) and  # 폭탄 위 아님
            (d not in [xy for (n, s, b, xy) in game_state['others']])): # 다른 에이전트 위치 아님
            valid_tiles.append(d)

    # 행동 명령어로 변환
    valid_actions = []
    if (x - 1, y) in valid_tiles: valid_actions.append('LEFT')
    if (x + 1, y) in valid_tiles: valid_actions.append('RIGHT')
    if (x, y - 1) in valid_tiles: valid_actions.append('UP')
    if (x, y + 1) in valid_tiles: valid_actions.append('DOWN')
    if (x, y) in valid_tiles: valid_actions.append('WAIT')
    
    if (bombs_left > 0) and (x, y) not in self.bomb_history:
        valid_actions.append('BOMB')

    # 4. [생존 최우선] 현재 위치가 위험하면 무조건 탈출
    # unsafe_map에 내 위치가 포함되어 있거나(곧 터짐), 긴급 상황이면 회피
    if unsafe_map[(x, y)] or is_imminent_danger((x, y), bombs):
        best_escape = get_best_escape(self, game_state, valid_actions)
        if best_escape:
            self.logger.info(f"Emergency Escape! Action: {best_escape}")
            print(my_name, "Emergency Escape! Action:", best_escape)
            return best_escape

    # 5. 역할별 행동 수행
    if my_name.endswith('_0'):
        return act_as_killer(self, game_state, valid_actions, enemies, bomb_xys)
    else:
        return act_as_lurer(self, game_state, valid_actions, enemies, bomb_xys)

# --- [전략 1] 킬러 (적 추적 및 공격) ---
def act_as_killer(self, game_state, valid_actions, enemies, bomb_xys):
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    
    # [개선] 킬러는 상자도 부수며 길을 열어야 함
    crates = [(r, c) for r in range(1, arena.shape[0] - 1) for c in range(1, arena.shape[1] - 1) if arena[r, c] == 1]
    
    free_space = (arena == 0)
    for bx, by in bomb_xys:
        free_space[bx, by] = False
        
    # 1. 공격: 적을 가두거나 직접 타격
    # [개선] 가장 가까운 적을 타겟으로 설정
    if enemies:
        target_enemy = min(enemies, key=lambda e: np.linalg.norm(np.array(e) - np.array((x, y))))
        dist_to_enemy = np.linalg.norm(np.array(target_enemy) - np.array((x, y)))

        # 적이 근처에 있고, 폭탄 설치가 안전하다면 공격
        if dist_to_enemy < 5 and 'BOMB' in valid_actions:
            if is_safe_to_bomb(self, game_state, (x, y)):
                # [개선] 적을 가두는 위치에 폭탄 설치 시도
                if can_trap_enemy(game_state, target_enemy):
                    self.bomb_history.append((x, y))
                    self.logger.info("Killer: Trapping enemy with a bomb.")
                    return 'BOMB'
                # 직접 타격 가능한 경우
                if dist_to_enemy <= 2:
                    self.bomb_history.append((x, y))
                    self.logger.info("Killer: Attacking nearby enemy.")
                    return 'BOMB'

    # 2. 이동: 적 > 상자 > 코인 순으로 우선순위 설정
    targets = []
    if enemies: targets.extend(enemies)
    if crates: targets.extend(crates) # 길을 열기 위해 상자도 목표
    if game_state['coins']: targets.extend(game_state['coins'])

    if targets:
        d = look_for_targets(free_space, (x, y), targets)
        
        # 목표에 인접했고, 그것이 상자이며, 폭탄 설치가 안전하면 파괴
        if d and (abs(d[0]-x) + abs(d[1]-y) <= 1) and arena[d] == 1 and 'BOMB' in valid_actions:
             if is_safe_to_bomb(self, game_state, (x, y)):
                self.bomb_history.append((x, y))
                return 'BOMB'

        move = get_move_from_target(x, y, d)
        if move in valid_actions:
            return move
    
    # 3. 최후의 수단: 안전한 곳에서 대기 또는 무작위 이동
    if 'BOMB' in valid_actions and is_safe_to_bomb(self, game_state, (x, y)):
        if is_safe_to_bomb(self, game_state, (x, y)):
            self.bomb_history.append((x, y))
            return 'BOMB'

    return 'WAIT'

# --- [전략 2] 미끼 (상자 파밍 및 생존) ---
def act_as_lurer(self, game_state, valid_actions, enemies, bomb_xys):
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    coins = game_state['coins']
    
    free_space = (arena == 0)
    for bx, by in bomb_xys:
        free_space[bx, by] = False

    # 1. [방어] 적 근접 시 방어용 폭탄 (안전할 때만)
    if enemies:
        dist = min([abs(ex - x) + abs(ey - y) for ex, ey in enemies])
        if dist <= 2 and 'BOMB' in valid_actions:
            if is_safe_to_bomb(self, game_state, (x, y)):
                self.bomb_history.append((x, y))
                return 'BOMB'

    # 2. [파밍] 코인 > 상자 순으로 목표 설정
    cols = range(1, arena.shape[0] - 1)
    rows = range(1, arena.shape[0] - 1)
    crates = [(r, c) for r in cols for c in rows if (arena[r, c] == 1)]
    
    # [개선] 맵 중앙의 상자를 우선적으로 파괴하여 공간 확보
    center_crates = sorted(crates, key=lambda c: abs(c[0] - arena.shape[0]//2) + abs(c[1] - arena.shape[1]//2))
    
    targets = []
    if coins: targets.extend(coins)
    if center_crates: targets.extend(center_crates)
    if crates: targets.extend(crates)

    if targets:
        d = look_for_targets(free_space, (x, y), targets)
        
        # 목표(코인 또는 상자)에 도달했거나 인접한 경우
        if d and (d == (x,y) or (abs(d[0]-x) + abs(d[1]-y) <= 1)):
            # 주변에 상자가 있고, 폭탄 설치가 안전하면 파괴
            is_crate_nearby = any(arena[nx, ny] == 1 for nx, ny in [(x+1,y), (x-1,y), (x,y+1), (x,y-1)] if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1])
            if is_crate_nearby and 'BOMB' in valid_actions:
                # [개선] 안전 지대를 미리 찾고 폭탄 설치
                escape_route = get_best_escape(self, game_state, valid_actions, bomb_at=(x,y))
                if escape_route:
                    self.logger.info("Lurer: Bombing crate with a safe escape route.")
                    self.bomb_history.append((x, y))
                    return 'BOMB'
        
        move = get_move_from_target(x, y, d)
        if move in valid_actions:
            return move

    # 3. [생존] 대기보다는 무작위 이동
    if valid_actions:
        if 'WAIT' in valid_actions and len(valid_actions) > 1:
            valid_actions.remove('WAIT')
        shuffle(valid_actions)
        return valid_actions[0]
        
    return 'WAIT'

# --- [핵심 유틸리티 수정] ---

def get_unsafe_map(game_state, safety_margin=1):
    """
    이동하면 죽는 위치 계산.
    safety_margin=1: 1턴 뒤에 터질 폭탄의 화염 범위도 위험 지역으로 간주.
    """
    unsafe = np.zeros_like(game_state['field'], dtype=bool)
    
    # 1. 이미 터지고 있는 곳
    unsafe[game_state['explosion_map'] > 0] = True
    
    # 2. 곧 터질 폭탄의 예상 화염 범위
    arena = game_state['field']
    bombs = game_state['bombs']
    
    # 연쇄 폭발을 고려하기 위해 폭탄을 타이머 순으로 정렬
    sorted_bombs = sorted(bombs, key=lambda b: b[1])

    for (bx, by), t in bombs:
        # 타이머가 safety_margin 이하인 폭탄은 모두 위험 처리
        if t <= safety_margin:
            unsafe[bx, by] = True # 폭탄 본체 위치
            # 4방향 화염 확산 예측
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                for i in range(1, s.BOMB_POWER + 1):
                    nx, ny = bx + dx*i, by + dy*i
                    # 맵 밖 체크
                    if not (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]): break
                    # [개선] 다른 폭탄에 닿으면 연쇄 폭발하므로 확산 중지 안함
                    is_other_bomb = False
                    for obx, oby in [(b[0][0], b[0][1]) for b in bombs if b[0] != (bx, by)]:
                        if (nx, ny) == (obx, oby): is_other_bomb = True
                    if not is_other_bomb and arena[nx, ny] == -1: break
                    # 벽 체크 (돌 벽은 화염을 막음)
                    if arena[nx, ny] == -1: break
                    unsafe[nx, ny] = True
    return unsafe

def is_safe_to_bomb(self, game_state, my_pos):
    """
    [개선된 로직] 폭탄 설치 후 시간의 흐름에 따라 생존 가능성을 정교하게 시뮬레이션합니다.
    BFS의 각 step을 시간(time)으로 간주하고, 해당 시간에 터지는 폭탄의 위험을 계산하여 회피합니다.
    """
    x, y = my_pos
    arena = game_state['field']
    bombs = game_state['bombs']
    
    # 1. 가상 폭탄을 현재 위치에 설치
    simulated_bombs = bombs + [((x, y), s.BOMB_TIMER)]
    
    # 2. BFS로 시간의 흐름(current_time)에 따른 탈출 경로 탐색
    queue = deque([(my_pos, 0)])  # (position, current_time)
    visited = set([(x, y)])
    
    # 모든 폭탄의 최종 폭발 범위를 미리 계산
    full_blast_mask = get_blast_mask(arena, simulated_bombs)

    while queue:
        current_pos, current_time = queue.popleft()

        # 3. 생존 조건: 폭탄이 터지기 전에 최종 안전지대(full_blast_mask 밖)에 도달
        if not full_blast_mask[current_pos] and current_time < s.BOMB_TIMER:
            return True

        # 4. 다음 시간(next_time)으로 이동
        next_time = current_time + 1
        if next_time > s.BOMB_TIMER: continue # 시뮬레이션 시간 초과 (값을 줄이면 연산량 감소)

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)]: # 제자리 대기 포함
            next_pos = (current_pos[0] + dx, current_pos[1] + dy)

            # 5. 이동 유효성 및 안전성 검사
            if (0 <= next_pos[0] < arena.shape[0] and 0 <= next_pos[1] < arena.shape[1] and
                    arena[next_pos] == 0 and (next_pos, next_time) not in visited):
                
                # 다음 시간에 터지는 폭탄들의 위험 지역 계산
                danger_at_next_time = get_blast_mask(arena, [b for b in simulated_bombs if b[1] == next_time])
                
                # 다음 시간에 해당 위치가 안전하다면 큐에 추가
                if not danger_at_next_time[next_pos]:
                    visited.add((next_pos, next_time))
                    queue.append((next_pos, next_time))
                    
    return False

def get_best_escape(self, game_state, valid_actions, bomb_at=None):
    """BFS로 가장 가까운 안전지대 찾기"""
    arena = game_state['field']
    bombs = game_state['bombs']
    _, _, _, start_pos = game_state['self']
    
    # 가상 폭탄 추가
    if bomb_at:
        simulated_bombs = bombs + [(bomb_at, s.BOMB_TIMER)]
    else:
        simulated_bombs = bombs

    # 모든 폭탄의 잠재적 화염 범위 계산
    blast_mask = get_blast_mask(arena, simulated_bombs)
    queue = deque([(start_pos, [])]) # (pos, path)
    visited = set([start_pos])
    
    while queue:
        (cx, cy), path = queue.popleft()
        
        # 현재 위치가 안전하다면(blast_mask 밖) 탈출 경로 반환
        if not blast_mask[cx, cy]:
            if not path: return None # 이미 안전
            return path[0]
        
        if len(path) >= 6: continue # 탐색 깊이 제한 (값을 줄이면 연산량 감소)

        for dx, dy, action in [(0, 1, 'DOWN'), (0, -1, 'UP'), (1, 0, 'RIGHT'), (-1, 0, 'LEFT')]:
            nx, ny = cx + dx, cy + dy
            
            # 이동 가능 조건
            if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and 
                arena[nx, ny] == 0 and (nx, ny) not in visited):
                
                # 폭탄 위치 장애물 처리
                if is_blocked_by_bomb((nx, ny), simulated_bombs): continue
                
                # 첫 스텝은 valid_actions에 있어야 함 (즉, 당장 터지는 곳이 아니어야 함)
                if len(path) == 0 and action not in valid_actions:
                    continue
                    
                visited.add((nx, ny))
                queue.append(((nx, ny), path + [action]))   
    return None

def get_blast_mask(arena, bombs):
    """모든 폭탄의 화염 범위 마킹"""
    mask = np.zeros_like(arena, dtype=bool)
    for (bx, by), t in bombs:
        mask[bx, by] = True
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            for i in range(1, s.BOMB_POWER + 1):
                nx, ny = bx + dx*i, by + dy*i
                if not (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]): break
                if arena[nx, ny] == -1: break
                mask[nx, ny] = True
    return mask

def is_imminent_danger(pos, bombs):
    """현재 위치가 폭탄 화염 범위 내에 있고 타이머가 임박했는지 확인"""
    x, y = pos
    for (bx, by), t in bombs:
        if t > 2: continue # 아직 여유 있음
        # 십자 범위 체크 (BOMB_POWER 고려)
        if (bx == x and abs(by - y) <= s.BOMB_POWER) or \
           (by == y and abs(bx - x) <= s.BOMB_POWER):
             return True
    return False

def is_blocked_by_bomb(pos, bombs):
    for (bx, by), t in bombs:
        if (bx, by) == pos: return True
    return False

def can_trap_enemy(game_state, enemy_pos):
    """폭탄을 설치해서 적의 탈출 경로를 막을 수 있는지 확인"""
    arena = game_state['field']
    ex, ey = enemy_pos
    
    # 적 주변의 빈 공간(탈출구) 수 계산
    escape_routes = 0
    for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
        nx, ny = ex + dx, ey + dy
        if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and arena[nx, ny] == 0:
            escape_routes += 1
    
    # 탈출구가 2개 이하일 때 가두기 시도 (코너에 몰렸을 때)
    if escape_routes <= 2:
        # 내가 폭탄을 놓을 위치가 적의 탈출구 중 하나를 막는지 확인
        my_x, my_y = game_state['self'][3]
        if (abs(my_x - ex) + abs(my_y - ey)) == 1: # 내가 적의 바로 옆에 있다면
            return True

    return False

def get_move_from_target(x, y, target):
    if target is None: return None
    if target == (x, y - 1): return 'UP'
    if target == (x, y + 1): return 'DOWN'
    if target == (x - 1, y): return 'LEFT'
    if target == (x + 1, y): return 'RIGHT'
    return None

def look_for_targets(free_space, start, targets, logger=None):
    if len(targets) == 0: return None
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
        neighbors = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
        shuffle(neighbors)
        for nx, ny in neighbors:
            if (0 <= nx < free_space.shape[0]) and (0 <= ny < free_space.shape[1]) and free_space[nx, ny]:
                if (nx, ny) not in parent_dict:
                    frontier.append((nx, ny))
                    parent_dict[(nx, ny)] = current
                    dist_so_far[(nx, ny)] = dist_so_far[current] + 1
    current = best
    while True:
        if parent_dict[current] == start: return current
        current = parent_dict[current]