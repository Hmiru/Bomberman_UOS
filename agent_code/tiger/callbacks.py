import os
import pickle
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import deque

ACTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT', 'WAIT', 'BOMB']

class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, output_size)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)

def setup(self):
    # 입력 Feature: 주변4방향(4) + 폭탄가능(1) + 힌트방향(4) = 9개로 증가
    self.input_size = 9
    self.model = DQN(self.input_size, len(ACTIONS))
    
    if not self.train and os.path.isfile("my-saved-model.pt"):
        self.logger.info("Loading model from saved state.")
        self.model.load_state_dict(torch.load("my-saved-model.pt"))
    
    self.model.eval()
def act(self, game_state: dict) -> str:
    # 1. 유효/안전 행동 계산
    valid_actions = get_valid_actions(game_state)
    safe_actions = get_safe_actions(game_state, valid_actions)
    
    # 안전한 행동 우선, 없으면 유효한 행동 (죽더라도 벽엔 박지 말자)
    candidate_actions = safe_actions if safe_actions else valid_actions
    # 정말 갈 곳이 없으면 WAIT
    if not candidate_actions: candidate_actions = ['WAIT']

    # Features 추출
    features = state_to_features(game_state)
    features_tensor = torch.from_numpy(features).float().unsqueeze(0)
    
    # 내비게이션 힌트 확인 (5~8번 인덱스)
    # 힌트가 모두 0이면 "목표 지점(상자/코인) 옆에 도착함"을 의미
    has_hint = (sum(features[5:9]) > 0)

    # -----------------------------------------------------------
    # [1] Epsilon Exploration (훈련 중 랜덤 탐험)
    # -----------------------------------------------------------
    if self.train and random.random() < self.epsilon:
        # A. 도착했으면 폭탄 투하! (힌트 없고 + 폭탄 있고 + 안전하면)
        if not has_hint and features[4] == 1 and 'BOMB' in candidate_actions:
            return 'BOMB'
        
        # B. 힌트 방향으로 이동 (Teacher Forcing)
        hint_actions = []
        if features[5] == 1: hint_actions.append('UP')
        if features[6] == 1: hint_actions.append('RIGHT')
        if features[7] == 1: hint_actions.append('DOWN')
        if features[8] == 1: hint_actions.append('LEFT')
        
        # 힌트 방향이 안전하다면 그쪽으로 우선 이동
        best_candidates = [a for a in hint_actions if a in candidate_actions]
        if best_candidates:
            return np.random.choice(best_candidates)
            
        # C. 힌트가 없거나 안전하지 않으면? -> 그냥 아무 안전한 곳으로 이동 (WAIT 금지)
        move_candidates = [a for a in candidate_actions if a != 'WAIT']
        if move_candidates:
            return np.random.choice(move_candidates)
            
        return 'WAIT'

    # -----------------------------------------------------------
    # [2] Model Inference (실전 추론)
    # -----------------------------------------------------------
    with torch.no_grad():
        q_values = self.model(features_tensor)[0]
        
        # Action Masking: 후보군에 없는 행동은 Q값을 -무한대로
        for i, action in enumerate(ACTIONS):
            if action not in candidate_actions:
                q_values[i] = -float('inf')
            
            # [강제] 움직일 수 있다면 'WAIT'는 절대 하지 마라!
            # 모델이 게으름 피우는 것을 방지
            if action == 'WAIT' and len([a for a in candidate_actions if a != 'WAIT']) > 0:
                q_values[i] = -float('inf')

        action_idx = torch.argmax(q_values).item()

    return ACTIONS[action_idx]

def look_for_targets(free_space, start, targets, logger=None):
    """BFS로 가장 가까운 타겟을 찾는 함수 (Rule-Based Agent에서 차용)"""
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
        neighbors = [(x, y) for (x, y) in [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)] if free_space[x, y]]
        random.shuffle(neighbors) # 랜덤성을 섞어서 다양한 길 학습
        for neighbor in neighbors:
            if neighbor not in parent_dict:
                frontier.append(neighbor)
                parent_dict[neighbor] = current
                dist_so_far[neighbor] = dist_so_far[current] + 1
    current = best
    while True:
        if parent_dict[current] == start: return current
        current = parent_dict[current]

