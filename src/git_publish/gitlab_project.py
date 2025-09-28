from os import getenv
from typing import Generator, Optional, cast

from git import Head
from gitlab.client import Gitlab
from gitlab.v4.objects import ProjectManager
from gitlab.v4.objects.merge_requests import (
    MergeRequest,
    ProjectMergeRequest,
    ProjectMergeRequestManager,
)

from .git_project import GitProject


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

    def __list_merge_requests(self) -> Generator[MergeRequest, None, None]:
        mrs = self.merge_requests.list(iterator=True, state="opened")
        return cast(Generator[MergeRequest, None, None], mrs)

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
        editable_merge_request.target_branch = target_branch.name
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
