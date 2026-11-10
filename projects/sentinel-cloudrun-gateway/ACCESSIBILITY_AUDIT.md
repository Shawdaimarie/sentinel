# SENTINEL Explorer accessibility review

**Standard:** WCAG 2.1 AA checklist · **Date:** 2026-11-02 · **Environment:** local synthetic explorer in Chrome accessibility tree

## Summary

No blocking keyboard or label issue was observed in the manual browser pass. Three improvements were made during review: a visible high-contrast keyboard focus ring, 44px minimum controls, and stronger footer contrast. The page now exposes the approval queue as a polite live region and errors as alerts.

## Checks and outcomes

| Area | Result | Evidence / limits |
|---|---|---|
| Semantics and names | Pass | Chrome accessibility tree exposed page title, headings, field labels, native select, buttons, status text and alert-capable error node. Decorative logo/arrow are hidden from assistive tech. |
| Keyboard | Pass | Tab order observed: identity, customer record, proposed note, run task, refresh, approval/denial controls, audit verification. Native select supports its standard keyboard operation. A visible focus outline was observed on the identity select. |
| Form labels | Pass | Each field is nested within a visible `<label>`; no placeholder-only fields. |
| Contrast | Pass for reviewed text pairs | Body `#edf2f8` on `#080d15`: 17.30:1. Muted text `#75879b` on panel `#101b28`: 4.71:1. Footer was initially 4.05:1 and changed from `#627488` to `#8295aa` (6.33:1 on `#080d15`). Normal text minimum: 4.5:1. |
| Target size | Improved | Inputs, select, and buttons now have 44px minimum height, including compact approval actions. |
| Responsive | Partially reviewed | CSS collapses the two-column panels to one column at 750px and hides the decorative hero statistic. A full 200% zoom/browser matrix was not run. |
| Screen reader | Not fully verified | Accessibility tree inspection is not a substitute for VoiceOver/NVDA. No assistive-technology session was available for this review. |

## Changes

- Added named section groupings and a polite live region for approval queue updates.
- Added `role="status"` to gateway health and `role="alert"` to request errors.
- Added `:focus-visible` styling with a 3px cyan outline and 2px offset.
- Increased controls to 44px minimum height and raised footer contrast.

## Remaining evidence

Run a VoiceOver/NVDA pass and verify 200% zoom in a hosted IAP session before awarding the usability/accessibility score. The application remains a local synthetic prototype; these observations are not a formal accessibility conformance claim.
