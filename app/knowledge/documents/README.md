# SafeFare Iris AI — application knowledge (user-facing)

Plain-language knowledge about how SafeFare works: screens, menus, buttons, fields, workflows, roles, limitations and FAQs. **This folder contains no API endpoints, payloads or source-code references** — those live in `../api/`. Iris uses this folder to answer *what / how / why* questions (STATIC_KNOWLEDGE, HOW_TO, TROUBLESHOOTING, UNSUPPORTED). Live numbers always come from API tools, never from these documents.

Built 2026-11-05 from the SafeFare frontend ZIP, the provided Swagger and the frontend team's verification notes. Java source, the business database schema and user guides were not supplied.

## Layout
```
documents/
  README.md
  application_overview.md       what SafeFare is, who uses it, modules, key concepts
  modules.md                    index of module documents with availability
  roles_permissions.md          roles, which permission opens which screen/action, data isolation
  workflows.md                  step-by-step tasks with exact menu names
  troubleshooting.md            verified behaviour vs possible causes, error messages
  limitations.md                what the app can't do yet, confusing points
  frequently_asked_questions.md
  terminology.md
  knowledge_test_cases.json     test questions for this folder
  modules/*.md                  one document per module (34)
```

## Module document format
YAML front matter: `module`, `feature_keys`, `routes` (app page links, for "open this page" buttons), `roles`, `permissions`, `availability`, `technical_reference` (path of the matching API file). Body sections: Purpose · Navigation · Screens · Features · Buttons · Form fields · Columns & filters · Search/paging · Workflows · Roles · Permissions · Business rules · Errors · Common questions · Limitations. Chunk on `## ` headings.

## Rules for Iris
1. Never quote numbers from these documents as live data.
2. Never give steps for anything listed in `limitations.md` / `modules/features_not_in_app.md`.
3. Drivers only have My Work; platform screens are only for the Safe-Fare Admin.
4. The Fleet Owner role code is unconfirmed — answer by permission, not role name.
