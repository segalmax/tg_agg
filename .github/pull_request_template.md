## What changed

<!-- Brief description of the changes -->

## Why

<!-- Motivation / context. Link relevant issue if any -->

## How to test

<!-- Step-by-step testing instructions -->

## Checklist

- [ ] Tests pass locally (`cd tg_site && python manage.py test videos.tests --noinput`)
- [ ] Lint passes (`ruff check tg_site/`)
- [ ] No unapplied migrations (`python manage.py showmigrations | grep '\[ \]'`)
- [ ] Commit messages follow convention (`feat:` / `fix:` / `chore:` / `docs:`)
