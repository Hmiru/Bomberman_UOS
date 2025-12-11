import numpy as np
from collections import deque
from random import shuffle
import settings as s
import heapq

def setup(self):
    """에이전트 초기화"""
    self.logger.debug('Successfully entered setup code')
    np.random.seed()
    self.bomb_history = deque([], 5)
    self.coordinate_history = deque([], 20)
    self.ignore_others_timer = 0
    self.current_round = 0
    # 캐싱 추가
    self.danger_cache = {}
    self.last_game_state_hash = None

def act(self, game_state: dict):
    """메인 행동 결정 함수 - 최적화 버전"""
    # 0. 상태 해시 계산 (캐싱용)
    state_hash = hash((
        tuple(game_state['field'].flatten()),
        tuple(tuple(b) for b in game_state['bombs']),
        game_state['self'][3]
    ))
    
    # 1. 정보 수집
    arena = game_state['field']
    _, score, bombs_left, (x, y) = game_state['self']
    bombs = game_state['bombs']
    bomb_xys = [xy for (xy, t) in bombs]
    
    my_name = game_state['self'][0]
    team_prefix = "totoro"
    enemies = [xy for (n, s, b, xy) in game_state['others'] if team_prefix not in n]

    # 2. [최적화] 빠른 위험 판단 - 즉시 위험한 상황만 체크
    immediate_danger = False
    for (bx, by), t in bombs:
        if t <= 1:  # 1턴 이내 폭발
            # 간단한 거리 체크로 위험 판단
            if (bx == x and abs(by - y) <= s.BOMB_POWER) or \
               (by == y and abs(bx - x) <= s.BOMB_POWER):
                immediate_danger = True
                break
    
    # 3. [긴급 회피] 즉각적인 위험이 있을 때만 정밀 계산
    if immediate_danger:
        # 빠른 탈출 경로 계산
        escape_action = fast_escape(game_state, (x, y))
        if escape_action:
            self.logger.info(f"EMERGENCY ESCAPE: {escape_action}")
            return escape_action
    
    # 4. 기본 이동 가능 타일 계산 (간소화)
    valid_actions = get_valid_actions_fast(game_state, (x, y), bombs)
    
    # 5. 폭탄 설치 가능 여부 (빠른 체크)
    can_place_bomb = bombs_left > 0 and (x, y) not in self.bomb_history
    if can_place_bomb:
        # 간단한 안전성 체크만 수행
        if quick_bomb_safety_check(game_state, (x, y)):
            valid_actions.append('BOMB')
    
    # 6. 역할별 행동 수행
    if my_name.endswith('_0'):
        return act_as_killer_optimized(self, game_state, valid_actions, enemies, bomb_xys)
    else:
        return act_as_lurer_optimized(self, game_state, valid_actions, enemies, bomb_xys)

def fast_escape(game_state, my_pos):
    """빠른 탈출 경로 찾기 - A* 알고리즘 사용"""
    arena = game_state['field']
    bombs = game_state['bombs']
    x, y = my_pos
    
    # 위험 지역 빠르게 계산
    danger_zones = set()
    for (bx, by), t in bombs:
        if t <= 2:  # 2턴 이내 폭발하는 폭탄만
            danger_zones.add((bx, by))
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                for i in range(1, s.BOMB_POWER + 1):
                    nx, ny = bx + dx*i, by + dy*i
                    if not (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]):
                        break
                    if arena[nx, ny] == -1:
                        break
                    danger_zones.add((nx, ny))
    
    # A* 알고리즘으로 안전지대 찾기
    heap = [(0, 0, my_pos, None)]  # (priority, distance, position, first_action)
    visited = set()
    
    while heap:
        _, dist, (cx, cy), first_action = heapq.heappop(heap)
        
        if (cx, cy) in visited:
            continue
        visited.add((cx, cy))
        
        # 안전지대 도달
        if (cx, cy) not in danger_zones and (cx, cy) != my_pos:
            return first_action
        
        # 탐색 깊이 제한
        if dist >= 4:
            continue
        
        for dx, dy, action in [(0, 1, 'DOWN'), (0, -1, 'UP'), (1, 0, 'RIGHT'), (-1, 0, 'LEFT')]:
            nx, ny = cx + dx, cy + dy
            
            if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and 
                arena[nx, ny] == 0 and (nx, ny) not in visited):
                
                # 폭탄 위치 체크
                if any((nx, ny) == bomb_xy for bomb_xy, _ in bombs):
                    continue
                
                # 첫 행동 기록
                next_first_action = first_action if first_action else action
                
                # 휴리스틱: 위험 지역으로부터의 거리
                heuristic = 0 if (nx, ny) not in danger_zones else 10
                priority = dist + 1 + heuristic
                
                heapq.heappush(heap, (priority, dist + 1, (nx, ny), next_first_action))
    
    # 탈출 불가능 - 최선의 선택
    if 'WAIT' in get_valid_actions_fast(game_state, my_pos, bombs):
        return 'WAIT'
    return None

