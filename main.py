"""Mini Git 엔트리 포인트 (CLI / REPL).

실행: python main.py

mini-git> 프롬프트에서
    입력 받기 -> 파싱(parse_line) -> 실행(MiniGitCLI.execute) -> 결과 출력
을 exit/quit 이 나올 때까지 반복한다.

이 파일은 "입력을 해석하고 결과를 글자로 보여주는 일"만 한다.
실제 동작은 minigit/repository.py 의 Repository가 맡는다.
"""

import shlex

from minigit.repository import MiniGitError, Repository

PROMPT = "mini-git> "
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

USAGE = {
    "init": "INIT <user_name>",
    "branch": "BRANCH <branch_name>",
    "switch": "SWITCH <branch_name>",
    "commit": "COMMIT <message>",
    "log": "LOG [--sort-by=date|author]",
    "path": "PATH <commit1> <commit2>",
    "ancestors": "ANCESTORS <commit_hash>",
    "search": "SEARCH <keyword> | SEARCH --author=<name>",
}


def parse_line(line):
    """한 줄을 (명령어, 인자 목록)으로 나눈다.

    - 명령어는 소문자로 바꿔 대소문자를 구분하지 않는다.
    - shlex로 나누므로 "Add login feature" 처럼 따옴표 안의 공백은 한 덩어리로 유지된다.
    - 따옴표 짝이 맞지 않으면 ValueError가 난다.
    """
    tokens = shlex.split(line)
    if not tokens:
        return None, []
    return tokens[0].lower(), tokens[1:]


def format_commit(repo, commit):
    """LOG에서 커밋 하나를 보여주는 3줄 형식."""
    labels = repo.branches_at(commit.hash)
    decoration = f" [{', '.join(labels)}]" if labels else ""
    parents = ", ".join(commit.parents) if commit.parents else "(none)"
    return (
        f"commit {commit.hash} ({commit.author}, {commit.timestamp.strftime(TIME_FORMAT)}){decoration}\n"
        f"    parents: {parents}\n"
        f"    {commit.message}"
    )


def format_commit_list(title, commits, empty_message):
    """SEARCH / ANCESTORS 결과처럼 '- hash: message (author)' 목록을 만든다.

    title 안의 {count} 자리에 "1 commit" / "3 commits" 가 들어간다.
    """
    if not commits:
        return empty_message
    unit = "commit" if len(commits) == 1 else "commits"
    lines = [title.format(count=f"{len(commits)} {unit}")]
    for c in commits:
        lines.append(f"- {c.hash}: {c.message} ({c.author})")
    return "\n".join(lines)


class MiniGitCLI:
    """명령어 이름 -> 처리 함수 를 연결하고, 결과를 문자열로 돌려준다."""

    def __init__(self):
        self.repo = None
        self.handlers = {
            "init": self.cmd_init,
            "branch": self.cmd_branch,
            "switch": self.cmd_switch,
            "commit": self.cmd_commit,
            "log": self.cmd_log,
            "path": self.cmd_path,
            "ancestors": self.cmd_ancestors,
            "search": self.cmd_search,
            "help": self.cmd_help,
        }

    def execute(self, line):
        """한 줄을 실행하고 출력할 문자열을 돌려준다. 모든 에러도 여기서 문자열이 된다."""
        try:
            command, args = parse_line(line)
        except ValueError:
            return "Invalid args (check your quotes)"
        if command is None:
            return ""
        handler = self.handlers.get(command)
        if handler is None:
            return f"Unknown command: {command} (type HELP)"
        if command not in ("init", "help") and self.repo is None:
            return "Not initialized. Run INIT <user_name> first."
        try:
            return handler(args)
        except MiniGitError as error:
            message = str(error)
            if message == "Invalid args":
                message += f"\nUsage: {USAGE[command]}"
            return message

    # ---------------- 저장소 / 브랜치 ----------------
    def cmd_init(self, args):
        if not args:
            raise MiniGitError("Invalid args")
        user = " ".join(args)
        if self.repo is not None:
            # 이미 있는 기록은 그대로 두고 사용자만 바꾼다 (여러 작성자 실습용).
            self.repo.user = user
            return f"Repository already initialized.\nCurrent user: {user}"
        self.repo = Repository(user)
        return f"Initialized repository.\nCurrent branch: main\nCurrent user: {user}"

    def cmd_branch(self, args):
        if len(args) != 1:
            raise MiniGitError("Invalid args")
        self.repo.create_branch(args[0])
        return f"Created branch: {args[0]}"

    def cmd_switch(self, args):
        if len(args) != 1:
            raise MiniGitError("Invalid args")
        self.repo.switch(args[0])
        return f"Switched to branch: {args[0]}"

    def cmd_commit(self, args):
        message = " ".join(args).strip()
        if not message:
            raise MiniGitError("Invalid args")
        commit_hash = self.repo.commit(message)
        return f"[{self.repo.head} {commit_hash}] {message}"

    # ---------------- 로그 / 탐색 ----------------
    def cmd_log(self, args):
        if not args:
            commits = self.repo.log_topological()
        elif len(args) == 1 and args[0].lower().startswith("--sort-by="):
            commits = self.repo.log_sorted(args[0].split("=", 1)[1].lower())
        else:
            raise MiniGitError("Invalid args")
        if not commits:
            return "No commits yet."
        return "\n".join(format_commit(self.repo, c) for c in commits)

    def cmd_path(self, args):
        if len(args) != 2:
            raise MiniGitError("Invalid args")
        path = self.repo.path(args[0], args[1])
        if path is None:
            return "No path"
        return "Path: " + " -> ".join(path)

    def cmd_ancestors(self, args):
        if len(args) != 1:
            raise MiniGitError("Invalid args")
        found = self.repo.ancestors(args[0])
        return format_commit_list(
            f"Ancestors of {args[0]} ({{count}}):", found, f"No ancestors: {args[0]} is a root commit"
        )

    # ---------------- 검색 ----------------
    def cmd_search(self, args):
        if not args:
            raise MiniGitError("Invalid args")
        if args[0].lower().startswith("--author="):
            if len(args) != 1:
                raise MiniGitError("Invalid args")
            name = args[0].split("=", 1)[1]
            if not name:
                raise MiniGitError("Invalid args")
            found = self.repo.search_author(name)
        else:
            found = self.repo.search_keyword(" ".join(args))
        return format_commit_list("Found {count}:", found, "No commits found.")

    def cmd_help(self, args):
        return "Commands:\n" + "\n".join(f"  {u}" for u in USAGE.values()) + "\n  EXIT | QUIT"


def main():
    """REPL: 입력 -> 파싱 -> 실행 -> 출력 을 반복한다."""
    cli = MiniGitCLI()
    while True:
        try:
            line = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in ("exit", "quit"):
            break
        output = cli.execute(line)
        if output:
            print(output)
    print("Bye!")


if __name__ == "__main__":
    main()
