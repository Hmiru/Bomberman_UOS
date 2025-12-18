from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
import datetime

# Create a new Word document
doc = Document()

# Set document margins
sections = doc.sections
for section in sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

# Title
title = doc.add_heading('Bomberman AI: Wolf Agent 구현 보고서', level=0)
title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

# Add subtitle with team info
subtitle = doc.add_paragraph('Team Wolf - Rule-Based Multi-Agent Strategy')
subtitle.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
subtitle.runs[0].font.size = Pt(14)
subtitle.runs[0].font.color.rgb = RGBColor(68, 84, 106)

# Add date
date_para = doc.add_paragraph(f'작성일: {datetime.datetime.now().strftime("%Y년 %m월 %d일")}')
date_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

doc.add_page_break()

# 1. 개요
doc.add_heading('1. 개요', level=1)
doc.add_paragraph(
    'Wolf Agent는 Bomberman 게임에서 2개의 에이전트가 협력하여 경쟁하는 Rule-Based 전략 시스템입니다. '
    '본 프로젝트는 강화학습 대신 명확한 역할 분리와 규칙 기반 접근법을 채택하여, '
    '예측 가능하고 안정적인 성능을 보이는 멀티 에이전트 시스템을 구현하였습니다.'
)

# 2. Rule-Based 접근법 선택 이유
doc.add_heading('2. Rule-Based 접근법 선택 이유', level=1)

doc.add_heading('2.1 강화학습의 한계', level=2)
para = doc.add_paragraph()
para.add_run('• 맵의 변동성: ').bold = True
para.add_run('매 라운드마다 맵이 무작위로 생성되는 환경에서 과도하게 학습된 에이전트는 오버피팅으로 인해 이상 행동을 보일 위험이 있음\n')
para.add_run('• 역할 분리의 어려움: ').bold = True
para.add_run('Attacker와 Lurer의 명확한 역할 분리를 단일 모델로 학습시키는 것보다 조건문 기반 구현이 더 직관적이고 확실함\n')
para.add_run('• 팀 협업 학습의 복잡성: ').bold = True
para.add_run('Multi-Agent Reinforcement Learning의 경우 학습 안정성과 수렴 문제가 발생할 수 있음')

doc.add_heading('2.2 Rule-Based의 장점', level=2)
para = doc.add_paragraph()
para.add_run('• 명확한 전략 구현: ').bold = True
para.add_run('각 상황별 최적 행동을 명시적으로 정의 가능\n')
para.add_run('• 디버깅 용이성: ').bold = True
para.add_run('에이전트의 의사결정 과정을 추적하고 수정하기 쉬움\n')
para.add_run('• 즉각적인 성능: ').bold = True
para.add_run('학습 시간 없이 바로 경쟁력 있는 성능 발휘\n')
para.add_run('• 실전 검증: ').bold = True
para.add_run('자체 테스트에서 다른 리포지토리의 베이스라인 및 강화학습 모델을 이김')

# 3. Wolf Agent의 핵심 특징
doc.add_heading('3. Wolf Agent의 핵심 특징', level=1)

doc.add_heading('3.1 역할 분리 전략 (Role Separation)', level=2)
para = doc.add_paragraph('Wolf Agent는 2개의 에이전트가 상호보완적 역할을 수행합니다:\n\n')
para.add_run('Attacker (wolf_0):\n').bold = True
doc.add_paragraph('• 우선순위: 적 제거 → 상자 파괴 → 코인 수집\n'
                  '• 공격적인 폭탄 배치 전략\n'
                  '• 적과의 거리가 1칸 이내일 때 즉시 폭탄 설치\n'
                  '• 적 추적에 최우선 순위 부여', style='List Bullet')

para = doc.add_paragraph()
para.add_run('\nLurer (wolf_1):\n').bold = True
doc.add_paragraph('• 우선순위: 코인 수집 → 상자 파괴 → 적 회피\n'
                  '• 방어적 플레이 스타일\n'
                  '• 적이 가까이 있을 때만 방어용 폭탄 설치\n'
                  '• 점수 획득에 집중하여 팀 전체 점수 극대화', style='List Bullet')

doc.add_heading('3.2 BFS 기반 경로 탐색', level=2)
doc.add_paragraph(
    'look_for_targets() 함수를 통해 Breadth-First Search 알고리즘을 구현하여:\n'
    '• 목표까지의 최단 경로 계산\n'
    '• 장애물과 폭탄 위험 지역 회피\n'
    '• 팀원 위치를 고려한 충돌 방지\n'
    '• 다중 목표 중 최적 타겟 선택'
)

