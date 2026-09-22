-- HawkerBridge AI/BI dashboard query pack.
-- Select the deployed catalog and schema in the SQL editor before running each query.
-- Queries use published_* views, so incomplete staging runs never appear.
-- In AI/BI, create one dataset per SELECT. Use :evaluation_date as a DATE parameter.

-- 1. Publication status. Show input_mode, source date and demographic year together.
SELECT publication_id, created_at AS published_at, input_mode,
       get_json_object(snapshot_json, '$.manifest.fetched_at') AS source_snapshot_at,
       get_json_object(snapshot_json, '$.manifest.population_year') AS population_year,
       get_json_object(snapshot_json, '$.manifest.quality.quarantined_closure_intervals') AS quarantined_intervals,
       mlflow_run_id
FROM gold_snapshots
ORDER BY created_at DESC, publication_id DESC
LIMIT 1;

-- 2. Closures over time: an operational schedule, not a permanent-closure trend.
SELECT closure_date, closed_centres, food_stalls_closed
FROM published_closure_calendar
WHERE year(closure_date) = 2026
ORDER BY closure_date;

-- 3. Populations of flagged subzones at the selected precomputed evaluation date.
-- This is an 800 m representative-point screen, not individual-level lost access.
SELECT planning_area, newly_exposed_residents AS residents_in_flagged_subzones,
       newly_exposed_seniors AS seniors_in_flagged_subzones,
       coverage_pct AS representative_point_coverage_pct,
       centres, closed_centres, radius_m
FROM published_access_by_area
WHERE evaluation_date = CAST(:evaluation_date AS DATE)
ORDER BY newly_exposed_seniors DESC, planning_area;

-- 4. Genuine model comparison under the same daily budget and assumptions.
SELECT evaluation_date, budget AS daily_budget_sgd, planned_meals, spent AS proposed_spend_sgd,
       weighted_benefit, baseline_weighted_benefit, improvement_pct, solver_status, runtime_seconds
FROM published_evaluations
ORDER BY evaluation_date, budget;

-- 5. Governed source evidence: retain provenance of any reused geometry.
SELECT source_key, dataset_id, source_url, transport_url, source_fetched_at,
       archived_reused_at, mirror, sha256, byte_count
FROM published_bronze_sources
ORDER BY source_key;

-- 6. Review queue: unresolved is not the same as open.
SELECT q.centre_id, c.name, q.kind, q.source_start, q.source_end, q.reason, q.source_text
FROM published_quarantine q
LEFT JOIN published_centres c ON q.centre_id = c.id
ORDER BY q.reason, c.name;

-- 7. Static cooked-food coverage context per 10,000 Census 2020 residents.
-- Zero-food-stall markets remain in inventory but cannot improve cooked-food coverage.
-- Pre-aggregate each side to avoid multiplying people by centres in a join.
WITH populations AS (
  SELECT planning_area, sum(residents) AS residents, sum(seniors) AS seniors
  FROM published_demand_zones GROUP BY planning_area
), centres AS (
  SELECT planning_area, count(*) AS inventory_centres,
         sum(CASE WHEN food_stalls > 0 THEN 1 ELSE 0 END) AS food_centres,
         sum(food_stalls) AS food_stalls
  FROM published_centres GROUP BY planning_area
)
SELECT p.planning_area, p.residents, p.seniors,
       coalesce(c.inventory_centres, 0) AS inventory_centres,
       coalesce(c.food_centres, 0) AS food_centres,
       coalesce(c.food_stalls, 0) AS food_stalls,
       CASE WHEN p.residents > 0 THEN coalesce(c.food_centres, 0) * 10000.0 / p.residents END AS food_centres_per_10000_residents
FROM populations p LEFT JOIN centres c USING (planning_area)
ORDER BY food_centres_per_10000_residents ASC NULLS LAST;

-- 8. National food-waste context only; never label this centre-level waste avoided.
SELECT year, generated_tonnes, recycled_tonnes, disposed_tonnes, recycling_rate_percent
FROM published_food_waste ORDER BY year;

-- 9. Quality gates and lineage for judge inspection.
SELECT check_name, passed, observed_value, detail, checked_at
FROM published_quality_audit ORDER BY check_name;

SELECT parent_asset, child_asset, transformation
FROM published_lineage_edges ORDER BY parent_asset, child_asset;
