"""역색인(Inverted Index).

책 뒤쪽의 "찾아보기"와 같은 구조다.
    "login"  -> ["da4b923"]
    "add"    -> ["da4b923", "77de68d"]

검색할 때 모든 커밋을 처음부터 훑지 않고, 딕셔너리에서 키 하나로
후보 커밋 목록을 바로 꺼낸다.
- 순회 검색: O(N × L)   (N = 커밋 수, L = 메시지 길이)
- 역색인:    O(1) 조회 + O(K) 결과 복사   (K = 결과 개수)
"""


def tokenize(message):
    """커밋 메시지를 공백으로 나누고 소문자로 바꾼 토큰 목록을 돌려준다.

    예: "Add Login feature" -> ["add", "login", "feature"]
    """
    return [token.lower() for token in message.split()]


class InvertedIndex:
    """키(단어 또는 작성자) -> 커밋 hash 목록 을 저장하는 사전."""

    def __init__(self):
        self._table = {}

    def add(self, key, commit_hash):
        """key의 목록 끝에 commit_hash를 추가한다.

        한 메시지에 같은 단어가 두 번 나와도("fix fix") 같은 커밋이
        두 번 들어가지 않도록, 마지막 값과 같으면 넣지 않는다.
        (커밋은 하나씩 순서대로 색인되므로 마지막 값만 보면 충분하다.)
        """
        hashes = self._table.setdefault(key, [])
        if not hashes or hashes[-1] != commit_hash:
            hashes.append(commit_hash)

    def get(self, key):
        """key에 해당하는 커밋 hash 목록(복사본)을 돌려준다. 없으면 빈 리스트."""
        return list(self._table.get(key, []))
