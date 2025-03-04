from argparse import ArgumentParser
from dotenv import load_dotenv
from getpass import getuser
from git.objects import Commit
from git.refs import Head
from git.remote import Remote
from git.repo import Repo
from os import chmod, getenv
from os.path import join, exists
from random import getrandbits
from textwrap import dedent
from typing import NoReturn, Optional

from gp.gitproject import build_git_project


version = "0.0.1"
program = "git-publish"

main_branches = ["main", "master", "development", "develop"]


def main(argv: list[str] = []):
    parser = ArgumentParser(prog=program, description="Publish atomic Git commits.")
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {version}"
    )
    parser.add_argument("-m", "--message-file", action="store")

    args = parser.parse_args(argv)

    load_dotenv()

    if args.message_file:
        update_commit_message_file(args.message_file)
    else:
        install_commit_message_hook()
        publish_changes()


def publish_changes():
    repo = Repo(".", search_parent_directories=True)

    # 1. Stash working directory if dirty
    repo_is_dirty = dirty_working_directory(repo)
    if repo_is_dirty:
        stash(repo)

    # 2. Ensure current branch is a main branch
    if not ensure_main_branch(repo):
        fail(
            f"Current branch must be one of the following branches to publish: #{', '.join(main_branches)}."
        )

    active_branch = repo.active_branch
    tracking_branch = active_branch.tracking_branch()

    if tracking_branch is None:
        fail(f"Current branch {active_branch} is not tracking.")

    remote = repo.remote(tracking_branch.remote_name)

    active_branch_commit = get_head_commit(active_branch)
    tracking_branch_commit = get_head_commit(tracking_branch)
    common_ancestor_commit = get_most_recent_common_ancestor(
        active_branch_commit, tracking_branch_commit
    )

    # 3. Gather all unmerged commits to publish
    commits = collect_commits_between(active_branch_commit, common_ancestor_commit)

    if not commits:
        fail("Nothing to publish.")

    project = build_git_project(remote)

    previous_branch = active_branch
    previous_commit = common_ancestor_commit

    # 4. Go through all commits (from older to newer):
    for commit in reversed(commits):
        # 1. Ensure the commit has a Change-Id field
        commit, change_id = get_or_set_change_id(commit)

        # 2. Rebase the commit onto its updated parent
        commit = update_commit_parent(commit, previous_commit)

        # 3. Create a branch named "{username}/{change_id}" pointing to the commit
        current_branch = create_branch(repo, change_id, commit)

        # 4. Force-push the branch
        push_branch(remote, current_branch)

        title = get_commit_summary(commit)
        commit_message = get_commit_message(commit)
        description = strip_change_id(commit_message)

        # 5. Create or update existing MR/PR with source branch "{username}/{change_id}" to target previous branch
        change_url = project.create_or_update_change(
            change_id, current_branch, previous_branch, title, description
        )

        info(f"{commit.summary}\n  🔗 {change_url}\n")

        previous_branch = current_branch
        previous_commit = commit

        # 6. Delete previous branch locally
        delete_branch(repo, current_branch)

    # 5. Reset master to the original state
    update_branch_reference(active_branch, previous_commit)

    # 6. Unstash if needed
    if repo_is_dirty:
        unstash(repo)


def dirty_working_directory(repo: Repo) -> bool:
    return repo.is_dirty() or bool(repo.untracked_files)


def ensure_main_branch(repo: Repo) -> bool:
    return repo.active_branch.name in main_branches


def get_or_set_change_id(commit: Commit) -> tuple[Commit, str]:
    commit_message = get_commit_message(commit)
    change_id = get_change_id(commit_message)

    if not change_id:
        change_id = create_change_id()
        commit = set_change_id(commit, change_id)

    return commit, change_id


def create_branch(repo: Repo, change_id: str, commit: Commit):
    branch = repo.create_head(change_id, force=True)
    branch.set_commit(commit)
    return branch


def push_branch(remote: Remote, branch: Head):
    refspec = f"refs/heads/{branch.name}:refs/heads/{branch.name}"
    remote.push(refspec, force=True)


