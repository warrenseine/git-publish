# git-publish

Push stacked atomic Pull/Merge Requests.

# What is this?

`git-publish` is a Python script that manages your stacked commits into separate PR (GitHub) / MR (GitLab). It assigns a change ID to each commit in the commit message through a commit message hook. When calling `git-publish` directly, each commit will be pushed to a dedicated remote branch and PR / MR will be created targeting the right branch to retain the commit history. If commits are amended, `git-publish` will refer to the change ID to find the associated branch and keep everything in order.

# Get started

Install `git-publish` for everyday use:

```sh
$ uv tool install git-publish
```

For local development of this repo:

```sh
$ uv build
$ uv tool install . -e
```

Set the required environment variables (add to your shell profile):

- `GITHUB_TOKEN` — required for GitHub projects (repo scope sufficient for PRs)
- `GITLAB_TOKEN` — required for GitLab projects (api scope)
- `GITLAB_URL` — optional GitLab instance URL; default: `https://gitlab.com`
- `GITPUBLISH_BRANCH_PREFIX` — optional branch/id prefix; defaults to your OS username
- `GITPUBLISH_CHANGE_ID_PREFIX` — prefix used in commit messages for change ids; defaults to `Change-Id:`

You can also drop these in a local `.env` file at the repo root; it will be auto‑loaded when you run the tool:

```env
# .env
GITHUB_TOKEN=ghp_...
GITLAB_TOKEN=glpat-...
GITLAB_URL=https://gitlab.example.com
GITPUBLISH_BRANCH_PREFIX=alice
GITPUBLISH_CHANGE_ID_PREFIX=Change-Id:
```

Run it in your repository:

```sh
$ git-publish
```

Tips:

- You can also run it as a Git subcommand: `git publish` (Git will invoke `git-publish` on PATH).
- Make sure you are on one of the main branches (`main`, `master`, `development`, `develop`) and that it is up-to-date with its tracking branch.
- After commit, check the commit message contains a line like `Change-Id: user/1a2b` (or your chosen prefix).

# Hooks

When you run the tool, it installs a `commit-msg` hook at `.git/hooks/commit-msg` that ensures a Change‑Id is present in every commit.

- Update: re-run `git-publish` to validate the existing hook content.
- Remove: `rm .git/hooks/commit-msg`.

# Safety

This tool will:

- Stash and later unstash your working tree when dirty
- Force‑push ephemeral branches (one per commit)
- Delete temporary local branches after publishing

Make sure your main branch is clean and tracking the correct remote.

# Development tasks

Using the task runner:

```sh
$ uv run task lint    # ruff (check) + pyright
$ uv run task format  # ruff --fix
$ uv run task test    # pytest
```

# Troubleshooting

- "Branch is not up‑to‑date with its tracking branch" → `git fetch` then `git pull --ff-only`.
- "Must be on a main branch" → switch to `main`, `master`, `development`, or `develop`.
- "Empty GITHUB_TOKEN/GITLAB_TOKEN" → export in your shell or add to `.env`.

# Example output

```
git-publish info: My feature commit
  🔗 https://github.com/owner/repo/pull/123
```

# Next

- Add nested blocking dependencies (available in GitLab 16.6+)
