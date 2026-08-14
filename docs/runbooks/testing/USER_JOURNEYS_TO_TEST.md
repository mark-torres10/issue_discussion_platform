# User journeys to test

Draft list of participant journeys for the current Next.js prototype. Backend checks are placeholders until Railway routes exist. Start the app with [How to run the app](../HOW_TO_RUN_APP.md).

## 1. Open the sample session from home

From `/`, open **Open sample session** and land on the introduction for `demo-campus-speech-001`.

### Journey 1: UI verification

### Journey 1: Backend verification

## 2. Read the introduction and continue

Confirm issue, AI persona (Jordan), duration, and continue to audio check.

### Journey 2: UI verification

### Journey 2: Backend verification

## 3. Pass the audio check and start in voice

Grant the microphone, complete the speaker check, and start the conversation in voice mode.

### Journey 3: UI verification

### Journey 3: Backend verification

## 4. Continue in text without a microphone

Choose text (or **Continue with text instead**) and start the conversation with a message box.

### Journey 4: UI verification

### Journey 4: Backend verification

## 5. Hold a text disagreement

Send several participant turns and confirm scripted AI replies appear in order.

### Journey 5: UI verification

### Journey 5: Backend verification

## 6. Hold a mocked voice conversation

In voice mode, check listening / speaking state, captions, mute, and interrupt if shown.

### Journey 6: UI verification

### Journey 6: Backend verification

## 7. Switch mode during the conversation

Move from text to voice or voice to text without losing visible turns.

### Journey 7: UI verification

### Journey 7: Backend verification

## 8. End the conversation and see completion

End the session (participant action or time limit) and land on `/complete` with next-step copy.

### Journey 8: UI verification

### Journey 8: Backend verification

## 9. Retry a failed save on completion

Trigger or simulate a retrying save status and confirm the retry control reaches a saved state.

### Journey 9: UI verification

### Journey 9: Backend verification

## 10. Open an expired session

Open `expired-demo` (home shortcut or `/session/expired-demo`) and see the expired unavailable screen.

### Journey 10: UI verification

### Journey 10: Backend verification

## 11. Open a completed session

Open `completed-demo` and see the already-complete unavailable screen.

### Journey 11: UI verification

### Journey 11: Backend verification

## 12. Open a paused session

Open `paused-demo` and see the paused unavailable screen.

### Journey 12: UI verification

### Journey 12: Backend verification

## 13. Open an unknown session id

Visit `/session/not-a-real-session` and see **Session not found**.

### Journey 13: UI verification

### Journey 13: Backend verification

## 14. Hit a live route on a non-active session

Open `/session/expired-demo/audio-check` or `/conversation` and confirm redirect to `/unavailable`.

### Journey 14: UI verification

### Journey 14: Backend verification