def get_valid_actions_fast(game_state, pos, bombs):
    """빠른 유효 행동 계산"""
    arena = game_state['field']
    x, y = pos
    valid_actions = []
    
    # 즉시 위험한 지역만 체크
    immediate_danger_zones = set()
    for (bx, by), t in bombs:
        if t == 0:  # 바로 터지는 폭탄
            immediate_danger_zones.add((bx, by))
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                for i in range(1, s.BOMB_POWER + 1):
                    nx, ny = bx + dx*i, by + dy*i
                    if not (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]):
                        break
                    if arena[nx, ny] == -1:
                        break
                    immediate_danger_zones.add((nx, ny))
    
    # 이동 가능 확인
    for dx, dy, action in [(0, -1, 'UP'), (0, 1, 'DOWN'), (-1, 0, 'LEFT'), (1, 0, 'RIGHT')]:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and
            arena[nx, ny] == 0 and
            (nx, ny) not in immediate_danger_zones and
            not any((nx, ny) == bomb_xy for bomb_xy, _ in bombs) and
            not any((nx, ny) == other_xy for (n, s, b, other_xy) in game_state['others'])):
            valid_actions.append(action)
    
    # 제자리 대기
    if (x, y) not in immediate_danger_zones:
        valid_actions.append('WAIT')
    
    return valid_actions

def quick_bomb_safety_check(game_state, my_pos):
    """빠른 폭탄 설치 안전성 체크"""
    arena = game_state['field']
    x, y = my_pos
    
    # 주변에 최소 2개 이상의 탈출 경로가 있는지 확인
    escape_routes = 0
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and
            arena[nx, ny] == 0):
            # 그 다음 칸도 체크 (2칸 이상 갈 수 있는지)
            for dx2, dy2 in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx2, ny2 = nx + dx2, ny + dy2
                if (0 <= nx2 < arena.shape[0] and 0 <= ny2 < arena.shape[1] and
                    arena[nx2, ny2] == 0 and (nx2, ny2) != (x, y)):
                    escape_routes += 1
                    break
    
    return escape_routes >= 2

def act_as_killer_optimized(self, game_state, valid_actions, enemies, bomb_xys):
    """최적화된 킬러 전략"""
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    
    # 1. 적이 가까이 있고 폭탄 설치 가능하면 공격
    if enemies and 'BOMB' in valid_actions:
        closest_enemy = min(enemies, key=lambda e: abs(e[0] - x) + abs(e[1] - y))
        dist = abs(closest_enemy[0] - x) + abs(closest_enemy[1] - y)
        
        if dist <= 3:
            self.bomb_history.append((x, y))
            return 'BOMB'
    
    # 2. 목표 추적 (간단한 휴리스틱)
    if enemies:
        target = enemies[0]
        dx = 1 if target[0] > x else -1 if target[0] < x else 0
        dy = 1 if target[1] > y else -1 if target[1] < y else 0
        
        if dx != 0 and ('RIGHT' if dx > 0 else 'LEFT') in valid_actions:
            return 'RIGHT' if dx > 0 else 'LEFT'
        if dy != 0 and ('DOWN' if dy > 0 else 'UP') in valid_actions:
            return 'DOWN' if dy > 0 else 'UP'
    
    # 3. 상자 파괴
    for dx, dy, action in [(0, -1, 'UP'), (0, 1, 'DOWN'), (-1, 0, 'LEFT'), (1, 0, 'RIGHT')]:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and
            arena[nx, ny] == 1 and 'BOMB' in valid_actions):
            self.bomb_history.append((x, y))
            return 'BOMB'
    
    # 4. 안전한 랜덤 이동
    if valid_actions:
        safe_actions = [a for a in valid_actions if a != 'WAIT']
        if safe_actions:
            return np.random.choice(safe_actions)
    
    return 'WAIT' if 'WAIT' in valid_actions else valid_actions[0] if valid_actions else 'WAIT'

def act_as_lurer_optimized(self, game_state, valid_actions, enemies, bomb_xys):
    """최적화된 미끼 전략"""
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    coins = game_state['coins']
    
    # 1. 코인 수집
    if coins:
        closest_coin = min(coins, key=lambda c: abs(c[0] - x) + abs(c[1] - y))
        dx = 1 if closest_coin[0] > x else -1 if closest_coin[0] < x else 0
        dy = 1 if closest_coin[1] > y else -1 if closest_coin[1] < y else 0
        
        if dx != 0 and ('RIGHT' if dx > 0 else 'LEFT') in valid_actions:
            return 'RIGHT' if dx > 0 else 'LEFT'
        if dy != 0 and ('DOWN' if dy > 0 else 'UP') in valid_actions:
            return 'DOWN' if dy > 0 else 'UP'
    
    # 2. 주변 상자 파괴
    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        nx, ny = x + dx, y + dy
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and
            arena[nx, ny] == 1 and 'BOMB' in valid_actions):
            self.bomb_history.append((x, y))
            return 'BOMB'
    
    # 3. 안전한 이동
    if valid_actions:
        safe_actions = [a for a in valid_actions if a != 'WAIT']
        if safe_actions:
            return np.random.choice(safe_actions)
    
    return 'WAIT' if 'WAIT' in valid_actions else valid_actions[0] if valid_actions else 'WAIT'