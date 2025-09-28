from abc import ABC, abstractmethod
from git import Head, Remote
from giturlparse import parse


class GitProject(ABC):
    @abstractmethod
    def create_or_update_change(
        self,
        change_id: str,
        source_branch: Head,
        target_branch: Head,
        title: str,
        description: str,
    ) -> str: ...


def build_git_project(remote: Remote) -> GitProject:
    git_url = parse(remote.url)
    project_namespace = git_url.pathname.removesuffix(".git").removeprefix("/")  # type: ignore

    if git_url.platform == "gitlab":
        # Imported lazily to avoid mixing provider-specific logic in this module
        from .gitlab_project import GitlabProject

        return GitlabProject(project_namespace)

    if git_url.platform == "github":
        # Imported lazily to avoid mixing provider-specific logic in this module
        from .github_project import GithubProject

        return GithubProject(project_namespace)

    raise NotImplementedError(f"Unknown Git platform {git_url.platform}.")
