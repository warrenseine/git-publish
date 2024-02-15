# git-publish

Push stacked atomic Pull/Merge Requests.

# Get started

Install `git-publish`:

```sh
$ poetry install
$ poetry build
$ pip install dist/*.whl
$ cp git-publish /usr/local/bin
```

Run it in your repository:

```sh
$ git-publish
```

# What is this?

`git-publish` is a Python script that manages your stacked commits into separate PR (GitHub) / MR (GitLab). It assigns a change ID to each commit in the commit message through a commit message hook. When calling `git-publish` directly, each commit will be pushed to a dedicated remote branch and PR / MR will be created targeting the right branch to retain the commit history. If commits are amended, `git-publish` will refer to the change ID to find the associated branch and keep everything in order.

# Next

- Add nested blocking dependencies (available in GitLab 16.6+)
