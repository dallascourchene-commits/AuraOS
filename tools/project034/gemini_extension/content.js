(() => {
  "use strict";

  const STATE = {
    loadedTurnId: null,
    baselineResponseFingerprints: new Set(),
  };

  const COMPOSER_HINT = /(prompt|ask|enter|message|gemini|type)/i;
  const RESPONSE_SELECTORS = [
    "model-response",
    "[data-test-id*='response']",
    "[class*='model-response']",
    "[class*='response-container']",
    "[class*='response-content']"
  ];

  function isVisible(el) {
    if (!(el instanceof HTMLElement)) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function accessibleText(el) {
    return [
      el.getAttribute("aria-label"),
      el.getAttribute("placeholder"),
      el.getAttribute("data-placeholder"),
      el.getAttribute("role"),
    ].filter(Boolean).join(" ");
  }

  function findComposer() {
    const all = Array.from(document.querySelectorAll("textarea, [contenteditable='true']"))
      .filter(isVisible)
      .filter((el) => !el.closest("[aria-hidden='true']"));

    const hinted = all.filter((el) => COMPOSER_HINT.test(accessibleText(el)));
    const candidates = hinted.length ? hinted : all;
    if (candidates.length !== 1) {
      return {
        ok: false,
        code: candidates.length === 0 ? "GEMINI_COMPOSER_NOT_FOUND" : "GEMINI_COMPOSER_AMBIGUOUS",
        count: candidates.length,
      };
    }
    return { ok: true, el: candidates[0] };
  }

  function setComposerText(el, text) {
    el.focus();
    if (el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) {
      const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      if (!setter) throw new Error("NATIVE_VALUE_SETTER_MISSING");
      setter.call(el, text);
      el.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
      el.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
      return;
    }
    if (el.isContentEditable) {
      el.textContent = text;
      el.dispatchEvent(new InputEvent("input", {
        bubbles: true,
        composed: true,
        inputType: "insertText",
        data: text,
      }));
      return;
    }
    throw new Error("UNSUPPORTED_COMPOSER_TYPE");
  }

  function responseCandidates() {
    const seen = new Set();
    const out = [];
    for (const selector of RESPONSE_SELECTORS) {
      for (const el of document.querySelectorAll(selector)) {
        if (!isVisible(el)) continue;
        const text = (el.innerText || el.textContent || "").trim();
        if (text.length < 20) continue;
        const fp = `${el.tagName}:${text}`;
        if (seen.has(fp)) continue;
        seen.add(fp);
        out.push({ el, text, fp });
      }
    }
    return out;
  }

  function snapshotResponses() {
    STATE.baselineResponseFingerprints = new Set(responseCandidates().map((x) => x.fp));
  }

  function selectedVisibleText() {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return "";
    const text = selection.toString().trim();
    if (!text) return "";
    const range = selection.getRangeAt(0);
    const node = range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE
      ? range.commonAncestorContainer
      : range.commonAncestorContainer.parentElement;
    if (!node || !document.documentElement.contains(node)) return "";
    return text;
  }

  function captureVisibleResponse() {
    const selected = selectedVisibleText();
    if (selected) {
      return { ok: true, text: selected, capture_mode: "USER_SELECTION" };
    }

    const fresh = responseCandidates().filter((x) => !STATE.baselineResponseFingerprints.has(x.fp));
    if (fresh.length !== 1) {
      return {
        ok: false,
        code: fresh.length === 0 ? "GEMINI_NEW_RESPONSE_NOT_FOUND" : "GEMINI_RESPONSE_AMBIGUOUS",
        count: fresh.length,
        instruction: "Select the visible Gemini response text, then use Capture again.",
      };
    }
    return { ok: true, text: fresh[0].text, capture_mode: "ONE_NEW_RESPONSE_NODE" };
  }

  function showLoadedBadge(turnId) {
    document.getElementById("aura-gemini-assisted-badge")?.remove();
    const badge = document.createElement("div");
    badge.id = "aura-gemini-assisted-badge";
    badge.textContent = `Aura Arena turn ${turnId} loaded. Review it and press Gemini Send yourself.`;
    Object.assign(badge.style, {
      position: "fixed",
      right: "16px",
      bottom: "16px",
      zIndex: "2147483647",
      maxWidth: "360px",
      padding: "10px 12px",
      borderRadius: "8px",
      background: "rgba(20,20,20,0.94)",
      color: "white",
      fontFamily: "system-ui, sans-serif",
      fontSize: "13px",
      boxShadow: "0 4px 18px rgba(0,0,0,.3)",
    });
    document.body.appendChild(badge);
    setTimeout(() => badge.remove(), 15000);
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    try {
      if (message?.type === "AURA_LOAD_PROMPT") {
        if (location.origin !== "https://gemini.google.com") {
          sendResponse({ ok: false, code: "WRONG_ORIGIN" });
          return;
        }
        if (!message.turn_id || typeof message.prompt_text !== "string" || !message.prompt_text.trim()) {
          sendResponse({ ok: false, code: "INVALID_AURA_TURN" });
          return;
        }
        const found = findComposer();
        if (!found.ok) {
          sendResponse(found);
          return;
        }
        snapshotResponses();
        setComposerText(found.el, message.prompt_text);
        STATE.loadedTurnId = message.turn_id;
        showLoadedBadge(message.turn_id);
        sendResponse({
          ok: true,
          turn_id: message.turn_id,
          mode: "ASSISTED_HUMAN_SEND_REQUIRED",
        });
        return;
      }

      if (message?.type === "AURA_CAPTURE_VISIBLE_RESPONSE") {
        if (!STATE.loadedTurnId) {
          sendResponse({ ok: false, code: "NO_AURA_TURN_LOADED" });
          return;
        }
        const capture = captureVisibleResponse();
        sendResponse({ ...capture, turn_id: STATE.loadedTurnId });
        return;
      }

      if (message?.type === "AURA_CLEAR_TURN") {
        STATE.loadedTurnId = null;
        STATE.baselineResponseFingerprints = new Set();
        sendResponse({ ok: true });
        return;
      }

      sendResponse({ ok: false, code: "UNKNOWN_MESSAGE" });
    } catch (error) {
      sendResponse({ ok: false, code: "CONTENT_ADAPTER_ERROR", detail: String(error?.message || error) });
    }
  });
})();
