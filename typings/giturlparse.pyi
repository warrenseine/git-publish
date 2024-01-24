from dataclasses import dataclass

@dataclass
class GitUrl:
    platform: str
    host: str
    resource: str
    port: int
    protocol: str
    protocols: list[str]
    user: str
    owner: str
    repo: str
    name: str
    groups: list[str]
    path: str
    path_raw: str
    branch: str

def parse(url: str) -> GitUrl: ...
