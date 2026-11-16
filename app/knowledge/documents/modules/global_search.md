---
module: Global Search
feature_keys:
- search
- global-search
- ctrl-k
- find-vehicle
- find-driver
routes:
- header search (every screen)
roles:
- all users for page search; record search needs device.read
permissions:
- device.read (record search)
availability: VERIFIED LIVE
technical_reference: api/modules/global_search_api.md
---

# Global Search

## 1. Purpose
One search box for app pages and fleet records (vehicles, drivers, alerts, geofences, users) returned by the server.

## 2. Navigation
Top bar "Search vehicles, drivers, or alerts…" or **Ctrl K**. Dialog "Search SafeFare AI" ("Search pages and the records the server returns. Use arrow keys and Enter.").

## 8. Behaviour
Starts after you type 2 characters and shows up to 8 records. Results grouped by type; linked only when you can open the target screen. Drivers get page results only.

## 18. Common questions
- **How do I quickly find a vehicle?** Press Ctrl K, type the vehicle name or device number, press Enter.

## 19. Limitations
Hit types/group keys undocumented; unknown types are listed but not linked; geofence and user hits are unlinked by design.
