---
applyTo: "**"
description: >
  Secrets handling and git-safety rules for the Finance Tracking App. Single source of
  truth — both the Finance App Dev agent and the GitHub Agent reference this instead of
  keeping their own copies, so a rule change only has to happen in one place.
---

# Security Rules

## Secrets
- API keys (Gemini, etc.) live only in `config.json`, loaded at runtime via `AppConfig`.
  Never hardcoded in any `.py` file, never committed with real values.
- `.gitignore` must include `config.json`, `database/finance.db`, `__pycache__/`, `*.pyc`,
  `/build`, `*.apk`. If you're about to stage any of these, stop and check `.gitignore` first.

## Before any DB write or file operation
- [ ] User-supplied input? → validate type, range, and max length at the service layer.
- [ ] File path? → confirm it resolves within the app data directory, not an arbitrary path.
- [ ] SQL query? → ORM or `?` bound placeholders, never string interpolation.
- [ ] Secret/key in this code path? → confirm it's read from `config.json`, not hardcoded.

## Before any git commit (applies to GitHub Agent and anyone committing manually)
- [ ] Does any staged file contain a hardcoded API key, token, or password?
- [ ] Is `config.json` (with real keys, not a template) being staged?
- [ ] Are build artifacts (`/build`, `*.apk`, `__pycache__`) being staged?
- [ ] Is `database/finance.db` (real seed/user data) being staged?

If any checkbox fails, unstage the offending file and fix `.gitignore` rather than
committing and trying to remove it in a follow-up commit — history still has it.