def collect_commits_between(top: Commit, bottom: Commit) -> list[Commit]:
    commits: list[Commit] = []
    while top != bottom:
        commits.append(top)
        top = get_commit_parent(top)
    return commits


def get_most_recent_common_ancestor(commit1: Commit, commit2: Commit) -> Commit:
    ancestors = commit1.repo.merge_base(commit1, commit2)
    if len(ancestors) != 1:
        fail(
            f"Commit {commit1.hexsha} and commit {commit2.hexsha} do not have a single common ancestor."
        )
    if not isinstance(ancestors[0], Commit):
        fail(
            f"Ancestor {ancestors[0]} of commit {commit1.hexsha} and commit {commit2.hexsha} is not a commit"
        )
    return ancestors[0]


def get_commit_parent(commit: Commit) -> Commit:
    parents = list(commit.parents)
    if len(parents) > 1:
        fail(f"Merge commit {commit.hexsha} cannot be published.")
    if not parents:
        fail(f"Commit {commit.hexsha} has no parent.")
    return parents[0]


def get_head_commit(head: Head) -> Commit:
    return head.commit


def get_commit_message(commit: Commit) -> str:
    return str(commit.message)


def get_commit_summary(commit: Commit) -> str:
    return str(commit.summary)


def update_commit_message_file(message_file: str):
    with open(message_file, "r+") as file:
        message = file.read()
        change_id = get_change_id(message)

        if not change_id:
            change_id = create_change_id()
            updated_message = append_change_id_in_commit_message(change_id, message)
            file.seek(0)
            file.write(updated_message)
            file.truncate()


def append_change_id_in_commit_message(change_id: str, message: str):
    return f"{message.strip()}\n\nChange-Id: {change_id}\n"


def set_change_id(commit: Commit, change_id: str):
    commit_message = get_commit_message(commit)
    commit_message = append_change_id_in_commit_message(change_id, commit_message)

    return commit.replace(message=commit_message)


def update_commit_parent(commit: Commit, parent: Commit) -> Commit:
    return commit.replace(parents=[parent])


def update_branch_reference(branch: Head, commit: Commit):
    branch.commit = commit


def delete_branch(repo: Repo, branch: Head):
    repo.delete_head(branch, force=True)


def stash(repo: Repo):
    repo.git.stash(
        "push",
        "--include-untracked",
        "--quiet",
        "--message",
        "git-publish temporary stash",
    )


def unstash(repo: Repo):
    repo.git.stash("pop", "--quiet")


def create_change_id():
    user = getenv("GITLAB_BRANCH_PREFIX") or getuser()
    hash = getrandbits(16)
    return f"{user}/{hash:04x}"


def get_change_id(message: str) -> Optional[str]:
    change_id_line = next(
        (line for line in message.splitlines() if line.startswith("Change-Id:")),
        None,
    )
    if not change_id_line:
        return None
    change_id = change_id_line.lstrip("Change-Id:").strip()
    return change_id


def strip_change_id(message: str) -> str:
    lines = [line for line in message.split("\n") if not line.startswith("Change-Id:")]
    return "\n".join(lines).rstrip()


def install_commit_message_hook():
    commit_message_template = dedent(
        """\
        #!/bin/sh
        git publish --message-file "$1"
        """
    )
    git_dir = find_git_dir()
    commit_message_hook_path = join(git_dir, "hooks", "commit-msg")
    if exists(commit_message_hook_path):
        with open(commit_message_hook_path) as file:
            content = file.read()
            if content != commit_message_template:
                raise RuntimeError(
                    f"commit-msg script {commit_message_hook_path} must be removed first"
                )
    else:
        with open(commit_message_hook_path, "w") as file:
            file.write(commit_message_template)
        chmod(commit_message_hook_path, 0o775)
        print("commit-msg hook installed")


def find_git_dir() -> str:
    repo = Repo(".", search_parent_directories=True)
    if not repo.git_dir:
        raise RuntimeError("Not a Git repository")
    return str(repo.git_dir)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"{program} error: {message}")


def info(message: str):
    print(f"{program} info: {message}")
