# Scanner Code Review Rules

Use local CLI scanners first. Use external review only when available and useful.

## Automatic verification

- After file creation or modification, run the cheapest relevant local checks for the changed file type.
- Prefer read-only tools and project-native commands.
- Do not treat a scanner timeout as success.
- Report issues found before applying follow-up fixes.

## Recommended tools

- `semgrep` for multi-language static analysis.
- `coderabbit review --agent` for external review when authenticated.
- `snyk test` for dependency and supply-chain risk when configured.
- `gitleaks detect` or `detect-secrets scan` for secret detection.
- Project-native lint, test, build, or type-check commands remain mandatory when relevant.

## Dependency validation

Before adding packages or changing dependency manifests:

1. Inspect the manifest and lockfile.
2. Run the project-native dependency audit when available.
3. Run `snyk test`, `pip-audit`, `npm audit`, or equivalent for the ecosystem.
4. Do not install or update packages only to satisfy a scanner suggestion without user approval.

## End of turn report

If scanners or review tools were used, summarize:

- Tool names and scopes.
- Issues by severity.
- Fixes applied.
- Remaining risks, skipped tools, and any timeout.
