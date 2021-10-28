import argparse
import filecmp
import getpass
import git
import os
import random
import shutil
import sys

version = "0.0.1"
program = "git-publish"


def main(argv: list[str]):
    parser = argparse.ArgumentParser(
        prog=program, description="Publish atomic Git commits."
    )
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
    if not ensure_clean_working_directory():
        return fail(
            f"Working directory is not clean. Clean it first before calling {program}."
        )
    pass


def ensure_clean_working_directory():
    repo = git.Repo(".", search_parent_directories=True)
    return not repo.is_dirty() and not repo.untracked_files


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
    user = getpass.getuser()
    hash = random.getrandbits(16)
    return f"{user}-{hash:04x}"


def get_change_id(message: str) -> str or None:
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
        os.chmod(commit_message_hook_path, 0o775)
        print("commit-msg hook installed")


def find_git_dir():
    repo = git.Repo(".", search_parent_directories=True)
    if not repo.git_dir:
        raise RuntimeError("not a git repository")
    return repo.git_dir


def fail(message: str) -> int:
    print(f"{program} error:", message, file=sys.stderr)
    exit(1)
