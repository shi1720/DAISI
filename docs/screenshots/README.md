# Verified product screenshots

These are real Chromium captures of the running HawkerBridge application, backed by its Python API and the acquired Singapore public-data snapshot. They are not mockups. The application was exercised in an isolated guest workspace using synthetic test records.

The captures come from [successful GitHub Actions run 35689097551](https://github.com/shi1720/DAISI/actions/runs/35689097551), source commit `94b96cf7994093bc77a23eac1171c9a2624a784e`, on 22 September 2026. All four browser journeys passed, including account creation/sign-in, saved-plan review/export, scoped planning, zero-budget behavior, and mobile navigation. The overview Axe scan returned no violations for its configured WCAG 2 A/AA rules. This automated check is not a claim of comprehensive accessibility certification.

| Image | Capture | What it shows |
|---|---|---|
| [welcome.png](welcome.png) | 1440 × 1040 | Guest access and real account sign-in |
| [overview.png](overview.png) | 1440 × 1000 viewport | 28 September 2026; all Singapore; 800 m threshold; 17 scheduled closures and 6 subzones flagged for review |
| [planner.png](planner.png) | 1440 × 1000 viewport | S$1,500 scenario: 225 planned meals at 2 unverified collection localities |
| [capacity-comparison.png](capacity-comparison.png) | 1440 × 1000 viewport | S$6,000 available, S$2,700 allocated, 450 planned meals; the three-locality capacity limit binds |
| [saved-plan.png](saved-plan.png) | 1440 × 1531 full page | Real saved browser-test proposal, review checkpoint, assumptions, notes, brief and successful PDF export |
| [evidence.png](evidence.png) | 1440 × 3208 full page | Source records, methodological limits, data-quality checks and computational benchmark |
| [mobile-overview.png](mobile-overview.png) | 390 × 2613 full page | Mobile overview without document-level horizontal overflow |
| [mobile-planner.png](mobile-planner.png) | 390 × 3399 full page | Mobile assumptions, allocation, comparison and uptake sensitivity |

The saved plan's **Reviewed** status records acknowledgement of modelling assumptions and the need for future verification. It does not indicate a verified venue, confirmed meal demand, operator agreement or dispatched service. No real partners were contacted. Population figures are Census 2020 residents in flagged subzones; meals are planning assumptions, not people actually served.

The PNGs are unmodified copies of the CI output. Because GitHub artifact storage was full, the workflow also preserved their bytes in tagged log records. `browser-tests/extract-evidence.mjs` decoded the records and verified each byte count and SHA-256 digest. [provenance.json](provenance.json) records image hashes, dimensions, source names, commit, run and data-snapshot provenance.

To reproduce the browser verification, run the repository's `Verify HawkerBridge` workflow. To decode its screenshot fallback:

```sh
gh run view RUN_ID --log > run.log
node browser-tests/extract-evidence.mjs run.log output/recovered-evidence
```

The separate `record_demo=true` workflow option records a real, silent walkthrough for Shivam Gupta's voiceover. It was intentionally skipped in the screenshot-verification run above.
