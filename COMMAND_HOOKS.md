# Command Hooks — Hard Rules

These hooks are mandatory for every assistant/tool/agent operating in this repo.
They override generic helpfulness instincts. When in doubt, follow the more restrictive rule.

## 1. Package manager operations

- `brew install`, `brew upgrade`, `brew remove`, `brew uninstall`:
  Forbidden without explicit user authorization in the same turn.
  List/search commands (`brew list`, `brew search`, `brew info`) are allowed.

- `uv tool install`, `uv tool uninstall`, `pip install`, `pip uninstall`, `pipx install`, `pipx uninstall`:
  Forbidden without explicit user authorization in the same turn.
  Listing commands (`uv tool list`, `pip list`, `pipx list`) are allowed.

- `apt`, `yum`, `dnf`, `pacman`, `npm i`, `npm uninstall`, `pnpm i`, `cargo install`, `go install`, etc:
  Same as above. No install/remove without explicit user authorization.

## 2. System mutation outside package managers

- Any command that removes, moves, renames or overwrites files/directories outside the repo
  without explicit user authorization in the same turn is forbidden.
  Blacklisted examples: `rm -rf`, `mv`, `trash`, `shred`, `dd`, `mkfs`, `> redirect` to sensitive paths.
  Read-only commands (`ls`, `cat`, `find`, `rg`, `grep`, `stat`, `du`, `df`) are allowed.

## 3. Git mutation

- Do not create branches, tags, stashes, commits, or PRs without explicit user authorization.
- Read-only git commands (`git status`, `git log`, `git diff`, `git branch --list`, `git tag --list`) are allowed.

## 4. Network and secrets

- Do not send secrets, tokens, or credentials to external endpoints without explicit user authorization.
- Do not create or modify files that commonly contain secrets (`.env`, `.env.*`, `*secret*`, `*credential*`) without explicit user authorization.

## 5. Overrides and privilege escalation

- No `sudo`, `doas`, `su`, or equivalent escalation without explicit user authorization in the same turn.
- No modification of shell profile/dotfiles (`~/.zshrc`, `~/.zprofile`, `~/.bashrc`, `~/.zshenv`, `~/.bash_profile`, `/etc/profile`, `/etc/environment`) without explicit user authorization.

## 6. Repo-local installation exceptions

- Repo-local project installs (`uv sync`, `pip install -e .`, `npm install`, `pnpm install`) are only allowed
  when the user explicitly requests dependency setup in that same turn.
- Do not run these automatically during bug fixes, reviews, or refactors.

## 7. Review and analysis tools

- Static analysis, linters, type checkers, secret scanners, and coverage tools may be installed
  only via the project’s existing dependency mechanism (e.g. `uv sync`, `requirements*.txt`, `pyproject.toml`)
  after explicit authorization.
- Do not install review tools globally with `pip install --user`, `brew install`, `npm i -g`, etc without authorization.

## 8. Command form contract

All commands in this workspace MUST be invoked via the project’s RTK prefix:

- `rtk <command>`
- Exception: tool invocations issued programmatically by the assistant framework.

Reason: token economy. Non-RTK raw commands are allowed only when RTK is unavailable for the specific command.

## 9. Enforcement contract

- If a rule blocks an action, the assistant must:
  1. State the blocked action.
  2. State the rule violated.
  3. Offer the minimal, least-invasive alternative that remains within policy.
- Do not silently skip, route around, or weaken a rule.
