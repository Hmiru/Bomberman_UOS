# Totoro Agent 전략 가이드

## 현재 구현 상태 분석

### 팀 인식 시스템 ✅
- `totoro` 접두사를 가진 에이전트를 팀으로 인식
- 적과 팀원을 명확히 구분
- 팀킬 방지 로직 구현됨

### 역할 분담 시스템 ✅ 
- **Killer (Agent_0)**: 적 추적 및 제거 담당
- **Lurer (Agent_1)**: 코인 수집 및 유인 담당
- 이름 끝자리로 역할 자동 할당

### 현재 강점
1. **팀 협력**: rule_based와 달리 팀원을 인식하고 팀킬 방지
2. **역할 분담**: 명확한 역할로 효율적 플레이
3. **안전 체크**: `is_safe_to_bomb_strict()` 함수로 폭탄 설치 전 철저한 안전 확인
4. **긴급 탈출**: 위험 감지 시 즉시 탈출 모드
5. **1대1 전략**: 점수 우위 시 자폭 전략

### 현재 약점 및 개선 필요 사항

#### 1. 팀 간 소통 부재
- Killer와 Lurer가 서로의 위치/상태를 고려하지 않음
- 협동 공격이나 연계 플레이 없음

#### 2. 유인 전략 미흡
- Lurer가 단순히 도망만 가고 실제 유인 역할 수행 못함
- 계획적인 함정 설치 없음

#### 3. 예측 능력 부족
- 적의 다음 이동 예측 없음
- 폭탄 연쇄 반응 활용 못함

## 개선 전략

### 1. 팀 시너지 강화

#### A. 위치 기반 협력
```python
def get_teammate_position(game_state):
    """팀원 위치 파악"""
    my_name = game_state['self'][0]
    team_prefix = "totoro"
    
    for name, score, bombs, xy in game_state['others']:
        if team_prefix in name and name != my_name:
            return xy
    return None

def coordinate_attack(self, game_state, enemy_pos, teammate_pos):
    """협동 공격 계획"""
    # 양쪽에서 포위
    # Killer는 정면, Lurer는 측면/후면
```

#### B. 역할 동적 전환
```python
def should_switch_roles(game_state):
    """상황에 따라 역할 전환"""
    # 예: Lurer가 적과 가까이 있고 유리한 위치면 공격
    # Killer가 코인 근처에 있으면 수집
```

### 2. 고급 유인 전략

#### A. 함정 설치
```python
def setup_trap(self, game_state, enemy_pos):
    """적을 특정 위치로 유인하여 함정 설치"""
    # 1. 막다른 길로 유인
    # 2. 탈출로 차단
    # 3. 폭탄 타이밍 계산
```

#### B. 미끼 활용
```python
def act_as_bait(self, game_state):
    """의도적으로 약해 보이기"""
    # 도망가는 척하며 원하는 위치로 유도
    # 팀원이 매복할 위치로 이끌기
```

### 3. 예측 시스템 구현

#### A. 적 이동 예측
```python
def predict_enemy_movement(enemy_pos, enemy_history):
    """적의 다음 이동 예측"""
    # 과거 이동 패턴 분석
    # BFS 경로 예측 (rule_based는 BFS 사용)
    # 목표물 기반 예측 (코인, 상자 등)
```

#### B. 폭탄 연쇄 계획
```python
def plan_chain_explosion(bombs, crates, enemies):
    """연쇄 폭발 최적 위치 계산"""
    # 현재 폭탄 위치 분석
    # 상자 파괴 시 연쇄 가능성
    # 적 이동 경로 차단
```

### 4. 상황별 전략 매트릭스

| 상황 | Killer 행동 | Lurer 행동 |
|------|------------|-----------|
| 게임 초반 | 중앙 진출, 상자 파괴 | 외곽 코인 수집 |
| 적 2명 생존 | 가까운 적 추적 | 먼 적 견제/코인 |
| 적 1명 생존 | 공격 집중 | 탈출로 차단 |
| 코인 많음 | 적 견제 | 코인 독점 |
| 코인 없음 | 적 제거 우선 | 상자 파괴 |

### 5. 승률 향상을 위한 핵심 개선점

#### 즉시 구현 가능한 개선
1. **팀원 위치 추적**: 서로의 위치 파악하여 협동
2. **적 이동 패턴 학습**: 최근 3-5 스텝 기록
3. **동적 역할 전환**: 상황에 따라 역할 바꾸기

#### 중기 개선 목표
1. **함정 시스템**: 계획적 유인 및 포위
2. **연쇄 폭발**: 폭탄 타이밍 최적화
3. **맵 컨트롤**: 구역 장악 전략

#### 장기 개선 목표
1. **학습 기반 예측**: 상대 플레이 스타일 학습
2. **메타 전략**: 게임 단계별 전략 전환
3. **심리전**: 의도적 패턴 생성 후 변경

## 테스트 및 평가

### 성능 지표
- 승률: 목표 50% 이상
- 평균 점수: 팀 합산 점수
- 생존 시간: 각 에이전트별
- 킬 수: Killer 성과
- 코인 수집: Lurer 성과

### 테스트 시나리오
```bash
# 기본 2v2 테스트
python main.py play --agents totoro totoro rule_based_agent rule_based_agent --n-rounds 100 --no-gui

# 다양한 시나리오
python main.py play --agents totoro totoro rule_based_agent rule_based_agent --scenario classic
python main.py play --agents totoro totoro rule_based_agent rule_based_agent --scenario coin-heaven
```

### 디버깅 및 분석
- 로그 분석으로 의사결정 과정 추적
- 리플레이로 전략 실패 원인 분석
- 각 역할별 효율성 측정

## 구현 우선순위

### Phase 1 (즉시 구현)
1. ✅ 팀 인식 시스템
2. ✅ 역할 분담 (Killer/Lurer)
3. ✅ 안전한 폭탄 설치
4. ⬜ 팀원 위치 추적 및 기본 협동

### Phase 2 (단기 목표)
1. ⬜ 적 이동 예측 시스템
2. ⬜ 함정 설치 로직
3. ⬜ 동적 역할 전환

### Phase 3 (중기 목표)
1. ⬜ 연쇄 폭발 계획
2. ⬜ 맵 컨트롤 전략
3. ⬜ 고급 유인 전술

### Phase 4 (장기 목표)
1. ⬜ 머신러닝 기반 예측
2. ⬜ 메타 게임 전략
3. ⬜ 적응형 전략 시스템

## 승률 50% 달성 로드맵

### 현재 예상 승률: ~30-35%
- 기본적인 팀 인식과 역할 분담만 구현됨
- Rule-based의 개인 플레이가 더 안정적

### 목표 달성 필요 조건
1. **팀원 간 협동** (+10-15%)
   - 위치 공유 및 포위 공격
   - 연계 플레이

2. **예측 시스템** (+10%)
   - Rule-based의 BFS 패턴 예측
   - 함정 설치

3. **최적화된 역할 수행** (+5-10%)
   - Killer의 효율적 추적
   - Lurer의 전략적 유인

총 예상 개선: +25-35% → **목표 승률 55-70% 달성 가능**