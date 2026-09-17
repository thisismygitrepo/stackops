from typing import Literal, TypedDict


class GitRepoSync(TypedDict):
    mode: Literal["git"]


class GuardRepoSync(TypedDict):
    mode: Literal["guard"]
    cloud: str
    remotePath: str
    ignoreGitignore: bool


type RepoSync = GitRepoSync | GuardRepoSync


class GitVersionInfo(TypedDict):
    branch: str
    commit: str


class RepoRemote(TypedDict):
    name: str
    url: str


class RepoRecordDict(TypedDict):
    name: str
    parentDir: str
    currentBranch: str
    remotes: list[RepoRemote]
    version: GitVersionInfo
    isDirty: bool
    sync: RepoSync


class RepoRecordFile(TypedDict):
    version: str
    repos: list[RepoRecordDict]
