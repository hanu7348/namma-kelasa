# Security Policy

Namma Kelasa handles authentication, job applications, uploaded résumés, employer information, and optional payment events. Please report security issues privately.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/hanu7348/namma-kelasa/security/advisories/new). Do not open a public issue containing exploit details, personal data, credentials, or uploaded documents.

Please include:

- affected route or component;
- reproduction steps;
- expected and observed behaviour;
- likely impact;
- a suggested fix, if available.

## Credential safety

- Keep Django, Resend, Razorpay, and database credentials only in environment variables.
- Never commit `.env`, database files, private media, logs, or production exports.
- Rotate any credential that has appeared in chat, logs, screenshots, or source control.
- Use test-mode payment keys and controlled email recipients during development.

Maintainers should acknowledge valid reports promptly and avoid disclosing details until a fix is available.
