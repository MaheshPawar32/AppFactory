# Change Impact and Rollback Safety

## Before editing
1. Inspect `git status --short`, current branch and recent commits.
2. Identify the requested behavior, likely affected files, dependencies, routes, data models, platform configuration and tests.
3. Summarize user changes already present. Never reset, clean, checkout over, or discard unrelated work.
4. If the tree is dirty or the change is risky, request/ensure a backup or commit before proceeding.
5. Prefer small, reversible batches. Do not modify signing, package IDs, lockfiles, Firebase/AdMob config or permissions without explaining the impact.

## During and after editing
- Review `git diff --check` and `git diff --stat`, then inspect the actual diff.
- Run focused checks first, followed by applicable broader checks.
- Report changed files, dependencies, migrations, known risks and tests with observed outcomes.
- If something fails, preserve logs and diagnose; do not hide failures or automatically revert unrelated files.

## Rollback
- Prefer a revert commit for committed changes.
- For uncommitted work, restore only files that this task changed and only after verifying the diff and user intent.
- Never use broad destructive commands such as `git reset --hard`, `git clean -fd`, or overwriting the whole project as a routine recovery step.
- Database/data migrations require a separate backup and rollback plan.
