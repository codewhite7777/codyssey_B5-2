"""Mini Git 저장소: 커밋 그래프, 브랜치, HEAD, 사용자, 역색인을 관리한다.

책임 분리
- commits      : hash -> Commit          커밋 저장소 (해시맵, O(1) 조회)
- children     : hash -> [자식 hash]     부모->자식 방향 간선 (LOG, PATH용)
- branches     : 브랜치 이름 -> 끝(tip) 커밋 hash
- head         : 현재 브랜치 "이름" (실제 Git처럼 브랜치를 가리킨다)
- user         : 현재 사용자 (새 커밋의 author)
- keyword_index, author_index : 검색용 역색인

알고리즘(탐색/정렬/색인)은 graph.py, sorting.py, index.py 에 따로 있고
이 클래스는 그것들을 "어떤 데이터로 호출할지"만 정한다.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime

from minigit.graph import find_ancestors, shortest_path, topological_order
from minigit.index import InvertedIndex, tokenize
from minigit.sorting import merge_sort


class MiniGitError(Exception):
    """사용자에게 그대로 보여줄 에러 메시지 (예: Unknown branch: dev)."""


@dataclass
class Commit:
    """커밋 노드 하나. 그래프에서 '점'에 해당한다."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: list = field(default_factory=list)  # 0개 이상의 부모 hash


class Repository:
    """INIT 으로 만들어지는 저장소 하나."""

    def __init__(self, user):
        self.user = user
        self.commits = {}
        self.children = {}
        self.branches = {"main": None}  # 첫 커밋 전에는 가리키는 커밋이 없다
        self.head = "main"
        self.keyword_index = InvertedIndex()
        self.author_index = InvertedIndex()
        self._counter = 0  # 해시 생성용 증가 카운터

    # ------------------------------------------------------------------
    # 조회 도우미
    # ------------------------------------------------------------------
    def head_commit(self):
        """HEAD(현재 브랜치)가 가리키는 커밋 hash. 아직 커밋이 없으면 None."""
        return self.branches[self.head]

    def get_commit(self, commit_hash):
        """hash로 커밋을 찾는다. 해시맵이라 O(1). 없으면 에러."""
        if commit_hash not in self.commits:
            raise MiniGitError(f"Unknown commit: {commit_hash}")
        return self.commits[commit_hash]

    def branches_at(self, commit_hash):
        """이 커밋을 끝으로 가리키는 브랜치 이름 목록 (현재 브랜치는 'HEAD -> ' 표시)."""
        labels = []
        for name, tip in self.branches.items():
            if tip == commit_hash:
                labels.append(f"HEAD -> {name}" if name == self.head else name)
        return labels

    def _parents_of(self, commit_hash):
        return self.commits[commit_hash].parents

    def _children_of(self, commit_hash):
        return self.children[commit_hash]

    def _undirected_neighbors(self, commit_hash):
        """PATH용: 부모와 자식을 모두 이웃으로 본다 (무방향 간선)."""
        return self._parents_of(commit_hash) + self._children_of(commit_hash)

    # ------------------------------------------------------------------
    # 저장소 / 브랜치 관리
    # ------------------------------------------------------------------
    def create_branch(self, name):
        """현재 HEAD 커밋을 가리키는 새 브랜치를 만든다."""
        if name in self.branches:
            raise MiniGitError(f"Branch already exists: {name}")
        self.branches[name] = self.head_commit()

    def switch(self, name):
        """HEAD를 다른 브랜치로 옮긴다."""
        if name not in self.branches:
            raise MiniGitError(f"Unknown branch: {name}")
        self.head = name

    def _new_hash(self):
        """세션 안에서 절대 겹치지 않는 7자리 hash를 만든다.

        카운터(1, 2, 3...)를 SHA-1에 넣고 앞 7자리를 쓴다.
        - 같은 순서로 실행하면 항상 같은 hash가 나온다 (재현성)
        - 혹시 7자리가 겹치면 카운터를 하나 더 올려 다시 만든다 (중복 0 보장)
        """
        while True:
            self._counter += 1
            candidate = hashlib.sha1(str(self._counter).encode()).hexdigest()[:7]
            if candidate not in self.commits:
                return candidate

    def commit(self, message):
        """현재 HEAD를 부모로 하는 새 커밋을 만들고 hash를 돌려준다.

        순서: hash 생성 -> 저장소 등록 -> 부모의 children 갱신
              -> 브랜치를 새 커밋으로 이동 -> 역색인 갱신
        """
        parent = self.head_commit()
        parents = [parent] if parent is not None else []

        new = Commit(
            hash=self._new_hash(),
            message=message,
            author=self.user,
            timestamp=datetime.now(),
            parents=parents,
        )
        self.commits[new.hash] = new
        self.children[new.hash] = []
        for p in parents:
            self.children[p].append(new.hash)

        self.branches[self.head] = new.hash

        # 커밋이 "만들어지는 순간" 바로 색인한다 -> 검색할 때는 조회만 하면 된다.
        for word in tokenize(message):
            self.keyword_index.add(word, new.hash)
        self.author_index.add(self.user.lower(), new.hash)
        return new.hash

    # ------------------------------------------------------------------
    # 로그 / 탐색
    # ------------------------------------------------------------------
    def log_topological(self):
        """부모가 항상 자식보다 먼저 나오는 커밋 목록 (위상 정렬)."""
        order = topological_order(list(self.commits), self._parents_of, self._children_of)
        return [self.commits[h] for h in order]

    def log_sorted(self, by):
        """date 또는 author 기준으로 정렬한 커밋 목록 (직접 구현한 병합 정렬).

        입력을 생성 순서로 넘기고 병합 정렬은 안정 정렬이므로,
        기준 값이 같으면 먼저 만든 커밋이 먼저 나온다.
        """
        keys = {
            "date": lambda c: c.timestamp,
            "author": lambda c: c.author.lower(),
        }
        if by not in keys:
            raise MiniGitError("Invalid args")
        return merge_sort(list(self.commits.values()), keys[by])

    def path(self, start, goal):
        """두 커밋 사이 최단 경로 (무방향 간선 기준). 없으면 None."""
        self.get_commit(start)
        self.get_commit(goal)
        return shortest_path(start, goal, self._undirected_neighbors)

    def ancestors(self, commit_hash):
        """해당 커밋에서 부모 방향으로 도달 가능한 모든 조상 커밋 목록."""
        self.get_commit(commit_hash)
        return [self.commits[h] for h in find_ancestors(commit_hash, self._parents_of)]

    # ------------------------------------------------------------------
    # 검색 (역색인 기반)
    # ------------------------------------------------------------------
    def search_keyword(self, keyword):
        """키워드가 들어간 커밋 목록.

        키워드가 여러 단어("login feature")면 모든 단어가 들어간 커밋만 고른다.
        """
        words = tokenize(keyword)
        if not words:
            raise MiniGitError("Invalid args")
        result = self.keyword_index.get(words[0])
        for word in words[1:]:
            others = set(self.keyword_index.get(word))
            result = [h for h in result if h in others]
        return [self.commits[h] for h in result]

    def search_author(self, name):
        """특정 작성자의 커밋 목록 (대소문자 구분 없음)."""
        return [self.commits[h] for h in self.author_index.get(name.lower())]
