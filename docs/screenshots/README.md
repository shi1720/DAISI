# Verified hosted product screenshots

These are unmodified Chromium captures from the real [Firebase application](https://hawkerbridge-sg.web.app), using its Python API and verified Databricks publication. They are not mockups. The source revision is `b539db724c3731897595e81061a73070655920cf`.

Screenshots were captured in the passing main and mobile journeys of [run 35697233597](https://github.com/shi1720/DAISI/actions/runs/35697233597). All six configured Axe scans returned no violations. The full run found a separate five-second readiness timeout while a successful initial analysis was loading; it is not labelled a passing run. [Final hosted acceptance 35697740614](https://github.com/shi1720/DAISI/actions/runs/35697740614) passed all four journeys, six Axe scans and 320px/390px layouts. Exact revisions are recorded in `submission/deployment-status.json`. The readiness change alters the test, not the pictured application.

| Image | What to inspect |
| --- | --- |
| welcome.png | Guest access and real account sign-in |
| overview.png | 28 September, 800 m, 17 closures and six subzones flagged for review |
| planner.png | S$1,500 and 225 planned meals |
| capacity-comparison.png | S$6,000 available, 450 planned meals, S$2,700 allocated |
| saved-plan.png | Synthetic 225-meal proposal, notes, review checkpoint and PDF export |
| evidence.png | Sources, limitations, publication and separate local benchmark |
| databricks-publication.png | Actual nine cloud scenarios, twelve passing checks and five sources |
| mobile-overview.png | 390px mobile overview |
| mobile-planner.png | 390px mobile planning workflow |
| small-mobile-planner.png | 320px layout, including all four budget presets |

A test proposal's Reviewed status acknowledges modelling assumptions and the need for future operational checks. It does not establish a verified venue, confirmed demand, operator agreement or delivered meals. All test notes are synthetic. Population figures are Census 2020 area totals.

`provenance.json` records original names, dimensions and SHA256 hashes. The workflow preserves screenshot bytes in logs as a fallback when artifact storage is unavailable. Decode them with `node browser-tests/extract-evidence.mjs run.log output/recovered-evidence`. The final narrated video uses an earlier actual hosted recording whose separate provenance is preserved in `output/demo-footage/provenance.json`.
