# HawkerBridge: source and modeling feasibility

Verified 22 September 2026. Files in `data/raw/baseline-20260922` are the reproducible initial baseline. Each has a SHA-256 and retrieval provenance. `data/processed/snapshot.json` is built from verified sources, and the live refresh was exercised successfully. The core ingestion uses public APIs without an account or API key.

## Sources

| Source | Dataset / URL | Observed coverage | Use |
|---|---|---|---|
| NEA Dates of Hawker Centres Closure | [d_bda4baa634dd1cc7a6c7cad5f19e2d68](https://data.gov.sg/datasets/d_bda4baa634dd1cc7a6c7cad5f19e2d68/view) | 123 rows, 27 columns, 2026 quarterly cleaning schedule plus selected other works from earlier years | Operational centre inventory, coordinates, food/market stall counts, dated shutdowns |
| SingStat Resident Population by Planning Area/Subzone of Residence, Age Group and Sex, Census 2020 | [d_d95ae740c0f8961a0b10435836660ce0](https://data.gov.sg/datasets/d_d95ae740c0f8961a0b10435836660ce0/view) | 388 rows: national total, 55 planning-area totals, 332 subzones | Observed resident population and sum of six 65+ age bands |
| URA Master Plan 2019 Planning Area Boundary, no sea | [d_4765db0e87b9c86336792efe8a1f7a66](https://data.gov.sg/datasets/d_4765db0e87b9c86336792efe8a1f7a66/view) | 55 polygons | Planning-area density and exact centre spatial join |
| URA Master Plan 2019 Subzone Boundary, no sea | [d_8594ae9ff96d0c708bc2af633048edfb](https://data.gov.sg/datasets/d_8594ae9ff96d0c708bc2af633048edfb/view) | 332 polygons | Join every census subzone; derive a geographic representative point |
| SingStat / NEA Waste Management and Overall Recycling Rates, Annual | [d_daf568968ab40dc81e7b08887a83c8fa](https://data.gov.sg/datasets/d_daf568968ab40dc81e7b08887a83c8fa/view) | 60 series, 2000–2025 | National food-waste context: generated, recycled, disposed, recycling rate |

All official dataset pages state the Singapore Open Data Licence and permit personal/commercial reuse. Attribution is required; see [Open Data Licence](https://data.gov.sg/open-data-licence). The licence does not imply government endorsement. Databricks Free Edition itself is non-commercial: commercial operation requires a separate supported paid deployment.

The [NEA hawker GeoJSON](https://data.gov.sg/datasets/d_4a086da0a5553be1d89383cd90d07ecd/view) was also examined. It includes proposed/under-construction sites, so the closure table's operational universe was chosen for the working inventory. Do not count future sites as currently accessible centres.

## Acquisition results

The documented legacy API works:

`GET https://data.gov.sg/api/action/datastore_search?resource_id=<dataset_id>&limit=1000&offset=0`

Response is `{"success":true,"result":{"fields":[...],"records":[...],"total":123,...}}`. Rows contain `_id`. Page through until `total` is reached, validate complete pagination, and retain the source payload. Population, closure and waste acquisitions were actually run.

The v2 list-rows endpoint returned HTTP 403 in this environment, while legacy tabular acquisition worked. The v1 poll-download geometry endpoint initially returned 403, then recovered. A clean refresh from an empty directory succeeded with **all five datasets downloaded directly from official data.gov.sg endpoints**, without any mirrored input. The delivered `data/raw/baseline-20260922` and current processed snapshot contain these official bytes with `mirror: false` for every source. No account or key was required.

The geometry API is:

`GET https://api-open.data.gov.sg/v1/public/api/datasets/<dataset_id>/poll-download`

A successful response has `code: 0` and `data.url`. Download that HTTPS URL to obtain the GeoJSON. The implementation records the canonical public endpoint rather than expiring signed download parameters. The original files have native URA properties such as `PLN_AREA_N`, `PLN_AREA_C`, `SUBZONE_N` and `SUBZONE_C`.

For resilience, explicitly opt-in archived-geometry fallback is implemented and always flagged if used. Earlier research copies, retained outside the delivered baseline, came from:

- Planning areas: [public download mirror](https://drive.google.com/uc?export=download&id=1kwvpiabQyc49CErAP5cTXarO7x5sWTeX), linked by [AFI's tutorial](https://www.afi.io/blog/upload-and-style-datasets-using-the-maps-datasets-api/).
- Subzones: [pinned public research repository data file](https://raw.githubusercontent.com/ethan-cyj/Public-Transportation-In-Singapore/660517a4afe692938477d8326efa8f20bd71f88d/data/SP1/MasterPlan2019SubzoneBoundaryNoSeaGEOJSON.geojson).

These fallback files are not used by the delivered baseline. Existing geometry can be reused after checksum verification because it changes slowly; its original retrieval time survives reuse. Fresh tabular records still receive current retrieval times.

Current SingStat 2025 demographic download links discovered from the Population Trends 2025 reference returned 404. The implementation deliberately uses clearly labelled Census 2020 observations rather than claiming current population. A future upgrade should acquire the latest SingStat demographic CSV, preserve that snapshot, and change observation-year metadata.

## Quality findings

- 123 centres, 6,681 listed cooked-food stalls. All coordinates valid in Singapore and all centres join to exactly one planning area.
- 460 resolved cleaning intervals plus 47 resolved other-works intervals = 507 retained intervals.
- 26 TBC/otherwise unresolved intervals are quarantined. No missing date is converted into a fabricated date.
- Six staggered block closures are quarantined. Circuit Road 79/79A and Haig Road 13/14 sometimes have different closure dates by block; centre-wide closures cannot be inferred when block-level stall counts are unavailable. The special remark that both blocks close together is retained.
- 332/332 census subzones join to geography using planning area plus normalized subzone name. 286 have a nonzero rounded resident count.
- Subzone resident counts sum to 4,044,340; senior age-band counts sum to 614,900. These differ from published national aggregates because of rounding. Preserve the actual observations; do not rescale them to make totals look exact.
- SingStat `-` is nil/negligible, so it is represented as zero with the rounding caveat. Other unknown numeric tokens fail validation rather than silently becoming zero.
- Polygon representative points are inside the corresponding geometry. They are neither homes nor population-weighted centroids. Straight-line distances from those points are only a screening proxy, particularly in large subzones.
- National food waste in 2025 is 790,000 tonnes generated, 140,000 tonnes recycled, 649,000 tonnes disposed, 18% recycled. Rounded quantities need not sum exactly. National waste is not a direct label for hawker waste, centre-level waste or preventable surplus.

## Defensible analytics

1. **Observed infrastructure density:** centres and listed food stalls per 10,000 Census 2020 residents, with year stated in the chart. Use planning-area published totals for that area-level denominator.
2. **Calendar exposure:** known full-centre closures per date, by area, with unresolved source intervals shown separately. Do not describe the present calendar as a complete permanent/temporary closure history.
3. **Access-screening scenarios:** compare distance from the same subzone representative point to listed centres in baseline versus closure scenarios. Label straight-line/proxy distance, not walking time. Include the omissions of coffee shops and other providers.
4. **Capacity-constrained allocation:** treat per-stall throughput, available spare capacity and participation rate as explicitly adjustable assumptions. Solve allocation/continuity decisions under those constraints. Show sensitivity bands and how recommendations change.
5. **Waste scenario:** calculate potential overproduction from explicit operator-entered meals and waste assumptions; national waste statistics can contextualize the problem. Do not downscale a national total into a pretend measured hawker label.
6. **Validation:** deterministic conservation checks, impossible-capacity cases, closed-destination exclusion, capacity limits, baseline comparison and sensitivity tests are meaningful. Training a model on a score formula and calling it predictive accuracy is not.

The strongest product promise is operational preparation: prioritize which closures require local review, compare backup capacity, record a coordinator's plan and export an action brief. Actual residents helped, spare capacity, sales, reduced waste and partner uptake need pilot measurement.

## Integration

- `build_snapshot(raw_dir) -> dict`: deterministic normalization plus checksum/contract checks. Builds no synthetic people.
- `refresh(data_dir, allow_mirror=False, reuse_geometry=True) -> dict`: fetches sources, stages immutable raw bundle, builds and validates, then atomically replaces the processed JSON.
- Raw bundles: `data/raw/<run_id>/{closures.json,population2020.json,planning_areas.geojson,subzones.geojson,waste.json,provenance.json}`.
- Source manifest `raw_path` is relative to `data/` and supplies SHA-256, URL, transport, mirror flag, agency, title and retrieval timestamp.
- CLI: `python scripts/refresh_data.py`. Offline: `python scripts/refresh_data.py --rebuild data/raw/baseline-20260922`.
- Eight tests cover geographic completeness, observed population preservation, unresolved/partial closures, corrupted raw input, pagination changes, failed refresh retention and atomic publication failure. Both incremental live refresh and a clean full refresh from an empty data directory completed successfully. The full refresh used official sources exclusively.
