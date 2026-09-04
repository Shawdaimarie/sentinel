# Security Policy

Sentinel is a reference implementation for governed AI-agent execution,
deterministic evaluation, and independently verifiable audit evidence. Security
reports are welcome when they concern the implementation, its documented trust
boundaries, or a deployment pattern that would materially affect users of the
project.

## Supported versions

| Version | Supported |
|---|---|
| `main` | Yes |
| `0.2.x` | Latest patch release |
| Earlier than `0.2` | No |

## Reporting a vulnerability

Please use GitHub's private vulnerability-reporting workflow:

https://github.com/Shawdaimarie/sentinel/security/advisories/new

Do not open a public issue for a suspected vulnerability. Include:

- affected commit or version;
- threat scenario and required attacker capability;
- minimal reproduction or proof of concept;
- expected versus observed control behavior;
- likely impact;
- suggested mitigation, when known; and
- whether coordinated disclosure timing is important.

Remove live credentials, personal information, client data, and proprietary
artifacts from every report.

## Response targets

- Acknowledgment within **3 business days**.
- Initial severity assessment within **10 business days**.
- Fix or documented mitigation target for High or Critical findings within
  **30 days** of assessment, followed by coordinated disclosure.

These are response targets, not a service-level agreement.

## Scope

In scope:

- policy bypass or an execution path outside `Agent.act`;
- audit-chain tampering accepted as valid;
- keyed-to-unkeyed downgrade acceptance;
- redirect, DNS, path, or URL-boundary bypass;
- prompt-injection behavior that escapes documented controls;
- unsafe canonicalization or disagreement among portable verifiers;
- leakage of secrets through logs, reports, URLs, or fixtures;
- evaluation-gate behavior that silently hides a safety regression; and
- vulnerable dependency or build-pipeline behavior with a credible exploit
  path.

Usually outside scope unless the report demonstrates a project defect:

- risks already identified as residual in `Sentinel/SECURITY.md`;
- social engineering;
- denial of service against third-party providers;
- findings that require arbitrary code execution on the host before Sentinel
  starts; and
- claims that the example benchmark proves or fails to prove general model
  safety.

The detailed adversary model, control matrix, and production-hardening
requirements are maintained in [`Sentinel/SECURITY.md`](Sentinel/SECURITY.md).
