import type { GeoJsonObject, Geometry } from 'geojson';

export type User = { id: string; name: string; email: string; mode: 'guest' | 'local' | 'databricks' };
export type Session = { user: User | null; csrf_token: string | null; auth_mode: 'local' | 'databricks' };
export type Closure = { id: string; centre_id: string; start_date: string; end_date: string; kind: 'cleaning' | 'works'; source_text: string };
export type Centre = { id: string; name: string; lat: number; lng: number; address: string; planning_area: string; food_stalls: number; market_stalls: number; food_access_eligible?: boolean };
export type AnalysedCentre = Centre & { status: 'open' | 'closed'; active_closures: Closure[] };
export type Zone = { id: string; name: string; planning_area: string; lat: number; lng: number; residents: number; seniors: number; geometry?: Geometry };
export type AnalysedZone = Zone & { baseline_distance_m: number | null; current_distance_m: number | null; baseline_centre_id: string | null; current_centre_id: string | null; baseline_covered: boolean; current_covered: boolean; newly_exposed: boolean; priority_score: number };
export type Source = { name?: string; title?: string; url?: string; dataset_id?: string; [key: string]: unknown };
export type Manifest = { fetched_at?: string; sources?: Source[] | Record<string, unknown>; quality?: Record<string, unknown>; limitations?: string[]; population_year?: number | string; closures_year?: number | string; [key: string]: unknown };
export type Snapshot = { manifest: Manifest; centres: Centre[]; closures: Closure[]; demand_zones: Zone[]; boundaries?: GeoJsonObject };
export type AnalysisParams = { date: string; radius_m: number; senior_weight: number; rescheduled_closure_ids: string[]; planning_areas: string[] };
export type Analysis = {
  date: string; radius_m: number; data_as_of: string; model_version: string; planning_areas?: string[];
  summary: { total_centres: number; closed_centres: number; total_residents: number; total_seniors: number; baseline_covered_residents: number; remaining_covered_residents: number; newly_exposed_residents: number; newly_exposed_seniors: number; affected_zones: number; food_stalls_closed: number };
  centres: AnalysedCentre[]; zones: AnalysedZone[];
  area_ranking: { planning_area: string; residents: number; seniors: number; newly_exposed_residents: number; newly_exposed_seniors: number; coverage_pct: number; centres: number; closed_centres: number; hawker_centres_per_10000?:number; food_centres?:number }[];
  calendar: { date: string; closed_centres: number; food_stalls_closed: number }[];
  limitations: string[]; source_fingerprint: string;
};
export type OptimiseParams = AnalysisParams & { budget: number; site_cost: number; meal_cost: number; meals_per_site: number; max_sites: number; participation_rate: number };
export type Site = { zone_id: string; name: string; planning_area: string; lat: number; lng: number; meals: number; estimated_demand: number; cost: number; covered_zone_ids: string[]; priority_weighted_meals: number };
export type Optimisation = {
  analysis: Analysis; assumptions: OptimiseParams; sites: Site[];
  summary: { budget: number; spent: number; unspent: number; total_meals: number; estimated_demand: number; unmet_demand: number; sites_selected: number; weighted_benefit: number; baseline_weighted_benefit: number; improvement_pct: number; solver_status: string };
  baseline: { name: string; total_meals: number; weighted_benefit: number; spent: number };
  sensitivity: { participation_rate: number; estimated_demand: number; planned_meals: number; matched_meals?: number; potential_surplus_meals?: number; unmet_demand: number }[];
  explanation: string; limitations: string[]; model_version: string; source_fingerprint: string;
};
export type Plan = { id: string; title: string; status: 'draft' | 'reviewed'; created_at: string; updated_at: string; date: string; summary?: Optimisation['summary']; parameters: OptimiseParams; result?: Optimisation; notes?: string };
export type Evidence = { manifest: Manifest; methodology: Record<string, unknown>; evaluation?: Record<string, unknown>; evaluation_status?: 'current'|'stale'|'unavailable' };
