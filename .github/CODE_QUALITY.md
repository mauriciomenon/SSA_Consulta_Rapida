# Code Quality And Security Automation

This repository separates blocking local/CI checks from external advisory services.

## Current Contract

- GitHub branch protection is not configured to require Snyk or DeepSource checks on `dev` or `main`.
- Repository rulesets currently do not make Snyk or DeepSource required merge gates.
- Snyk and DeepSource are treated as advisory PR signals unless their dashboards or GitHub rulesets are changed outside this repository.
- Local release validation remains `py_compile`, `ruff`, `ty`, focused `pytest`, plus the security scans selected for the slice.

## Repository Change Applied

- The repository policy now states that Snyk and DeepSource are advisory unless explicitly required by branch protection, rulesets, or their external dashboards.
- No required Snyk/DeepSource status check existed in GitHub branch protection or rulesets during the 2026-04-25 check, so there was no repository-side required check to remove.
- Any remaining Snyk/DeepSource failure mode is controlled outside this repo by the Snyk or DeepSource GitHub App/dashboard.

## Blocking Checks Owned By This Repository

- `.github/workflows/minimal-ci.yml`: Python import/lint/test gate for the supported project scope.
- `.github/workflows/codeql.yml`: GitHub CodeQL security scan.
- `.github/workflows/secret_scan.yml`: blocking workspace and PR diff secret scans; history scan is advisory and only runs on schedule/manual dispatch.
- `.deepsource.toml`: local analyzer configuration only; it does not decide whether the GitHub App blocks a PR.

## Supply Chain Download Policy

- PR and release gates must not install Python or npm packages from public registries only to produce advisory metadata.
- `.github/actions/opencode-github/action.yml` does not run `npm install`; if its cache is missing, the review job fails with an explicit error instead of downloading from npm.
- GitHub Automatic Dependency Submission is a dynamic GitHub-managed workflow (`dynamic/dependency-graph/auto-submission`), not a versioned YAML file in this repo.
- The repository variable `GH_DEPENDENCY_SUBMISSION_SKIP_CACHE=true` is set to avoid cache persistence while Automatic Dependency Submission remains enabled.
- To fully stop Automatic Dependency Submission, disable it in GitHub Settings > Advanced Security > Dependency graph > Automatic dependency submission. The direct workflow disable API returned HTTP 422 on 2026-05-13.
- `minimal-ci` still installs the OS package `libegl1` from the runner package manager because PyQt smoke coverage depends on it.
- `release-windows` still installs Inno Setup with Chocolatey only in the manual Windows release flow when installers are requested.

## External Advisory Services

### Snyk

- Snyk currently runs as an external service/App, not as a repository workflow in this repo.
- If Snyk reports `Code test limit reached` or private-test quota errors, that is an account/quota condition, not a code vulnerability by itself.
- To keep Snyk warning-only, configure this in the Snyk dashboard or GitHub App settings: do not fail PR checks on quota/advisory findings, or remove Snyk checks from required status checks.
- Do not add `code/snyk` or `security/snyk` to GitHub required checks unless the release policy changes explicitly.

### DeepSource

- DeepSource currently runs as a GitHub App using `.deepsource.toml` for analyzer selection.
- Local validation with `deepsource config validate` requires an authenticated DeepSource CLI session.
- To keep DeepSource warning-only, configure this in the DeepSource dashboard/GitHub App settings: advisory/report-only status, or do not mark DeepSource checks as required in branch protection/rulesets.
- Do not add `DeepSource:*` checks to required status checks unless the release policy changes explicitly.

## Local Verification Notes

- On 2026-04-25, branch protection for `main` and `dev` was checked and neither branch had required status checks configured.
- On 2026-04-25, GitHub rulesets were checked and only `Copilot_review` was active.
- On 2026-04-25, local Snyk CLI execution was blocked by the local Node install missing `libsimdutf.33.dylib`; this is a local toolchain issue.
- On 2026-04-25, local DeepSource config validation was blocked by missing CLI authentication.

## Required Secrets

Only configure these if the corresponding workflow or external dashboard actually needs them:

| Secret | Description | Owner |
|--------|-------------|-------|
| `SONAR_TOKEN` | SonarCloud authentication if Sonar is re-enabled | SonarCloud dashboard |
| `SNYK_TOKEN` | Snyk API token if a Snyk workflow is added later | Snyk dashboard |

## Policy

- External advisory tools may create PR comments and status signals, but they are not release blockers unless explicitly added to required checks.
- If a future branch protection/ruleset starts requiring Snyk or DeepSource, update this document in the same config slice.
- Do not treat quota/auth/toolchain errors from external tools as code failures without a confirmed vulnerability or reproducible repository issue.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