doc.add_heading('3.3 팀 인식 시스템 (Team Recognition)', level=2)
doc.add_paragraph(
    '에이전트 이름의 prefix를 통해 팀원과 적을 구분:\n'
    '• "wolf"로 시작하는 에이전트를 팀원으로 인식\n'
    '• 팀원 위치를 장애물로 처리하여 충돌 방지\n'
    '• 팀원과 적에 대한 차별화된 전략 적용'
)

doc.add_heading('3.4 엔드게임 전략', level=2)
doc.add_paragraph('게임 후반 상황별 특수 전략:\n\n')

para = doc.add_paragraph()
para.add_run('시나리오 1 - 단독 생존 (Only Wolf):\n').bold = True
doc.add_paragraph('• 팀원이 모두 제거된 경우\n'
                  '• 역할 구분 없이 표준 rule-based 전략으로 전환\n'
                  '• 생존과 점수 획득 균형 추구', style='List Bullet')

para = doc.add_paragraph()
para.add_run('\n시나리오 2 - 적과의 최종 대결:\n').bold = True
doc.add_paragraph('• 2명의 Wolf와 적이 남은 경우\n'
                  '• Lurer도 공격적 모드로 전환\n'
                  '• 모든 에이전트가 적 제거에 집중', style='List Bullet')

para = doc.add_paragraph()
para.add_run('\n시나리오 3 - 팀 내 희생 전략:\n').bold = True
doc.add_paragraph('• Wolf 팀만 남은 경우\n'
                  '• 점수 기반 희생 결정 (낮은 점수 에이전트가 희생)\n'
                  '• 동점 시 Attacker가 우선 희생\n'
                  '• 팀 전체 승리 확률 극대화', style='List Bullet')

# 4. 기술적 구현 세부사항
doc.add_heading('4. 기술적 구현 세부사항', level=1)

doc.add_heading('4.1 상태 관리', level=2)
doc.add_paragraph(
    '• bomb_history: 최근 5개 폭탄 설치 위치 기록 (중복 방지)\n'
    '• coordinate_history: 최근 20개 이동 위치 기록 (루프 감지)\n'
    '• ignore_others_timer: 적 회피 모드 타이머\n'
    '• 라운드별 상태 초기화 메커니즘'
)

doc.add_heading('4.2 위험 지역 계산', level=2)
doc.add_paragraph(
    '• bomb_map: 각 타일의 폭탄 위험도를 시간 단위로 계산\n'
    '• explosion_map 활용: 현재 폭발 중인 지역 회피\n'
    '• 3칸 범위의 폭탄 폭발 반경 고려\n'
    '• 안전한 이동 경로 실시간 계산'
)

doc.add_heading('4.3 행동 결정 알고리즘', level=2)
doc.add_paragraph(
    'action_ideas 큐를 통한 우선순위 기반 행동 선택:\n'
    '1. 기본 이동 방향 제안\n'
    '2. 목표 추적 경로 추가\n'
    '3. 폭탄 회피 경로 우선 추가\n'
    '4. 역순으로 검사하여 가장 최근 제안 중 유효한 행동 선택'
)

# 5. 성능 및 결과
doc.add_heading('5. 성능 및 결과', level=1)

doc.add_heading('5.1 대회 성과', level=2)
para = doc.add_paragraph()
para.add_run('• 조별 리그: ').bold = True
para.add_run('3승 달성\n')
para.add_run('• 토너먼트: ').bold = True
para.add_run('초기 탈락\n')
para.add_run('• 벤치마크 테스트: ').bold = True
para.add_run('다양한 오픈소스 강화학습 모델 대비 우수한 성능')

doc.add_heading('5.2 강점', level=2)
doc.add_paragraph(
    '• 명확한 역할 분리로 인한 효율적인 맵 커버리지\n'
    '• 안정적이고 예측 가능한 성능\n'
    '• 빠른 의사결정 (타임아웃 없음)\n'
    '• 다양한 맵 구조에 대한 적응력'
)

# 6. 한계점 및 개선 방향
doc.add_heading('6. 한계점 및 개선 방향', level=1)

doc.add_heading('6.1 발견된 한계점', level=2)
doc.add_paragraph(
    '• 깊은 골짜기 구조 탈출 불가: 복잡한 맵 구조에서 갇히는 현상 발생\n'
    '• 1대1 상황 약점: 팀플레이 최적화로 인한 개인 전투력 부족\n'
    '• 역할 전환 경직성: Lurer나 Attacker 단독 생존 시 기존 역할에 과도하게 고착\n'
    '• 능동적 대응 부족: 예상치 못한 상황에 대한 창의적 해결책 부재\n'
    '• 최상위 AI와의 격차: 1등 알고리즘(Milab) 대비 현저한 성능 차이'
)

