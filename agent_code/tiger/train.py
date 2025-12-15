import torch
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from collections import deque, namedtuple
from typing import List
import events as e
from .callbacks import state_to_features, ACTIONS
import random

# 학습 하이퍼파라미터
BATCH_SIZE = 32
GAMMA = 0.99
EPSILON_START = 1.0
EPSILON_END = 0.1
EPSILON_DECAY = 0.9995
LEARNING_RATE = 0.001
PLACE_BOMB = "PLACE_BOMB"

Transition = namedtuple('Transition', ('state', 'action', 'next_state', 'reward'))

def setup_training(self):
    """훈련 변수 초기화"""
    self.epsilon = EPSILON_START
    self.memory = deque(maxlen=10000) # 경험 리플레이 메모리
    self.optimizer = optim.Adam(self.model.parameters(), lr=LEARNING_RATE)
    self.round_counter = 0

def game_events_occurred(self, old_game_state: dict, self_action: str, new_game_state: dict, events: List[str]):
    """매 스텝마다 호출: 경험 저장 및 학습"""
    if old_game_state is None or self_action is None:
        return
    if self_action == 'BOMB':
        events.append(PLACE_BOMB) # 이벤트를 기록해둠
    # 1. 데이터 전처리
    state = state_to_features(old_game_state)
    next_state = state_to_features(new_game_state)
    action_idx = ACTIONS.index(self_action)
    reward = reward_from_events(self, events)

    # 2. 메모리에 저장 (Experience Replay)
    self.memory.append(Transition(state, action_idx, next_state, reward))

    # 3. 모델 학습 (Batch Sampling)
    train_step(self)

def end_of_round(self, last_game_state: dict, last_action: str, events: List[str]):
    """라운드 종료 시 호출: 마지막 경험 저장 및 모델 저장"""
    # 마지막 상태 저장
    state = state_to_features(last_game_state)
    action_idx = ACTIONS.index(last_action)
    reward = reward_from_events(self, events)
    self.memory.append(Transition(state, action_idx, None, reward)) # 종료 상태는 None

    # 학습 및 엡실론 감소
    train_step(self)
    if self.epsilon > EPSILON_END:
        self.epsilon *= EPSILON_DECAY

    # 모델 저장 (PyTorch 방식)
    torch.save(self.model.state_dict(), "my-saved-model.pt")
    self.round_counter += 1

def train_step(self):
    """실제 신경망 학습 로직"""
    if len(self.memory) < BATCH_SIZE:
        return

    # 랜덤 배체 추출
    batch = random.sample(self.memory, BATCH_SIZE)
    batch_state = torch.FloatTensor([t.state for t in batch])
    batch_action = torch.LongTensor([t.action for t in batch]).unsqueeze(1)
    batch_reward = torch.FloatTensor([t.reward for t in batch])
    
    # 종료 상태(None)가 아닌 것들만 골라냄
    non_final_mask = torch.tensor(tuple(map(lambda s: s.next_state is not None, batch)), dtype=torch.bool)
    non_final_next_states = torch.FloatTensor([t.next_state for t in batch if t.next_state is not None])

    # 1. 예측 Q값 계산 (Q(s, a))
    current_q_values = self.model(batch_state).gather(1, batch_action)

    # 2. 목표 Q값 계산 (R + gamma * max Q(s', a'))
    next_q_values = torch.zeros(BATCH_SIZE)
    if len(non_final_next_states) > 0:
        next_q_values[non_final_mask] = self.model(non_final_next_states).max(1)[0].detach()
    
    expected_q_values = batch_reward + (next_q_values * GAMMA)

    # 3. 손실 함수 계산 (MSE Loss) 및 역전파
    loss = F.mse_loss(current_q_values.squeeze(), expected_q_values)
    
    self.optimizer.zero_grad()
    loss.backward()
    self.optimizer.step()
    
def reward_from_events(self, events: List[str]) -> int:
    reward_sum = 0
    
    # [보상]
    if e.COIN_COLLECTED in events: reward_sum += 10
    if e.KILLED_OPPONENT in events: reward_sum += 50
    if e.CRATE_DESTROYED in events: reward_sum += 20  # 상자 깨기 보상 강화
    
    # [패널티]
    if e.GOT_KILLED in events or e.KILLED_SELF in events: reward_sum -= 100
    if e.INVALID_ACTION in events: reward_sum -= 5
    
    # [중요] 쉬지 말고 움직여라!
    if e.WAITED in events: reward_sum -= 1  # 패널티 강화 (-0.3 -> -1)
    
    return reward_sum