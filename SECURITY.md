# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.3.x   | ✅ Supported        |
| 0.2.x   | Security fixes only |
| 0.1.x   | ❌ No longer supported |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

**Email:** ace@scoutli.ai

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Do NOT** open a public GitHub issue for security vulnerabilities.

We will acknowledge receipt within 48 hours and aim to provide a fix within 7 days for critical issues.

## Security Considerations

Naturo is a desktop automation tool that intentionally provides:

- **Input simulation** (click, type, press) — by design, not a vulnerability
- **UI tree inspection** — reads accessibility information exposed by the OS
- **Process management** — launches and controls applications as the current user
- **Registry / Service access** — operates with the permissions of the running user

These capabilities are core features. Security concerns should focus on:

- Privilege escalation beyond the current user's permissions
- Remote code execution through crafted inputs
- Information disclosure of data not accessible to the current user
- Denial of service affecting the host system