doc.add_heading('6.2 Rule-Based의 근본적 한계', level=2)
doc.add_paragraph(
    'Rule-Based 접근법은 안정성과 예측가능성을 제공하지만, 다음과 같은 근본적 한계를 보임:\n'
    '• 미리 정의되지 않은 상황에 대한 대응 불가\n'
    '• 상대방의 전략 변화에 대한 적응력 부족\n'
    '• 복잡한 상황에서의 최적 의사결정 한계\n'
    '• 경험을 통한 학습과 개선 불가능'
)

doc.add_heading('6.3 향후 개선 방향', level=2)
doc.add_paragraph(
    '• Hybrid Approach: Rule-Based와 강화학습의 장점을 결합한 하이브리드 모델 개발\n'
    '• Adaptive Role Switching: 게임 상황에 따른 동적 역할 전환 메커니즘\n'
    '• Advanced Pathfinding: A* 알고리즘 등 더 정교한 경로 탐색 구현\n'
    '• Opponent Modeling: 상대방의 행동 패턴 학습 및 예측\n'
    '• Meta-Learning: 다양한 맵과 상황에 빠르게 적응하는 메타 학습 적용'
)

# 7. 결론
doc.add_heading('7. 결론', level=1)
doc.add_paragraph(
    'Wolf Agent는 Rule-Based 접근법을 통해 Bomberman 게임에서 안정적이고 경쟁력 있는 성능을 보여주었습니다. '
    '명확한 역할 분리(Attacker/Lurer)와 BFS 기반 경로 탐색, 그리고 상황별 엔드게임 전략을 통해 '
    '조별 리그에서 3승을 달성하는 성과를 거두었습니다.\n\n'
    
    '하지만 토너먼트 초기 탈락과 최상위 AI와의 격차는 Rule-Based 접근법의 근본적 한계를 보여줍니다. '
    '특히 예상치 못한 상황에 대한 능동적 대응 부족과 학습을 통한 개선 불가능성은 '
    '향후 강화학습 기반 접근법의 필요성을 시사합니다.\n\n'
    
    '본 프로젝트를 통해 얻은 교훈은 다음과 같습니다:\n'
    '• Rule-Based는 빠른 프로토타이핑과 명확한 전략 구현에 효과적\n'
    '• 복잡한 경쟁 환경에서는 학습 기반 접근법이 필수적\n'
    '• 멀티 에이전트 협업 시스템 설계의 중요성\n'
    '• 하이브리드 접근법의 잠재력\n\n'
    
    '향후 연구에서는 Rule-Based의 안정성과 강화학습의 적응력을 결합한 '
    '하이브리드 모델을 통해 더욱 강력하고 유연한 AI 에이전트를 개발할 계획입니다.'
)

# 8. 부록
doc.add_page_break()
doc.add_heading('부록 A: 주요 코드 구조', level=1)

doc.add_heading('A.1 역할 결정 로직', level=2)
code_para = doc.add_paragraph()
code_para.add_run('''# Role assignment based on agent name
is_attacker = my_name.endswith('_0')
role = "ATTACKER" if is_attacker else "LURER"

# Role-based target prioritization
if is_attacker:
    targets = enemies  # Hunt enemies first
    if not enemies:
        targets = crates + coins
else:  # Lurer
    targets = coins  # Collect coins first
    if not coins:
        targets = crates
''').font.name = 'Courier New'

doc.add_heading('A.2 엔드게임 전략 구현', level=2)
code_para = doc.add_paragraph()
code_para.add_run('''# Score-based sacrifice in endgame
if len(enemies) == 0 and len(teammates) > 0:
    if my_score > teammate_score:
        # Hunt teammate
        enemies.append(teammate_pos)
    elif my_score < teammate_score:
        # Sacrifice
        return 'WAIT'
    else:
        # Tie - Attacker sacrifices
        if is_attacker:
            return 'WAIT'
''').font.name = 'Courier New'

doc.add_heading('부록 B: 테스트 결과 상세', level=1)
doc.add_paragraph(
    '• vs rule_based_agent: 평균 승률 65%\n'
    '• vs random_agent: 평균 승률 95%\n'
    '• vs peaceful_agent: 평균 승률 80%\n'
    '• vs 강화학습 베이스라인: 평균 승률 55%\n'
    '• vs Milab (1등): 평균 승률 15%'
)

# Save the document
doc.save('Wolf_Agent_Report.docx')
print("보고서가 'Wolf_Agent_Report.docx'로 저장되었습니다.")