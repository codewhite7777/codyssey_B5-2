"""커밋 그래프 탐색 알고리즘 모음.

이 파일의 함수들은 "커밋 저장소"를 직접 알지 못한다.
대신 `neighbors(node)` 처럼 "이 노드에서 갈 수 있는 이웃 목록을 돌려주는 함수"를
인자로 받는다. 그래서 같은 BFS 코드를

- ANCESTORS : 부모 방향으로만 이동 (neighbors = 부모 목록)
- PATH      : 부모 + 자식 양쪽으로 이동 (neighbors = 무방향 이웃 목록)

처럼 이웃 함수만 바꿔서 재사용할 수 있다.
"""

from collections import deque


def bfs_order(start, neighbors):
    """start에서 BFS로 방문한 노드를 방문 순서대로 돌려준다 (start 포함).

    visited 집합으로 이미 본 노드는 다시 넣지 않으므로
    여러 경로로 만나는 노드(merge 등)도 한 번만 나온다.
    시간복잡도: O(V + E)
    """
    visited = {start}
    order = [start]
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in neighbors(node):
            if nxt not in visited:
                visited.add(nxt)
                order.append(nxt)
                queue.append(nxt)
    return order


def bfs_distances(start, neighbors):
    """start에서 각 노드까지의 최소 간선 수를 {노드: 거리} 딕셔너리로 돌려준다.

    도달할 수 없는 노드는 결과에 들어가지 않는다.
    시간복잡도: O(V + E)
    """
    dist = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in neighbors(node):
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                queue.append(nxt)
    return dist


def find_ancestors(start, parents_of):
    """start에서 부모 방향으로 도달 가능한 모든 조상을 가까운 순서대로 돌려준다.

    BFS 방문 순서에서 자기 자신(start)만 빼면 된다.
    """
    return bfs_order(start, parents_of)[1:]


def shortest_path(start, goal, neighbors):
    """start -> goal 최단 경로(간선 수 최소)를 노드 리스트로 돌려준다. 없으면 None.

    최단 경로가 여러 개면 "사전순으로 가장 작은 경로"를 고른다.

    방법 (2단계):
      1) goal에서 BFS를 돌려 모든 노드의 "goal까지 남은 거리"를 구한다.
      2) start에서 출발해, 남은 거리가 정확히 1 줄어드는 이웃 중
         hash가 가장 작은 것을 하나씩 골라 goal까지 걸어간다.

    모든 hash 길이가 같으므로, 앞에서부터 한 칸씩 가장 작은 hash를 고르면
    "a->b->c" 문자열 전체로 비교해도 가장 작은 경로가 된다.
    시간복잡도: O(V + E)
    """
    dist = bfs_distances(goal, neighbors)
    if start not in dist:
        return None

    path = [start]
    node = start
    while node != goal:
        best = None
        for nxt in neighbors(node):
            if dist.get(nxt) == dist[node] - 1 and (best is None or nxt < best):
                best = nxt
        path.append(best)
        node = best
    return path


def topological_order(nodes, parents_of, children_of):
    """부모가 항상 자식보다 먼저 나오는 순서(위상 정렬)를 돌려준다. (Kahn 알고리즘)

    1) 각 커밋의 진입 차수 = 부모 수 를 센다.
    2) 진입 차수가 0인 커밋(부모가 없거나, 부모가 이미 다 출력된 커밋)을 큐에 넣는다.
    3) 큐에서 하나 꺼내 출력하고, 그 자식들의 진입 차수를 1씩 줄인다.
       0이 된 자식은 큐에 넣는다.

    nodes를 생성 순서로 넘기면, 동시에 준비된 커밋끼리는 먼저 만든 것이 먼저 나온다.
    사이클이 있으면 일부 노드의 진입 차수가 끝까지 0이 되지 않으므로 ValueError를 낸다.
    시간복잡도: O(V + E)
    """
    indegree = {node: len(parents_of(node)) for node in nodes}
    queue = deque(node for node in nodes if indegree[node] == 0)
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for child in children_of(node):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    if len(order) != len(indegree):
        raise ValueError("cycle detected: commit graph is not a DAG")
    return order
