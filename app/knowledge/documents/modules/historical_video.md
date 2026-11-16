---
module: Historical Video
feature_keys:
- historical-video
- recordings
- recording-calendar
- clip-export
- playback
- cameras
- channels
routes:
- /drive-vision/video
roles:
- users with video.playback
permissions:
- video.playback (screen and export request)
- video.live (live/embed — unused)
availability: PARTIALLY IMPLEMENTED (no playback)
technical_reference: api/modules/historical_video_api.md
---

# Historical Video

## 1. Purpose
Find recorded camera footage for a device by day and channel, and request clip exports (downloadable files) from the vendor.

## 2. Navigation
Sidebar **Monitor → Historical Video**.

## 3. Screen
- **Device** picker ("Choose a device"; shows camera count) and **Channel** (All channels or 1..n from the device's camera lines/count).
- **Recording calendar** (Previous month / Next month) — days that have recordings.
- **Recordings** list for the selected day (IST).
- **Playback not available yet** panel.
- **Clip exports** ("Jobs requested for this device") with Prev/Next paging, **Download** links, "Link not usable", "No file yet".

## 5. Buttons
| Button | Action |
|---|---|
| Export clip (on a recording) → **Request export** | Asks the server to prepare a downloadable clip of that recording, after confirmation "Request a clip export?". |
| Download | Opens the export file URL (only real http(s) links). |
| Try again | Reload devices. |

## 9. Workflows
**How do I view historical video?**
1. Monitor → **Historical Video**.
2. Choose a **Device**, optionally a **Channel**.
3. In the **Recording calendar** pick a highlighted day (use Previous/Next month).
4. The **Recordings** list shows that day's recordings.
5. In-browser playback is **not available yet**; to get the footage, use **Export clip → Request export**, then wait for the job in **Clip exports** and use **Download** when a file link appears.

## 10–11. Roles / permissions
`video.playback`. In the reference permission sets, tenant ADMIN and Safe-Fare Admin have it; a Fleet Owner only if the role includes it.

## 16. Business rules
- Exports may consume vendor credit or device data — NOT VERIFIED.
- Placeholder hosts (e.g. `example.invalid`) are shown as "Link not usable".

## 17. Errors
"The server didn't accept the export" toast; "Couldn't load devices"; empty states "No recordings", "No exports".

## 18. Common questions
- **Why is historical video unavailable / won't play?** In-app playback needs the vendor's video SDK/player, which hasn't been provided; recordings can be listed and exported only. Also check the device is video-capable and has recordings on that day (calendar).
- **Why does my export have no download link?** The job may still be processing; the list refreshes only when you reload it (no auto-refresh).

## 19. Limitations
PLAYBACK NOT AVAILABLE. Export status values and cost are undocumented. The export list doesn't refresh automatically.
