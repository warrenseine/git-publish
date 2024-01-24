from abc import ABC, abstractmethod
from os import getenv
from typing import Optional
from git import Head, Remote
from github import Github
from github.PullRequest import PullRequest
from gitlab.client import Gitlab
from gitlab.v4.objects import ProjectManager
from gitlab.v4.objects.merge_requests import (
    MergeRequest,
    ProjectMergeRequest,
    ProjectMergeRequestManager,
)
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
    ) -> str:
        ...


def build_git_project(remote: Remote) -> GitProject:
    git_url = parse(remote.url)
    project_namespace = git_url.pathname.removesuffix(".git")  # type: ignore

    if git_url.platform == "gitlab":
        return GitlabProject(project_namespace)

    if git_url.platform == "github":
        return GithubProject(project_namespace)

    raise NotImplementedError(f"Unknown Git platform {git_url.platform}.")


class GithubProject(GitProject):
    def __init__(self, project_namespace: str):
        github_token = getenv("GITHUB_TOKEN")
        if not github_token:
            raise EnvironmentError("Empty environment variable GITHUB_TOKEN.")
        self.github = Github(github_token)
        self.project = self.github.get_repo(project_namespace)
        self.pull_requests = self.project.get_pulls()

    def create_or_update_change(
        self,
        change_id: str,
        source_branch: Head,
        target_branch: Head,
        title: str,
        description: str,
    ) -> str:
        pull_request = self.__find_pull_request(change_id)

        if pull_request:
            self.__update_pull_request(pull_request, target_branch, title)
        else:
            pull_request = self.__create_pull_request(
                source_branch, target_branch, title, description
            )

        return pull_request.html_url

    def __find_pull_request(self, source_branch: str) -> Optional[PullRequest]:
        for pull_request in self.pull_requests:
            if pull_request.head.ref == source_branch:
                return pull_request
        return None

    def __update_pull_request(
        self, pull_request: PullRequest, target_branch: Head, title: str
    ):
        pull_request.edit(base=target_branch.name, title=title)

    def __create_pull_request(
        self, source_branch: Head, target_branch: Head, title: str, description: str
    ) -> PullRequest:
        return self.project.create_pull(
            title=title,
            body=description,
            base=target_branch.name,
            head=source_branch.name,
        )


class GitlabProject(GitProject):
    def __init__(self, project_namespace: str):
        gitlab_token = getenv("GITLAB_TOKEN")
        if not gitlab_token:
            raise EnvironmentError("Empty environment variable GITLAB_TOKEN.")
        gitlab_url = getenv("GITLAB_URL", "https://gitlab.com")
        self.gitlab = Gitlab(gitlab_url, private_token=gitlab_token)
        project_manager: ProjectManager = self.gitlab.projects  # type: ignore
        self.project = project_manager.get(project_namespace, lazy=True)
        self.merge_requests: ProjectMergeRequestManager = self.project.mergerequests

    def create_or_update_change(
        self,
        change_id: str,
        source_branch: Head,
        target_branch: Head,
        title: str,
        description: str,
    ) -> str:
        merge_request = self.__find_merge_request(change_id)

        if merge_request:
            self.__update_merge_request(merge_request, target_branch, title)
        else:
            merge_request = self.__create_merge_request(
                source_branch, target_branch, title, description
            )

        return merge_request.web_url

    def __list_merge_requests(self) -> list[MergeRequest]:
        return self.merge_requests.list(get_all=True)  # type: ignore

    def __find_merge_request(self, source_branch: str) -> Optional[MergeRequest]:
        for merge_request in self.__list_merge_requests():
            if merge_request.source_branch == source_branch:
                return merge_request
        return None

    def __update_merge_request(
        self, merge_request: MergeRequest, target_branch: Head, title: str
    ):
        editable_merge_request: ProjectMergeRequest = self.merge_requests.get(
            merge_request.iid, lazy=True
        )  # type: ignore
        editable_merge_request.target_branch = str(target_branch)
        editable_merge_request.title = title
        editable_merge_request.save()

    def __create_merge_request(
        self, source_branch: Head, target_branch: Head, title: str, description: str
    ):
        response = self.merge_requests.create(
            {
                "source_branch": source_branch.name,
                "target_branch": target_branch.name,
                "title": title,
                "description": description,
                "remove_source_branch": True,
            }
        )
        merge_request: MergeRequest = response  # type: ignore
        return merge_request
