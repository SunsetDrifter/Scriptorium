# Owner review

Triggered by "owner review for auth". Code-level verification catches signature drift; owner review catches "we deprecated this whole module last sprint and nobody told the wiki". This is how large wikis stay honest.

1. **Open the subsystem README** (`subsystems/<name>/README.md`) and every page listed in its `key_modules`, `key_services`, and `key_adrs`.
2. **Interview the owner.** For each page, ask the human (acting as owner): is this still accurate? Any major recent changes the wiki misses? Anything new that should be documented?
3. **Update pages based on the answers.** Deprecations, ownership changes, and mission drift get edited now; larger gaps become follow-up document tasks the human approves. Status flips on active modules still require explicit confirmation.
4. **Bump `last_owner_review`** on the README (lint warns when it exceeds 90 days).
5. **Run `python3 lint.py check`** and fix any errors.
6. **Append an owner-review entry to `log.md`**, then commit: `owner-review: <subsystem>`.

Log entry format:

```
## [2026-04-10] owner-review | auth
- reviewed with: @jack
- pages confirmed: 6, pages updated: 2
- follow-ups: document libs/auth/webauthn (new, undocumented)
```
