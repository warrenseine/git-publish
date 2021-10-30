from argparse import ArgumentParser
from filecmp import cmp
from getpass import getuser
from git import Head, Remote
from git.objects import Commit
from git.repo import Repo
from gitlab.client import Gitlab
from gitlab.v4.objects import Project, ProjectManager
from gitlab.v4.objects.merge_requests import (
    MergeRequest,
    ProjectMergeRequest,
    ProjectMergeRequestManager,
)
from giturlparse import parse as parse_git_url
from os import chmod
from os.path import join, exists
from random import getrandbits
from shutil import copyfile
from typing import NoReturn, Optional


version = "0.0.1"
program = "git-publish"


def main(argv: list[str]):
    parser = ArgumentParser(prog=program, description="Publish atomic Git commits.")
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {version}"
    )
    parser.add_argument("-m", "--message-file", action="store")

    args = parser.parse_args(argv)

    if args.message_file:
        update_commit_message(args.message_file)
    else:
        install_commit_message_hook()
        publish_changes()


def publish_changes():
    # 1. Ensure clean working directory.
    # 2. List existing Merge Requests for my user
    # 3. Check current branch is master (or main)
    # 4. Go through all commits (older to newer) above origin/master:
    #   1. Check the commit have a Change-Id field
    #   2. Remember the name of the current branch
    #   3. Create a branch named "{username}-{change_id}" from the current branch if it doesn't exist
    #   4. Switch to this branch
    #   5. Cherry-pick the commit
    #   6. Force-push the branch
    #   7. Find a Merge Request with source branch "{username}-{change_id}"
    #   8. Update target branch on Merge Request to previous branch if found
    #   9. Create a Merge Request from "{username}-{change_id}" to previous branch otherwise
    #   10. Delete previous branch locally
    repo = Repo(".", search_parent_directories=True)
    if not ensure_clean_working_directory(repo):
        fail(
            f"Working directory is not clean. Clean it first before calling {program}."
        )
    if not ensure_main_branch(repo):
        fail("Current branch must be 'main' or 'master' to publish changes.")

    gitlab = Gitlab.from_config("gitlab.com")

    active_branch = repo.active_branch
    tracking_branch = active_branch.tracking_branch()

    if tracking_branch is None:
        fail(f"Current branch {active_branch} is not tracking.")

    remote = repo.remote(tracking_branch.remote_name)

    commit1 = get_head_commit(active_branch)
    commit2 = get_head_commit(tracking_branch)
    commit3 = get_most_recent_common_ancestor(commit1, commit2)

    commits = collect_commits_between(commit1, commit3)

    if not commits:
        fail("Nothing to publish.")

    project = get_project(gitlab, remote)
    merge_requests = list_merge_requests(project)

    previous_branch = active_branch

    for commit in reversed(commits):
        change_id = get_change_id(get_commit_message(commit))
        if not change_id:
            fail(f"Commit {commit.hexsha} doesn't have a Change-Id field.")

        current_branch = create_branch(repo, change_id, commit)

        refspec = f"refs/heads/{current_branch.name}:refs/heads/{current_branch.name}"
        remote.push(refspec)

        merge_request = find_merge_request(merge_requests, change_id)

        if merge_request:
            update_merge_request(project, merge_request, previous_branch)
        else:
            create_merge_request(project, current_branch, previous_branch)

        previous_branch = current_branch


def ensure_clean_working_directory(repo: Repo) -> bool:
    return not repo.is_dirty() and not repo.untracked_files


def ensure_main_branch(repo: Repo) -> bool:
    return repo.active_branch.name in ["main", "master"]


def find_merge_request(
    merge_requests: list[MergeRequest], source_branch: str
) -> Optional[MergeRequest]:
    for merge_request in merge_requests:
        if merge_request.source_branch == source_branch:
            return merge_request
    return None


def create_branch(repo: Repo, change_id: str, commit: Commit):
    branch = repo.create_head(change_id, force=True)
    branch.set_commit(commit)
    return branch


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
    parents: list[Commit] = commit.parents  # type: ignore
    if len(parents) > 1:
        fail(f"Merge commit {commit.hexsha} cannot be published.")
    if not parents:
        fail(f"Commit {commit.hexsha} has no parent.")
    return parents[0]


def get_head_commit(head: Head) -> Commit:
    return head.commit  # type: ignore


def get_commit_message(commit: Commit) -> str:
    return commit.message  # type: ignore


def list_merge_requests(project: Project) -> list[MergeRequest]:
    merge_requests: ProjectMergeRequestManager = project.mergerequests
    return merge_requests.list()  # type: ignore


def update_merge_request(
    project: Project, merge_request: MergeRequest, target_branch: Head
):
    merge_requests: ProjectMergeRequestManager = project.mergerequests
    editable_merge_request: ProjectMergeRequest = merge_requests.get(
        merge_request.iid, lazy=True
    )  # type: ignore
    editable_merge_request.target_branch = target_branch
    editable_merge_request.save()


def create_merge_request(
    project: Project,
    source_branch: Head,
    target_branch: Head,
):
    commit = get_head_commit(source_branch)
    merge_requests: ProjectMergeRequestManager = project.mergerequests
    merge_requests.create(
        {
            "source_branch": source_branch.name,
            "target_branch": target_branch.name,
            "title": commit.summary,
        }
    )


def get_project(gitlab: Gitlab, remote: Remote) -> Project:
    git_url = parse_git_url(remote.url)
    project_namespace = f"{git_url.owner}/{git_url.repo}"  # type: ignore
    project_manager: ProjectManager = gitlab.projects  # type: ignore
    return project_manager.get(project_namespace, lazy=True)


def update_commit_message(message_file: str):
    with open(message_file, "r+") as file:
        message = file.read()
        change_id = get_change_id(message)

        if not change_id:
            change_id = create_change_id()
            updated_message = f"{message.strip()}\n\nChange-Id: {change_id}\n"
            file.seek(0)
            file.write(updated_message)
            file.truncate()


def create_change_id():
    user = getuser()
    hash = getrandbits(16)
    return f"{user}-{hash:04x}"


def get_change_id(message: str) -> Optional[str]:
    last_paragraph = message.split("\n\n")[-1]
    change_id_line = next(
        (line for line in last_paragraph.splitlines() if line.startswith("Change-Id:")),
        None,
    )
    if not change_id_line:
        return None
    change_id = change_id_line.lstrip("Change-Id:").strip()
    return change_id


def install_commit_message_hook():
    commit_message_script = join("resources", "commit-msg")
    git_dir = find_git_dir()
    commit_message_hook_path = join(git_dir, "hooks", "commit-msg")
    if exists(commit_message_hook_path):
        if not cmp(commit_message_hook_path, commit_message_script):
            raise RuntimeError(
                f"commit-msg script {commit_message_hook_path} must be removed first"
            )
    else:
        copyfile(commit_message_script, commit_message_hook_path)
        chmod(commit_message_hook_path, 0o775)
        print("commit-msg hook installed")


def find_git_dir() -> str:
    repo = Repo(".", search_parent_directories=True)
    if not repo.git_dir:
        raise RuntimeError("Not a Git repository")
    return repo.git_dir


def fail(message: str) -> NoReturn:
    raise SystemExit(f"{program} error:", message)
