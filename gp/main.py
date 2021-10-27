import argparse
import filecmp
import git
import os
import shutil

version = "0.0.1"


def main(argv: list[str]):
    parser = argparse.ArgumentParser(
        prog="git-publish", description="Publish atomic Git commits."
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {version}"
    )

    args = parser.parse_args(argv)

    install_commit_message_hook()


def install_commit_message_hook():
    commit_message_script = os.path.join("resources", "commit-msg")
    git_dir = find_git_dir()
    commit_message_hook_path = os.path.join(git_dir, "hooks", "commit-msg")
    if os.path.exists(commit_message_hook_path):
        if not filecmp.cmp(commit_message_hook_path, commit_message_script):
            raise RuntimeError(
                f"commit-msg script {commit_message_hook_path} must be removed first"
            )
    else:
        shutil.copyfile(commit_message_script, commit_message_hook_path)
        print("commit-msg hook installed")


def find_git_dir():
    repo = git.Repo(".", search_parent_directories=True)
    if not repo.git_dir:
        raise RuntimeError("not a git repository")
    return repo.git_dir
