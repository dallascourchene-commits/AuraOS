((global) => {
  "use strict";

  function requiredFunction(value, name) {
    if (typeof value !== "function") {
      throw new TypeError(`${name} must be a function`);
    }
    return value;
  }

  function shouldPaceAfterChapter(chapter) {
    return Boolean(chapter && chapter.consequential !== true);
  }

  function waitForPresentation({
    activeView,
    getControl,
    getStage,
    now = Date.now,
    schedule = setTimeout,
    timeoutMs = 15000,
    pollMs = 40,
  }) {
    if (typeof activeView !== "string" || !activeView.trim()) {
      return Promise.reject(new TypeError("activeView must be a non-empty string"));
    }
    const control = requiredFunction(getControl, "getControl");
    const stage = requiredFunction(getStage, "getStage");
    const clock = requiredFunction(now, "now");
    const scheduler = requiredFunction(schedule, "schedule");
    const timeout = Number(timeoutMs);
    const interval = Number(pollMs);
    if (!Number.isFinite(timeout) || timeout < 0 || !Number.isFinite(interval) || interval < 0) {
      return Promise.reject(new TypeError("presentation wait timing must be finite and non-negative"));
    }
    const normalizedView = activeView.trim().toUpperCase();
    const expectedMode = normalizedView.toLowerCase().replaceAll("_", "-");
    const deadline = clock() + timeout;
    return new Promise((resolve, reject) => {
      const check = () => {
        const target = control(normalizedView);
        const presentation = stage();
        if (
          target?.getAttribute?.("aria-pressed") === "true"
          && presentation?.dataset?.presentationMode === expectedMode
        ) {
          resolve({ activeView: normalizedView, presentationMode: expectedMode });
          return;
        }
        if (clock() >= deadline) {
          reject(new Error(`P3 did not retain the exact ${normalizedView} presentation receipt`));
          return;
        }
        scheduler(check, interval);
      };
      check();
    });
  }

  async function settleDirective(effect, render) {
    const apply = requiredFunction(effect, "effect");
    const repaint = requiredFunction(render, "render");
    try {
      return await apply();
    } finally {
      repaint();
    }
  }

  global.AuraConstructionDirectorContract = Object.freeze({
    settleDirective,
    shouldPaceAfterChapter,
    waitForPresentation,
  });
})(globalThis);
