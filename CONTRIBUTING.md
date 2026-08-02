# Contributing to Namma Kelasa

Thank you for helping make local employment opportunities more accessible across Karnataka.

## Before you begin

- Search existing issues before opening a new one.
- Use an issue for significant features or schema changes before implementation.
- Never include real API keys, user résumés, email addresses, payment data, or production database exports.
- Keep candidate safety, accessibility, Kannada support, and mobile usability in scope.

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm install
npm run build
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Use `OTP_BACKEND=console` for local development. Do not use production credentials in a development checkout.

## Branches and commits

1. Create a focused branch such as `feature/kannada-search` or `fix/otp-rate-limit`.
2. Keep commits small and describe the outcome in the imperative mood.
3. Avoid unrelated formatting or generated-file changes.
4. Add or update tests for behaviour changes.

## Required checks

Run these commands before opening a pull request:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
python manage.py test
```

For UI changes, verify both desktop and a 390 px mobile viewport. Respect reduced-motion preferences and test light and dark themes.

## Pull requests

A good pull request explains:

- what changed and why;
- candidate or employer impact;
- screenshots for visible UI changes;
- migrations or environment-variable changes;
- validation performed;
- security, privacy, accessibility, and localisation considerations.

By contributing, you agree that maintainers may review, revise, or decline changes to protect users and the project direction.
