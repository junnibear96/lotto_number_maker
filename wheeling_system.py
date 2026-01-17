import itertools
import random

def create_wheeling_system(numbers, guarantee=3):
    """
    numbers: 내가 선택한 20개의 번호 리스트
    guarantee: 보장 등수 (3은 5등 보장, 4는 4등 보장 의미)
    """
    
    # 1. 20개 번호로 가능한 모든 6개 조합 생성 (38,760개)
    # 메모리 효율을 위해 제너레이터 대신 리스트로 변환 (규모가 작으므로 괜찮음)
    full_combinations = list(itertools.combinations(numbers, 6))
    
    # 무작위성을 위해 섞기 (매번 다른 조합이 나오도록)
    random.shuffle(full_combinations)
    
    purchased_tickets = []
    
    # 풀이 빌 때까지 반복
    while full_combinations:
        # 2. 리스트의 첫 번째 조합을 구매 확정
        current_ticket = full_combinations.pop(0)
        purchased_tickets.append(current_ticket)
        
        # 3. 커버링 제거 (Filtering)
        # 남은 조합들 중, 방금 뽑은 티켓과 'guarantee' 개수 이상 겹치는 것들을 모두 제거
        # set.intersection을 사용하여 교집합 개수 확인
        current_set = set(current_ticket)
        
        # 리스트 컴프리헨션으로 필터링 (속도 최적화)
        full_combinations = [
            combo for combo in full_combinations 
            if len(current_set.intersection(set(combo))) < guarantee
        ]
        
    return purchased_tickets

# --- 실행 설정 ---
# 예시: 1~20번을 뽑았다고 가정 (실제 사용자 번호 20개로 교체하세요)
my_20_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

# 시스템 가동 (3개 일치 보장 = 5등 보장형)
result_tickets = create_wheeling_system(my_20_numbers, guarantee=3)

print(f"=== 결과 리포트 ===")
print(f"선택 번호 수: {len(my_20_numbers)}개")
print(f"전체 경우의 수: {38760}개")
print(f"압축된 구매 게임 수: {len(result_tickets)}게임")
print(f"예상 비용: {len(result_tickets) * 1000:,}원")
print("-" * 30)
for i, ticket in enumerate(result_tickets):
    print(f"게임 {i+1}: {sorted(ticket)}")