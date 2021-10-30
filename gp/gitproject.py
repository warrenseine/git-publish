from abc import ABC, abstractmethod
from os import getenv
from typing import Optional
from git import Head, Remote
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
        self, change_id: str, source_branch: Head, target_branch: Head, title: str
    ):
        ...


def build_git_project(remote: Remote) -> GitProject:
    git_url = parse(remote.url)
    project_namespace = f"{git_url.owner}/{git_url.repo}"  # type: ignore

    if git_url.platform == "gitlab":
        return GitlabProject(project_namespace)

    raise NotImplementedError(f"Unknown Git platform {git_url.platform}.")


class GitlabProject(GitProject):
    def __init__(self, project_namespace: str):
        gitlab_token = getenv("GITLAB_TOKEN")
        if not gitlab_token:
            raise EnvironmentError(f"Empty environment variable GITLAB_TOKEN.")
        self.gitlab = Gitlab("https://gitlab.com", private_token=gitlab_token)
        project_manager: ProjectManager = self.gitlab.projects  # type: ignore
        self.project = project_manager.get(project_namespace, lazy=True)
        self.merge_requests: ProjectMergeRequestManager = self.project.mergerequests

    def create_or_update_change(
        self, change_id: str, source_branch: Head, target_branch: Head, title: str
    ):
        merge_request = self.__find_merge_request(change_id)

        if merge_request:
            self.__update_merge_request(merge_request, target_branch, title)
        else:
            self.__create_merge_request(source_branch, target_branch, title)

    def __list_merge_requests(self) -> list[MergeRequest]:
        return self.merge_requests.list()  # type: ignore

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
        editable_merge_request.target_branch = target_branch
        editable_merge_request.title = title
        editable_merge_request.save()

    def __create_merge_request(
        self, source_branch: Head, target_branch: Head, title: str
    ):
        self.merge_requests.create(
            {
                "source_branch": source_branch.name,
                "target_branch": target_branch.name,
                "title": title,
            }
        )
