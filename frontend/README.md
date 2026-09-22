# HawkerBridge web application

React, TypeScript, Vite and Leaflet. All product metrics come from the same-origin FastAPI service; there are no bundled demo responses or hardcoded credentials. Fonts and map geometry are served locally. There are no map-tile, font-CDN, or LLM requests in the application.

## Development

From this directory, run `npm ci`, then `npm run dev`. Vite proxies `/api` to `http://127.0.0.1:8000`; start the Python service using the repository README. Local registration and isolated guest sessions use the API's HttpOnly cookie and CSRF token. Databricks mode relies on the platform session.

`npm run build` type-checks the application and emits `dist/` for the backend to serve. `npm test` runs local component and transport tests. Run the complete React DOM workflow against an already running API with:

```sh
HAWKERBRIDGE_TEST_API=http://127.0.0.1:8000 npm test
```

The integration test creates an isolated guest, scopes an analysis, generates and saves a real proposal, edits/reviews it, obtains its brief, deletes it, and signs out. It does not contact partners or dispatch services. The map is mocked only inside that DOM test; visual rendering, keyboard map interaction, responsive layout and browser downloads require browser QA.

## Product safeguards

- All displayed exposure totals are explicitly census residents **in flagged subzones**, not identified individuals without food access.
- Meal uptake, unit costs, setup costs, capacity and senior priority are visible assumptions.
- Fixed-plan uptake sensitivity exposes matched meals and potential surplus.
- A proposed locality is a subzone point, not a booked or verified venue.
- Changed inputs disable proposal saving until recomputation. Failed analysis refreshes keep the previous result explicitly marked stale and disable optimisation.
- Date selection is restricted to the source schedule year. Planning-area scope travels through analysis, optimisation, and saved plans.
- Every saved-plan mutation is CSRF-protected; exports and briefs use the authenticated owner's API endpoints.

Primary screens are `Overview`, `Planner`, `SavedPlans`, and `Evidence`. `App.tsx` owns session, source snapshot, scoped analysis and navigation state. `api.ts` handles JSON errors and CSRF transport. `AccessMap.tsx` owns and cleans up its Leaflet instance, resize observer and data layers.
