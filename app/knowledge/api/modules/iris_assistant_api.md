---
module: Iris AI / Assistant
user_document: documents/modules/iris_assistant.md
roles:
- users with device.read (not drivers)
permissions:
- device.read
apis:
- GET /api/v1/assistant/prompts
- POST /api/v1/assistant/ask
sources:
- src/components/drive-vision/assistant/ai-assistant.tsx
- src/features/drive-vision/api/assistant-service.ts
status: Prompts VERIFIED LIVE 2026-10-29 (8 prompts); POST /assistant/ask IMPLEMENTED, never sent during verification. Separate Python Iris AI service (iris-ai FastAPI) is NOT connected to this UI.
---

# Iris AI / Assistant — API and implementation reference

Technical companion of `documents/modules/iris_assistant.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. API
`GET /assistant/prompts` → `[Prompt {text, intent}]`. `POST /assistant/ask` body `{question}` → `AnswerDto {question, intent, answer, data, suggestions[], simulated}`.

## Technical details referenced by the user document

- Suggested prompts (from `GET /assistant/prompts`), message box "Ask about vehicles, alerts, trips…" (≤ 500 characters), **Send**, **Clear conversation**, **Close assistant**; answers show a link to the related screen when the user may open it (Open licence expiries, Open Safety Analytics, Open availability, Open Trips, Open incidents, Open Vehicles, Open Live Monitoring, Open Fleet Overview) and clickable suggestions.
- The new FastAPI Iris service must replace or sit beside `POST /assistant/ask`; the UI currently has no conversation history, no conversation id and no markdown tables.
- Drivers need a separate path (their tools are `/driver/**` with `own.data.read`).
