---
module: Iris AI / Assistant
feature_keys:
- iris
- assistant
- ai-assistant
- ask-iris
- prompts
- chatbot
routes:
- header launcher 'Ask Iris' (every fleet screen)
roles:
- users with device.read (not drivers)
permissions:
- device.read
availability: Prompts VERIFIED; ask NOT VERIFIED
technical_reference: api/modules/iris_assistant_api.md
---

# Iris AI / Assistant

## 1. What exists today
The frontend has a chat panel **Iris AI** ("Answers from the SafeFare server"). It calls the **Java** assistant (`assistant-controller`), which is rule-based with fixed intents: LICENCE_EXPIRY, RISKY_DRIVERS, DRIVER_AVAILABILITY, ACTIVE_TRIPS, OPEN_ALERTS, DEVICE_HEALTH, FLEET_STATUS, OVERVIEW, HELP. Answers may be flagged `simulated` ("The server marked this answer as simulated").

## 2. Navigation
Top bar launcher "Open Iris, the SafeFare AI assistant" / **Ask Iris**. Can be hidden per browser in Settings → This browser → Show AI assistant.

## 3. Panel
Suggested prompts (from the server), message box "Ask about vehicles, alerts, trips…" (≤ 500 characters), **Send**, **Clear conversation**, **Close assistant**; answers show a link to the related screen when the user may open it (Open licence expiries, Open Safety Analytics, Open availability, Open Trips, Open incidents, Open Vehicles, Open Live Monitoring, Open Fleet Overview) and clickable suggestions.

## 16. Rules
Failures are shown as errors, never replaced by a local answer. The old in-browser rule engine was deleted.

## 18. Common questions
- **What can Iris do?** Answer fleet questions using SafeFare data you're allowed to see, explain how to use SafeFare screens, and link to the right page.
- **Why can't drivers use Iris?** The current Java assistant requires `device.read`.

## 19. Limitations / integration notes for the new Iris AI
- The current panel has no conversation history and no tables.
- Drivers can't use it yet.
