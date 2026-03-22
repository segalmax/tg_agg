# Claude Instructions

## Behavior
- **Always run commands yourself** — never give me commands to run unless I explicitly ask.
- **Diagnose without modifying** — if asked to diagnose/investigate, run only read/non-modifying commands.
- **Investigate proactively** — if asked to investigate, do it thoroughly yourself; don't hand me a list of steps.
- **When modifying the environment** (only if explicitly asked): be defensive and back up what you change.
- **DB queries**: check table indexes before running heavy queries. Watch for special character escaping issues in queries (e.g. `LIKE '%xx%'`).

## Code Style
- **Fail-fast, loud** — no defensive fallbacks. If expected data/columns are missing, fail ungracefully. Keeps code concise.
- **Always use a `main()` function** — minimize global variable scope.
- **argparse style**: use `snake_case` argument names (e.g. `--site_id` not `--site-id`), minimalistic setup.
- **Long, self-explanatory names** — variable and function names should make comments redundant.

## Big Task Flow
When asked to work on a big multi-file/multi-step task:
1. Investigate code and DB thoroughly first.
2. Ask all clarifying questions upfront.
3. Object if you disagree with my design ideas — prioritize simplicity, readability, conciseness.
4. Maintain two docs: **code documentation** (concise, updated as you learn) + **execution plan** (sequential sub-tasks).
6. Tests: short, simple, clear — don't reimplement what the tested code does.

## Diagrams (Mermaid)
- Use components inside components for different systems/VMs/DBs/UIs/configs
- Add sequential numbers showing operation order (forked: 6a, 6b, etc.)
- Use colors, shapes, and best conventions for readable, professional diagrams

## Doc-it
When asked to document learnings from a chat:
- Find or create a relevant `.md` doc in the codebase
- Reread the whole doc before updating — add/update only, don't drop existing info
- Focus on reusable "tribal knowledge": env insights, DB schema, general stats, codebase patterns
- Keep it general, not tailored to the specific task
