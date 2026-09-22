# HawkerBridge implementation contract

Root owns FastAPI API, model/optimisation engine, auth/local persistence, integration/tests/docs.
Data agent owns backend/hawkerbridge/ingest.py, scripts/refresh_data.py, tests/test_ingest.py, data/*.
Frontend agent owns frontend/*, frontend UI tests. Platform agent owns databricks/*, resources/*, databricks.yml, app.yaml, backend/hawkerbridge/databricks_store.py and platform docs/tests.

Brand: **HawkerBridge**. A closure continuity desk for Singapore. Warm ivory, forest teal, vermilion signal. Editorial refined, big readable type, polished SVG/Leaflet map, restrained purposeful cards. No chat wrapper. Main workflow: select a date, inspect who loses nearby hawker access, compare a budgeted support plan, save/export. Saved scenario is a planning proposal requiring site and operator verification, not actual dispatched help.

## JSON API
All /api endpoints same origin. Errors JSON {detail:string}. GET /api/health public. Auth GET /api/auth/session -> {user:null|{id,name,email,mode:'guest'|'local'|'databricks'},csrf_token:string|null,auth_mode:'local'|'databricks'}. POST /api/auth/demo {} creates isolated guest session. POST /api/auth/register {name,email,password}, POST /api/auth/login {email,password}, POST /api/auth/logout {}. Successful auth returns same session envelope. Use HttpOnly cookie (fetch credentials same-origin) and send X-CSRF-Token on all mutations after auth. Guests may save their own plans. Real account registration is local deployment only; Databricks uses platform sign-in. Do not hardcode credentials.

GET /api/snapshot (authenticated) returns top-level manifest,centres,closures,demand_zones,boundaries (GeoJSON).
centres = {id,name,lat,lng,address,planning_area,food_stalls,market_stalls}
closures = {id,centre_id,start_date,end_date,kind:'cleaning'|'works',source_text}
demand_zones = {id,name,planning_area,lat,lng,residents,seniors,geometry?:GeoJSON}
manifest contains fetched_at,sources,quality,limitations, population_year, closures_year. UI adapt optional fields.

POST /api/analyse {date:'YYYY-MM-DD',radius_m:800,senior_weight:2,rescheduled_closure_ids:[]} ->
{
 date, radius_m, data_as_of, model_version,
 summary:{total_centres,closed_centres,total_residents,total_seniors,baseline_covered_residents,remaining_covered_residents,newly_exposed_residents,newly_exposed_seniors,affected_zones,food_stalls_closed},
 centres:[...centre,status:'open'|'closed',active_closures:[...]],
 zones:[...demand_zone,baseline_distance_m,current_distance_m,baseline_centre_id,current_centre_id,baseline_covered:boolean,current_covered:boolean,newly_exposed:boolean,priority_score:number],
 area_ranking:[{planning_area,residents,seniors,newly_exposed_residents,newly_exposed_seniors,coverage_pct,centres,closed_centres}],
 calendar:[{date,closed_centres,food_stalls_closed}],
 limitations:[string],source_fingerprint:string
}
Use null distances if unavailable. Data coverage and proxy caveats prominently visible.

POST /api/optimise {...analysis params,budget:1500,site_cost:300,meal_cost:4,meals_per_site:150,max_sites:3,participation_rate:0.05} ->
{
 analysis:<same analysis>,
 assumptions:{budget,site_cost,meal_cost,meals_per_site,max_sites,participation_rate,...},
 sites:[{zone_id,name,planning_area,lat,lng,meals,estimated_demand,cost,covered_zone_ids:[string],priority_weighted_meals:number}],
 summary:{budget,spent,unspent,total_meals,estimated_demand,unmet_demand,sites_selected,weighted_benefit,baseline_weighted_benefit,improvement_pct,solver_status},
 baseline:{name:'Largest demand first',total_meals,weighted_benefit,spent},
 sensitivity:[{participation_rate,estimated_demand,planned_meals,unmet_demand}],
 explanation:string,limitations:[string],model_version:string,source_fingerprint:string
}
All meal figures are ASSUMED participation of newly exposed residents, never observed demand or people actually helped. Costs in SGD per day. Candidate sites = proposed collection locality represented by subzone point, no claim a booked/available venue. Optimisation decision is one day.

GET /api/plans -> {plans:[{id,title,status:'draft'|'reviewed',created_at,updated_at,date,summary,...}]}
POST /api/plans {title:string,parameters:<optimise inputs>,notes:string} -> plan with result computed SERVER-side.
GET /api/plans/{id} -> plan (includes parameters,result,notes)
PATCH /api/plans/{id} {title?:string,notes?:string,status?:'draft'|'reviewed'} -> plan
DELETE /api/plans/{id} -> 204
GET /api/plans/{id}/export?format=json|csv|pdf -> download (auth owner only)
GET /api/evidence -> {manifest,methodology:{...},evaluation?:{...}}
GET /api/brief?plan_id=id -> deterministic sourced prose within saved plan, no LLM keys.

## Platform persistence interface
DatabricksStore(config): load_snapshot()->dict; list_plans(owner_id)->list[dict]; get_plan(owner_id,plan_id)->dict|None; save_plan(owner_id,plan:dict)->None; delete_plan(owner_id,plan_id)->bool. Plan object id,title,status,created_at,updated_at,date,parameters,result,notes. SQL bind parameters. SDK statement execution. Tables gold_snapshots(snapshot_json,created_at), application_plans(owner_id,plan_id,plan_json,updated_at). Fail closed on missing warehouse/config; no implicit demo fallback. Owner comes ONLY from platform identity in Databricks mode. Pipeline writes snapshot table with model inputs and gold entity tables; registers data quality and optimiser evaluation via MLflow. Auth mode enabled explicitly only within Databricks runtime.
