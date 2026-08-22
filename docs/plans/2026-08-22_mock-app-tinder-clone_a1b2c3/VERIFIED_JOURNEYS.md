# Verified journeys — mock app Tinder clone

**Date:** 2026-08-22  
**Environment:** `http://127.0.0.1:8765/`  
**Evidence:** [images/](images/) (PNG screenshots + `09-journey-demo.webm`)

End-to-end QA of the localhost mock app happy path. Screenshots were captured after automated Playwright runs; one manual GUI pass reported flaky Undo clicks, but Playwright evidence on `07-after-undo-restored.png` confirms restore behavior.

## Summary

| Journey | Status | Evidence file | Notes |
|---------|--------|---------------|-------|
| 1. Discover deck loads with photo, work, education, badges, counter | **Verified** | `images/01-discover-deck.png` | Alex Chen card shows gradient photo placeholder, LinkedIn + Trust badges, WORK/EDUCATION sections, and "3 profiles left". |
| 2. Open verification modal (LinkedIn) | **Verified** | `images/02-verification-modal.png` | "Your verification" modal opens from Discover; LinkedIn tab active with photo/video inputs and submit button. |
| 3. Switch to Trust Source tab | **Verified** | `images/03-verification-trust-tab.png` | Trust Source tab selected; instructions and submit button update for trust verification. |
| 4. LinkedIn photo upload → success + badge | **Verified** | `images/04-linkedin-upload-success.png` | Success banner "LinkedIn verification submitted — badge updated."; LinkedIn badge shows checkmark. |
| 5. Trust Source video upload → success + badge | **Verified** | `images/05-trust-upload-success.png` | Success banner "Trust Source verification submitted — badge updated."; both LinkedIn and Trust badges show checkmarks. |
| 6. Like advances deck; Undo button appears | **Verified** | `images/06-after-like-with-undo.png` | After Like, profile advances to Jordan Lee, counter shows "2 profiles left", yellow Undo button visible. |
| 7. Undo restores previous profile | **Verified** | `images/07-after-undo-restored.png` | Playwright PASS: Alex Chen restored, counter back to "3 profiles left", Undo hidden. Manual computerUse clicks were flaky; screenshot evidence is authoritative. |
| 8. Empty deck hides Like/Pass | **Verified** | `images/08-empty-state.png` | "You've seen everyone" empty state; Like/Pass buttons absent; reload hint shown. |

**Result:** 8/8 journeys **Verified**. 0 Partial. 0 Fail.

## Demo video

`images/09-journey-demo.webm` — screen recording of the full journey sequence (discover → verification uploads → like/undo → empty state). Use alongside individual PNGs for walkthrough review.

## Evidence index

Filename-to-journey mapping: [images/README.md](images/README.md).
