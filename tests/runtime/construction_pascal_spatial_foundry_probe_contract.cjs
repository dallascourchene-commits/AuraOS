"use strict";

/**
 * Pure, browser-independent CommonJS contract module.
 *
 * Exports the exact screenshot contract, expected fifteen-chapter order,
 * required evidence fields, and a pure evidence-result validator.
 *
 * The browser probe consumes this canonical contract rather than
 * duplicating it. Tests import this module to prove the contract
 * without executing Playwright.
 */

const SCREENSHOTS = Object.freeze({
  INITIAL: "00-bilateral-intent.png",
  FRAME_CONSTRUCTION: "01-design-3d.png",
  SHOW_FLOOR_PLAN: "02-floorplan-2d.png",
  SHOW_AS_BUILT: "03-as-built.png",
  COMPARE_REPRESENTATIONS: "04-compare.png",
  OBLIGATION_INSPECTOR: "05-obligation-inspector.png",
  TIMELINE_BUDGET_CREWS: "06-timeline-budget-crews.png",
  REVIEW_CANDIDATES: "07-construction-candidates.png",
  CONSTRUCTION_DECISION: "08-construction-decision.png",
  AURA_WATCH_THIS: "09-capture-started.png",
  MARK_INCIDENT: "10-incident-marked.png",
  FINALIZE_REPLAY: "11-replay-proof.png",
  RUN_RUNTIME_V2: "12-repair-route.png",
  DEGRADED_PREVIEW: "13-preview-rollback.png",
  CURRENT_REPROOF: "14-current-reproof.png",
  RETURN_TO_CONSTRUCTION: "15-observatory.png",
  DISSOLVE: "16-dissolved.png",
});

// 14 screenshot artifacts (INITIAL through DISSOLVE).
// The 15th chapter (RESTART) does not produce a screenshot — it resets.
const SCREENSHOT_VALUES = Object.freeze(Object.values(SCREENSHOTS));

// The exact fifteen-chapter order the Director must advance through.
const EXPECTED_CHAPTER_ORDER = Object.freeze([
  "INITIAL",
  "FRAME_CONSTRUCTION",
  "SHOW_FLOOR_PLAN",
  "SHOW_AS_BUILT",
  "COMPARE_REPRESENTATIONS",
  "OBLIGATION_INSPECTOR",
  "TIMELINE_BUDGET_CREWS",
  "REVIEW_CANDIDATES",
  "CONSTRUCTION_DECISION",
  "AURA_WATCH_THIS",
  "MARK_INCIDENT",
  "FINALIZE_REPLAY",
  "RUN_RUNTIME_V2",
  "DEGRADED_PREVIEW",
  "CURRENT_REPROOF",
  "RETURN_TO_CONSTRUCTION",
  "DISSOLVE",
  "RESTART",
]);

// Required terminal evidence fields that browser-evidence.json must contain.
const REQUIRED_EVIDENCE_FIELDS = Object.freeze([
  "relaunchSucceeded",
  "exactOrder",
  "allAuthorityFalse",
  "requestFailures",
  "externalRequests",
  "pageErrors",
  "sourceMutation",
  "productionMutation",
  "automaticMerge",
  "humanReviewRequired",
]);

/**
 * Validate an evidence result object against the canonical contract.
 * Returns { valid: true } on success, { valid: false, errors: string[] } on failure.
 */
function validateEvidence(evidence) {
  const errors = [];

  if (evidence === null || typeof evidence !== "object") {
    return { valid: false, errors: ["evidence is not an object"] };
  }

  // Check all required fields are present and not undefined.
  for (const field of REQUIRED_EVIDENCE_FIELDS) {
    if (!(field in evidence)) {
      errors.push(`missing required evidence field: ${field}`);
    }
  }

  // exactOrder must be an array matching EXPECTED_CHAPTER_ORDER.
  if (Array.isArray(evidence.exactOrder)) {
    if (evidence.exactOrder.length !== EXPECTED_CHAPTER_ORDER.length) {
      errors.push(
        `exactOrder has ${evidence.exactOrder.length} chapters, expected ${EXPECTED_CHAPTER_ORDER.length}`
      );
    } else {
      for (let i = 0; i < EXPECTED_CHAPTER_ORDER.length; i++) {
        if (evidence.exactOrder[i] !== EXPECTED_CHAPTER_ORDER[i]) {
          errors.push(
            `exactOrder[${i}] is "${evidence.exactOrder[i]}", expected "${EXPECTED_CHAPTER_ORDER[i]}"`
          );
        }
      }
    }
  } else {
    errors.push("exactOrder is not an array");
  }

  // Authority fields must all be false.
  if (evidence.allAuthorityFalse !== true) {
    errors.push("allAuthorityFalse is not true");
  }
  if (evidence.sourceMutation !== false) {
    errors.push("sourceMutation is not false");
  }
  if (evidence.productionMutation !== false) {
    errors.push("productionMutation is not false");
  }
  if (evidence.automaticMerge !== false) {
    errors.push("automaticMerge is not false");
  }
  if (evidence.humanReviewRequired !== true) {
    errors.push("humanReviewRequired is not true");
  }

  return errors.length === 0 ? { valid: true } : { valid: false, errors };
}

module.exports = {
  SCREENSHOTS,
  SCREENSHOT_VALUES,
  EXPECTED_CHAPTER_ORDER,
  REQUIRED_EVIDENCE_FIELDS,
  validateEvidence,
};
