import os
import pickle
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import random

ACTIONS = ['UP', 'RIGHT', 'DOWN', 'LEFT', 'WAIT', 'BOMB']

# 1. 신경망 모델 정의 (The Brain)
class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(DQN, self).__init__()
        # 간단한 3층 신경망 (입력 -> 은닉 -> 출력)
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, output_size)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)

def setup(self):
    """모델 초기화 및 불러오기"""
    self.input_size = 6  # state_to_features에서 반환하는 특징 개수 (수정 가능)
    self.model = DQN(self.input_size, len(ACTIONS))
    
    # 저장된 모델이 있으면 불러오기
    if not self.train and os.path.isfile("my-saved-model.pt"):
        self.logger.info("Loading model from saved state.")
        self.model.load_state_dict(torch.load("my-saved-model.pt"))
    
    self.model.eval() # 추론 모드 설정

def act(self, game_state: dict) -> str:
    """행동 결정 (Exploration vs Exploitation)"""
    # 1. 상태를 특징 벡터(Tensor)로 변환
    features = state_to_features(game_state)
    features_tensor = torch.from_numpy(features).float().unsqueeze(0)

    # 2. 훈련 중일 때: 엡실론 그리디 (랜덤 탐험)
    # (train.py에서 self.epsilon을 관리한다고 가정)
    if self.train and random.random() < self.epsilon:
        self.logger.debug("Choosing action purely at random.")
        return np.random.choice(ACTIONS, p=[.2, .2, .2, .2, .1, .1])

    # 3. 모델을 통해 행동 예측 (Exploitation)
    with torch.no_grad():
        q_values = self.model(features_tensor)
        action_idx = torch.argmax(q_values).item()
    
    return ACTIONS[action_idx]

def state_to_features(game_state: dict) -> np.array:
    """게임 상태를 신경망에 넣을 숫자로 변환 (The Eye)"""
    if game_state is None:
        return None

    # (예시) 간단한 6가지 특징 추출
    # 1~4: 상하좌우가 막혔는지 (0: 이동가능, 1: 벽/폭탄/적)
    # 5: 가장 가까운 코인/적의 가로 방향 (-1, 0, 1)
    # 6: 가장 가까운 코인/적의 세로 방향 (-1, 0, 1)
    
    arena = game_state['field']
    _, _, _, (x, y) = game_state['self']
    
    # 주변 4방향 정보
    surroundings = []
    for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < arena.shape[0] and 0 <= ny < arena.shape[1]:
            val = arena[nx, ny]
            if val == -1:    # 돌벽 (못 깸) -> -1
                surroundings.append(-1)
            elif val == 1:   # 나무상자 (깰 수 있음) -> 1
                surroundings.append(1)
            else:            # 빈 공간 -> 0
                surroundings.append(0)
        else:
            surroundings.append(-1) # 맵 밖은 돌벽 취급

    # 목표(코인 등) 방향 계산 (단순화된 예시)
    coins = game_state['coins']
    if coins:
        closest_coin = coins[np.argmin([abs(cx-x)+abs(cy-y) for cx, cy in coins])]
        dir_x = np.sign(closest_coin[0] - x)
        dir_y = np.sign(closest_coin[1] - y)
    else:
        dir_x, dir_y = 0, 0

    # 특징 벡터 결합
    features = np.array(surroundings + [dir_x, dir_y])
    return features