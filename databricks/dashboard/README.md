# HawkerBridge AI/BI evidence dashboard

`hawkerbridge-evidence.lvdash.json` is a real Lakeview dashboard definition, deployed by `resources/dashboard.yml` through the root bundle's existing `resources/*.yml` include. It contains SQL and presentation settings only: no query-result cache, workspace ID, token, user identity or invented chart values.

The four widgets read the latest successful publication through the pipeline's governed views:

| Widget | Dataset and purpose |
| --- | --- |
| Centres scheduled closed | `published_closure_calendar`, fixed to **28 September 2026**. Infrastructure count, not people missing meals. |
| Allocation versus baseline | `published_evaluations`, fixed to **22 September 2026**, comparing weighted meal benefit at each published budget with the largest-demand-first baseline. Both series use the same published scenario assumptions. |
| Source provenance | `published_bronze_sources`, showing original fetch/reuse metadata, source route, full SHA-256 and official dataset URL. No reuse marker is not a claim of a fresh fetch. |
| Unresolved interval review | `published_quarantine` joined to `published_centres`. Retains malformed or partial intervals for review; unresolved never means confirmed open. |

The first row pairs the closure counter with a grouped teal/gold comparison. Full-width source and quarantine tables follow; long hashes and URLs remain available without shortening the underlying data. All titles expose the scope of the result. The different dates are deliberate: the closure example uses the pitch date, while the chart uses one of the pipeline's predeclared evaluation dates. This small dashboard avoids filter/parameter ambiguity; arbitrary dates and budgets remain available in the application.

## Deploy after a successful publication

The resource reuses `${var.warehouse_id}` and binds `${var.catalog}` / `${var.schema}` through the officially supported `dataset_catalog` and `dataset_schema` fields. Queries contain unqualified view names, so there is no templating or arbitrary string substitution inside SQL. Do not hardcode a personal namespace into the JSON. [Databricks namespace binding example](https://docs.databricks.com/aws/en/dev-tools/bundles/examples#dashboard-catalog-and-schema-parameterization)

The normal root deployment creates/updates the resource. Run the pipeline before refreshing dashboard datasets; a dashboard created before its views exist cannot query them yet. Exclude `databricks/dashboard/*.lvdash.json` from ordinary bundle file sync when using dashboard Git support, as described in the [dashboard resource documentation](https://docs.databricks.com/aws/en/dev-tools/bundles/resources#dashboard), to prevent duplicate workspace assets. The bundle resource still reads its local `file_path`.

After the root bootstrap has authenticated, deployed and published data:

```sh
databricks bundle summary --target dev --profile hawkerbridge
```

Open the `hawkerbridge_evidence` resource link returned by that command. Refresh the four datasets. Before sharing, inspect both SQL results and visual layout in the target workspace. If a separate publish action is required, use the actual returned dashboard ID:

```sh
databricks lakeview publish "$HAWKERBRIDGE_DASHBOARD_ID" \
  --embed-credentials=false --profile hawkerbridge
databricks lakeview get "$HAWKERBRIDGE_DASHBOARD_ID" \
  --profile hawkerbridge --output json
databricks lakeview get-published "$HAWKERBRIDGE_DASHBOARD_ID" \
  --profile hawkerbridge --output json
```

The dashboard resource explicitly sets `embed_credentials: false`. It neither broadens access nor creates a schedule. Viewers need dashboard access, permission to use the existing warehouse, namespace usage and SELECT on the five views listed above. The authenticated app's principal has a different, smaller table-access contract; do not grant access to private saved plans to make this dashboard work. Publishing with viewer credentials is not public or anonymous access. [Databricks dashboard resource reference](https://docs.databricks.com/aws/en/dev-tools/bundles/resources#dashboard)

If a teammate edits the dashboard in the UI, export or use `bundle generate dashboard` to bring those edits back into source before redeploying. Do not force an overwrite of an unreviewed remote edit. [Databricks bundle commands](https://docs.databricks.com/aws/en/dev-tools/cli/bundle-commands#databricks-bundle-generate)

## Offline validation

The dashboard format follows the counter v2, bar v3, table v1 and six-column layout demonstrated in the [official Databricks bundle example](https://github.com/databricks/bundle-examples/blob/main/knowledge_base/dashboard_nyc_taxi/src/nyc_taxi_trip_analysis.lvdash.json). Its complete contents round-trip through the [Databricks Labs generated Lakeview model](https://github.com/databrickslabs/lsql/blob/main/src/databricks/labs/lsql/lakeview/model.py), detecting unsupported/lost fields. This is additional static assurance, not a server-side rendering guarantee.

From the repository root, without workspace credentials:

```sh
.tools/databricks/databricks bundle schema > /tmp/hawkerbridge-dashboard-bundle-schema.json
uv run --no-project \
  --with databricks-labs-lsql==0.17.0 --with jsonschema --with pyyaml \
  --with regex --with sqlglot --with duckdb \
  python databricks/dashboard/validate.py \
  --bundle-schema /tmp/hawkerbridge-dashboard-bundle-schema.json
```

The validator checks the resource against the **installed CLI's actual schema**, Lakeview model compatibility, non-overlapping layout, field references, read-only Databricks SQL and permitted unqualified views. It executes the actual dataset SQL in DuckDB using real archived sources and real stored local evaluation outputs. The latter validates query semantics and column contracts; cloud scenario budgets come from the actual published pipeline and are not replaced by local outputs. A separate `bundle validate --strict` with real deployment variables is still required in the authenticated workspace.

Recorded on 22 September 2026 with **Databricks CLI 1.17.0**: all offline checks passed; the archive yielded 17 scheduled closed centres, six comparison rows, five source rows and 32 quarantine rows. No dashboard creation, cloud SQL execution, publication or visual rendering in Databricks is claimed by these checks. Record the actual resource ID, warehouse query success and screenshot after deployment.
