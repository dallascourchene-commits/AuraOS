# Aura Arena Gemini Bridge — T1 Assisted Extension

This is the first browser-facing transport for AWJ-034. It connects a **normal, user-authenticated Gemini web chat** to the local AuraOS relay without using the Gemini API.

## Claim ceiling

This folder is an **ASSISTED reference adapter**. It does not prove live Gemini compatibility until an owner-host browser run produces a turn/result receipt. Version 0.1 never presses Gemini Send.

## Security / authority boundaries

- The extension never requests Chrome cookie permissions.
- It never reads Google passwords, cookies, session tokens, CAPTCHA state, hidden model state, or provider credentials.
- The only stored secret is the local Aura bridge bearer token created by `gemini_webchat_loopback.py`; this is not a Google credential.
- The content script runs only on `https://gemini.google.com/*`.
- The local relay binds only to loopback.
- AuraOS revalidates Arena head/currentness before a turn is exposed and again before accepting the visible result.
- Tool execution is not implemented in the browser adapter yet. Gemini tool intent must become `AuraToolRequestV1`; AuraOS remains the executor/authority.
- If the Gemini UI is ambiguous, capture fails closed. The owner may select the visible response text and retry capture.

## T1 assisted flow

1. Start the local relay on the owner host:

   ```bash
   python tools/project034/gemini_webchat_loopback.py --root ~/.aura/gemini_webchat_bridge
   ```

2. AuraOS (or a bounded setup utility) must create:
   - `state/endpoint_binding_v1.json` through `RelayStoreV1.bind_endpoint(...)`;
   - `state/arena_currentness_v1.json` with `arena_sid`, `arena_head`, `currentness_hash`;
   - one admitted `ArenaTurnEnvelopeV1` in `turn_outbox` through `publish_turn(...)`.

3. In Chromium/Chrome/Edge, open Extensions -> Developer mode -> Load unpacked and select this `gemini_extension` directory.

4. Open the exact normal Gemini conversation intended to act as the Arena endpoint.

5. Read the local token from `state/loopback_token.txt`. In the extension popup enter the Aura Endpoint ID, Visit ID, and that local token. Save.

6. Click **Load next Aura turn into Gemini**. The extension asks the loopback relay for one current pending turn and inserts its visible bootstrap packet into the Gemini composer.

7. **Review the prompt and press Gemini Send yourself.** The extension does not click Send in T1.

8. When Gemini has produced its visible answer, reopen the popup and click **Capture visible Gemini response -> Arena**.
   - Preferred fail-safe fallback: select the exact visible Gemini response text before clicking Capture.
   - If no selection exists, the content adapter accepts only one newly observed response-like DOM node; ambiguity refuses.

9. The popup hashes the visible text and posts `ArenaTurnResultV1` to the loopback relay. AuraOS validates endpoint/visit/head/currentness and persists an exactly-once result receipt.

## Why assisted first?

The goal is to prove the important invariant first: **normal Gemini browser turn -> visible answer -> source-bound Arena result**, without conflating that proof with autonomous web-UI control. Automatic send/wake is a separate `GUARDED_AUTO` transport mode and requires explicit owner enablement plus UI-drift, replay, stop-control, and provider-policy disposition.

## Recommission

A browser tab/conversation URL is only a locator, not authority. If the tab/session dies, release the VisitID, persist a debrief/reopen state in AuraOS, bind a new VisitID/conversation, and force normal Arena re-entry/currentness before further work.