def state_to_features(game_state: dict) -> np.array:
    if game_state is None: return None
    arena = game_state['field']
    _, _, bombs_left, (x, y) = game_state['self']
    coins = game_state['coins']
    bombs = game_state['bombs']
    bomb_xys = [xy for (xy, t) in bombs]
    others = [xy for (n, s, b, xy) in game_state['others']]
    
    channels = []
    
    # 1~4. 주변 정보 (상자=1, 빈공간=0, 벽/장애물=-1)
    # 주변에 상자가 있는지 모델이 쉽게 알게 함
    for nx, ny in [(x, y-1), (x+1, y), (x, y+1), (x-1, y)]:
        if not (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]): channels.append(-1)
        elif arena[nx, ny] == 1: channels.append(1) # 상자!
        elif arena[nx, ny] == -1 or (nx, ny) in bomb_xys or (nx, ny) in others: channels.append(-1)
        else: channels.append(0)

    # 5. 폭탄 설치 가능?
    channels.append(1 if bombs_left else 0)

    # 6~9. [NEW] 내비게이션 힌트 (UP, RIGHT, DOWN, LEFT)
    # BFS를 돌려서 다음 스텝이 어디인지 계산하여 Feature로 넣어줌
    # 모델은 이 Feature를 보고 "아, 이 값이 1인 방향으로 가면 좋은거구나"라고 학습함
    cols = range(1, arena.shape[0] - 1)
    rows = range(1, arena.shape[0] - 1)
    crates = [(r, c) for r in cols for c in rows if (arena[r, c] == 1)]
    targets = coins + crates # 코인과 상자를 목표로 설정
    
    free_space = (arena == 0)
    # 현재 폭탄이 있는 자리는 장애물 취급
    for bx, by in bomb_xys: free_space[bx, by] = False
    for ox, oy in others: free_space[ox, oy] = False

    next_step = look_for_targets(free_space, (x, y), targets)
    
    # 힌트 벡터: [UP, RIGHT, DOWN, LEFT] 중 가야할 곳만 1
    hint = [0, 0, 0, 0] 
    if next_step == (x, y-1): hint[0] = 1
    elif next_step == (x+1, y): hint[1] = 1
    elif next_step == (x, y+1): hint[2] = 1
    elif next_step == (x-1, y): hint[3] = 1
    
    channels.extend(hint) # Feature 6,7,8,9

    return np.array(channels)

def get_valid_actions(game_state):
    # (이전과 동일)
    arena = game_state['field']
    _, _, bombs_left, (x, y) = game_state['self']
    others = [xy for (n, s, b, xy) in game_state['others']]
    bomb_xys = [xy for (xy, t) in game_state['bombs']]
    valid = []
    directions = [(x, y-1, 'UP'), (x+1, y, 'RIGHT'), (x, y+1, 'DOWN'), (x-1, y, 'LEFT')]
    for nx, ny, action in directions:
        if (0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1] and 
            arena[nx, ny] == 0 and (nx, ny) not in others and (nx, ny) not in bomb_xys):
            valid.append(action)
    valid.append('WAIT')
    if bombs_left: valid.append('BOMB')
    return valid

def get_safe_actions(game_state, valid_actions):
    # (이전과 동일)
    explosion_map = game_state['explosion_map']
    _, _, _, (x, y) = game_state['self']
    safe = []
    for action in valid_actions:
        nx, ny = x, y
        if action == 'UP': ny -= 1
        elif action == 'DOWN': ny += 1
        elif action == 'LEFT': nx -= 1
        elif action == 'RIGHT': nx += 1
        if 0 <= nx < explosion_map.shape[0] and 0 <= ny < explosion_map.shape[1]:
            if explosion_map[nx, ny] == 0: safe.append(action)
    return safe