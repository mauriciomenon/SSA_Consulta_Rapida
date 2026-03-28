# Code Quality & Security Automation

This repository uses automated tools for code quality and security:

## Code Quality
- **SonarCloud**: Static analysis, code smells, coverage
- **CodeFactor**: Automated code review
- **Codacy**: Quality metrics, duplication
- **CodeQL**: GitHub security analysis

## Security
- **Snyk**: Vulnerability scanning (dependencies + code)
- **Dependabot**: Automated dependency updates

## Required Secrets

Configure in repository Settings → Secrets and variables → Actions:

| Secret | Description | How to get |
|--------|-------------|------------|
| `SONAR_TOKEN` | SonarCloud authentication | sonarcloud.io → Account → Security → Generate Token |
| `SNYK_TOKEN` | Snyk API token | snyk.io → Account Settings → API Token |

## Quality Gates

- **SonarCloud**: Fails on MAJOR+ issues
- **Snyk**: Alerts on HIGH/CRITICAL vulnerabilities
- **CodeQL**: Weekly security scans

## Quick Setup

1. Fork/clone repository
2. Add SONAR_TOKEN and SNYK_TOKEN secrets
3. Push to trigger workflows
4. Check Actions tab for results

## VSCode Extensions

```
sonarsource.sonarlint-vscode
snyk-security.snyk-vulnerability-scanner
```
