"""직접 구현한 정렬 알고리즘. (sorted(), list.sort() 사용 금지)

병합 정렬(Merge Sort)을 사용한다.
- 평균 시간복잡도: O(n log n)
- 최악 시간복잡도: O(n log n)   (입력 모양과 상관없이 항상 반씩 나눈다)
- 추가 메모리:     O(n)
- 안정 정렬:       예 (같은 값이면 원래 순서를 유지한다)

비교 기준은 key 함수로 바꿀 수 있다.
    merge_sort(commits, key=lambda c: c.timestamp)  # 날짜 기준
    merge_sort(commits, key=lambda c: c.author)     # 작성자 기준
"""


def merge_sort(items, key):
    """items를 key(item) 오름차순으로 정렬한 "새 리스트"를 돌려준다. 원본은 바꾸지 않는다."""
    if len(items) <= 1:
        return list(items)

    mid = len(items) // 2
    left = merge_sort(items[:mid], key)
    right = merge_sort(items[mid:], key)
    return _merge(left, right, key)


def _merge(left, right, key):
    """이미 정렬된 두 리스트를 하나의 정렬된 리스트로 합친다."""
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        # 오른쪽이 "더 작을 때만" 오른쪽을 먼저 넣는다.
        # 값이 같으면 왼쪽(원래 앞에 있던 것)을 먼저 넣으므로 안정 정렬이 된다.
        if key(right[j]) < key(left[i]):
            result.append(right[j])
            j += 1
        else:
            result.append(left[i])
            i += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
