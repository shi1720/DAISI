"""Deterministic geospatial exposure modelling and constrained meal allocation.

No individual welfare inference is made. All distances are great-circle distances from
subzone representative points, and all meal demand is an explicit scenario assumption.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import date, timedelta
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

MODEL_VERSION = "hawkerbridge-1.0.0"
LIMITATIONS = [
    "Exposure means loss of a nearby listed hawker centre, not measured hunger or food insecurity.",
    "Distances are straight-line estimates from subzone representative points, not walking routes or wheelchair access.",
    "The model covers listed hawker centres only. Coffee shops, food courts, home cooking and delivery are outside its coverage.",
    "Census residents are aggregated geographically. The model does not locate or identify individual residents.",
    "Absence of a published closure is not confirmation that a centre or its stalls are operating.",
]


def haversine_matrix(left: list[dict], right: list[dict]) -> np.ndarray:
    """Pairwise metres on a mean-radius earth, accepting empty collections."""
    if not left or not right:
        return np.zeros((len(left), len(right)), dtype=float)
    a = np.radians([[x["lat"], x["lng"]] for x in left])
    b = np.radians([[x["lat"], x["lng"]] for x in right])
    delta = a[:, None, :] - b[None, :, :]
    h = np.sin(delta[:, :, 0] / 2) ** 2
    h += np.cos(a[:, None, 0]) * np.cos(b[None, :, 0]) * np.sin(delta[:, :, 1] / 2) ** 2
    return 6_371_008.8 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def _int(value: Any) -> int:
    return max(0, int(value or 0))


def _money(value: float) -> float:
    return round(float(value), 2)


class PlanningEngine:
    def __init__(self, snapshot: dict):
        self.snapshot = copy.deepcopy(snapshot)
        self.centres = self.snapshot["centres"]
        self.zones = self.snapshot["demand_zones"]
        self.closures = self.snapshot["closures"]
        self.manifest = self.snapshot.get("manifest", {})
        canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
        if not self.centres or not self.zones:
            raise ValueError("A validated centre and demographic snapshot is required")
        self.distances = haversine_matrix(self.zones, self.centres)
        # Three listed facilities in the real feed are markets with no food stalls.
        # Retain the inventory, but do not count them as cooked-food alternatives.
        self.food_indices = [
            i for i, c in enumerate(self.centres) if _int(c.get("food_stalls")) > 0
        ]
        if not self.food_indices:
            raise ValueError("At least one centre with listed food stalls is required")
        self.distances[:, [i for i in range(len(self.centres)) if i not in self.food_indices]] = (
            np.inf
        )
        self.baseline_indices = self.distances.argmin(axis=1)
        self.baseline_distances = self.distances.min(axis=1)
        self.centre_by_id = {c["id"]: c for c in self.centres}
        self.closure_by_id = {c["id"]: c for c in self.closures}

    def _active(self, day: str, rescheduled: set[str]) -> dict[str, list[dict]]:
        result: dict[str, list[dict]] = {}
        for closure in self.closures:
            if closure["id"] in rescheduled:
                continue
            if closure["start_date"] <= day <= closure["end_date"]:
                result.setdefault(closure["centre_id"], []).append(closure)
        return result

    def analyse(self, params: dict) -> dict:
        day = date.fromisoformat(str(params["date"])).isoformat()
        if self.manifest.get("closures_year") and int(day[:4]) != int(
            self.manifest["closures_year"]
        ):
            raise ValueError(
                f"This snapshot covers the {self.manifest['closures_year']} closure schedule"
            )
        radius = float(params.get("radius_m", 800))
        weight = float(params.get("senior_weight", 2))
        scope = set(params.get("planning_areas", []))
        known_areas = {z["planning_area"] for z in self.zones}
        if scope - known_areas:
            raise ValueError("Unknown planning area in scope")
        rescheduled = set(params.get("rescheduled_closure_ids", []))
        if not 200 <= radius <= 3000 or not 1 <= weight <= 5:
            raise ValueError("Radius must be 200–3000 m and senior weight 1–5")
        for identifier in rescheduled:
            if identifier not in self.closure_by_id:
                raise ValueError("Unknown closure in rescheduling scenario")
            if self.closure_by_id[identifier]["kind"] != "cleaning":
                raise ValueError("Only cleaning closures may be moved in a what-if scenario")
        active = self._active(day, rescheduled)
        open_indices = [i for i in self.food_indices if self.centres[i]["id"] not in active]
        if open_indices:
            open_dist = self.distances[:, open_indices]
            current_nearest = np.array(open_indices)[open_dist.argmin(axis=1)]
            current_dist = open_dist.min(axis=1)
        else:
            current_nearest = np.full(len(self.zones), -1)
            current_dist = np.full(len(self.zones), np.inf)
        centres = [
            dict(
                c,
                status="closed" if c["id"] in active else "open",
                food_access_eligible=_int(c.get("food_stalls")) > 0,
                active_closures=active.get(c["id"], []),
            )
            for c in self.centres
        ]
        zones = []
        for i, z in enumerate(self.zones):
            if scope and z["planning_area"] not in scope:
                continue
            baseline = bool(self.baseline_distances[i] <= radius)
            current = bool(current_dist[i] <= radius)
            residents = _int(z["residents"])
            seniors = min(residents, _int(z.get("seniors")))
            exposed = baseline and not current
            zones.append(
                dict(
                    z,
                    residents=residents,
                    seniors=seniors,
                    baseline_distance_m=round(float(self.baseline_distances[i])),
                    current_distance_m=round(float(current_dist[i]))
                    if math.isfinite(current_dist[i])
                    else None,
                    baseline_centre_id=self.centres[self.baseline_indices[i]]["id"],
                    current_centre_id=self.centres[current_nearest[i]]["id"]
                    if current_nearest[i] >= 0
                    else None,
                    baseline_covered=baseline,
                    current_covered=current,
                    newly_exposed=exposed,
                    priority_score=round(residents + (weight - 1) * seniors, 2) if exposed else 0,
                )
            )
        area_map: dict[str, dict] = {}
        for z in zones:
            area = z["planning_area"]
            row = area_map.setdefault(
                area,
                dict(
                    planning_area=area,
                    residents=0,
                    seniors=0,
                    newly_exposed_residents=0,
                    newly_exposed_seniors=0,
                    covered=0,
                    centres=0,
                    food_centres=0,
                    closed_centres=0,
                ),
            )
            row["residents"] += z["residents"]
            row["seniors"] += z["seniors"]
            row["covered"] += z["residents"] if z["current_covered"] else 0
            if z["newly_exposed"]:
                row["newly_exposed_residents"] += z["residents"]
                row["newly_exposed_seniors"] += z["seniors"]
        for centre in centres:
            if centre["planning_area"] in area_map:
                row = area_map[centre["planning_area"]]
                row["centres"] += 1
                row["food_centres"] += int(centre["food_access_eligible"])
                row["closed_centres"] += int(centre["status"] == "closed")
        for row in area_map.values():
            row["coverage_pct"] = (
                round(100 * row.pop("covered") / row["residents"], 1) if row["residents"] else 0
            )
            row["hawker_centres_per_10000"] = (
                round(10000 * row["food_centres"] / row["residents"], 3)
                if row["residents"]
                else None
            )
        calendar = []
        first = date.fromisoformat(day) - timedelta(days=7)
        for offset in range(35):
            d = (first + timedelta(days=offset)).isoformat()
            if self.manifest.get("closures_year") and int(d[:4]) != int(
                self.manifest["closures_year"]
            ):
                continue
            closed = self._active(d, rescheduled)
            if scope:
                closed = {
                    k: v
                    for k, v in closed.items()
                    if self.centre_by_id[k]["planning_area"] in scope
                }
            calendar.append(
                dict(
                    date=d,
                    closed_centres=len(closed),
                    food_stalls_closed=sum(
                        _int(self.centre_by_id[x].get("food_stalls"))
                        for x in closed
                        if x in self.centre_by_id
                    ),
                )
            )
        scope_centres = [c for c in centres if not scope or c["planning_area"] in scope]
        summary = dict(
            total_centres=len(scope_centres),
            closed_centres=sum(c["status"] == "closed" for c in scope_centres),
            food_centres=sum(c["food_access_eligible"] for c in scope_centres),
            total_residents=sum(z["residents"] for z in zones),
            total_seniors=sum(z["seniors"] for z in zones),
            baseline_covered_residents=sum(z["residents"] for z in zones if z["baseline_covered"]),
            remaining_covered_residents=sum(z["residents"] for z in zones if z["current_covered"]),
            newly_exposed_residents=sum(z["residents"] for z in zones if z["newly_exposed"]),
            newly_exposed_seniors=sum(z["seniors"] for z in zones if z["newly_exposed"]),
            affected_zones=sum(1 for z in zones if z["newly_exposed"] and z["residents"] > 0),
            food_stalls_closed=sum(
                _int(c.get("food_stalls")) for c in scope_centres if c["status"] == "closed"
            ),
        )
        limitations = LIMITATIONS + list(self.manifest.get("limitations", []))
        if rescheduled:
            limitations += [
                "Selected cleaning closures are hypothetically moved outside this date. No official schedule has changed; approval and destination-date conflicts must be checked."
            ]
        return dict(
            date=day,
            radius_m=radius,
            planning_areas=sorted(scope),
            data_as_of=self.manifest.get("fetched_at"),
            model_version=MODEL_VERSION,
            summary=summary,
            centres=centres,
            zones=zones,
            area_ranking=sorted(
                area_map.values(),
                key=lambda r: (
                    -r["newly_exposed_seniors"],
                    -r["newly_exposed_residents"],
                    r["planning_area"],
                ),
            ),
            calendar=calendar,
            limitations=list(dict.fromkeys(limitations)),
            source_fingerprint=self.fingerprint,
        )

    def optimise(self, params: dict) -> dict:
        analysis = self.analyse(params)
        budget = float(params.get("budget", 1500))
        site_cost = float(params.get("site_cost", 300))
        meal_cost = float(params.get("meal_cost", 4))
        capacity = int(params.get("meals_per_site", 150))
        max_sites = int(params.get("max_sites", 3))
        uptake = float(params.get("participation_rate", 0.05))
        senior_weight = float(params.get("senior_weight", 2))
        if not 0 <= budget <= 100_000 or not 1 <= site_cost <= 10000 or not 1 <= meal_cost <= 100:
            raise ValueError("Invalid daily cost or budget")
        if not 1 <= capacity <= 5000 or not 0 <= max_sites <= 20 or not 0.001 <= uptake <= 1:
            raise ValueError("Invalid capacity, site limit or participation rate")
        # Use integer cents throughout the constraint so a feasible solver solution cannot overspend through rounding.
        budget_cents, site_cents, meal_cents = (
            round(x * 100) for x in (budget, site_cost, meal_cost)
        )
        affected = [z for z in analysis["zones"] if z["newly_exposed"] and z["residents"] > 0]
        demand = np.array([math.ceil(z["residents"] * uptake) for z in affected], dtype=int)
        weights = np.array(
            [1 + (senior_weight - 1) * z["seniors"] / z["residents"] for z in affected]
        )
        n = len(affected)
        adjacency = haversine_matrix(affected, affected) <= params.get("radius_m", 800)
        edges = list(zip(*np.where(adjacency), strict=True)) if n else []
        baseline_allocation = self._greedy(
            demand, weights, adjacency, budget_cents, site_cents, meal_cents, capacity, max_sites
        )
        chosen = baseline_allocation
        status = (
            "no_exposure"
            if n == 0
            else "insufficient_budget"
            if budget_cents < site_cents + meal_cents or not max_sites
            else "baseline_fallback"
        )
        if n and max_sites and budget_cents >= site_cents + meal_cents:
            # y_j opens locality j; x_ij assigns meals from locality j to demand subzone i.
            # Each person-equivalent appears in a single subzone demand constraint.
            num_vars = n + len(edges)
            c = np.r_[np.full(n, 1e-5), [-weights[i] for i, _ in edges]]
            rows, cols, vals = [], [], []
            # Demand rows [0,n), capacity rows [n,2n), budget 2n, site limit 2n+1.
            for j in range(n):
                rows.extend([n + j, 2 * n, 2 * n + 1])
                cols.extend([j] * 3)
                vals.extend([-capacity, site_cents, 1])
            for k, (i, j) in enumerate(edges, n):
                rows.extend([i, n + j, 2 * n])
                cols.extend([k] * 3)
                vals.extend([1, 1, meal_cents])
            matrix = coo_matrix(
                (np.array(vals, float), (rows, cols)), shape=(2 * n + 2, num_vars)
            ).tocsc()
            upper = np.r_[demand, np.zeros(n), budget_cents, max_sites].astype(float)
            try:
                solved = milp(
                    c,
                    integrality=np.ones(num_vars),
                    bounds=Bounds(
                        np.zeros(num_vars),
                        np.r_[np.ones(n), [min(demand[i], capacity) for i, _ in edges]],
                    ),
                    constraints=LinearConstraint(matrix, np.full(2 * n + 2, -np.inf), upper),
                    options={"time_limit": 5.0, "mip_rel_gap": 0.001},
                )
                if solved.x is not None:
                    vector = np.rint(solved.x).astype(int)
                    variable_upper = np.r_[np.ones(n), [min(demand[i], capacity) for i, _ in edges]]
                    if (
                        np.all(matrix @ vector <= upper + 1e-6)
                        and np.all(vector >= 0)
                        and np.all(vector <= variable_upper)
                    ):
                        allocation = np.zeros((n, n), dtype=int)
                        for k, (i, j) in enumerate(edges, n):
                            allocation[i, j] = vector[k]
                        # Drop unused sites, including degeneracies in a time-limited solution.
                        allocation_score = float(np.sum(allocation.sum(axis=1) * weights))
                        baseline_score = float(np.sum(chosen.sum(axis=1) * weights))
                        if allocation_score >= baseline_score - 1e-6:
                            chosen = allocation
                            status = "optimal" if solved.status == 0 else "feasible_time_limit"
            except (ValueError, RuntimeError):
                # A validated feasible baseline keeps decision support available during solver failures.
                status = "baseline_fallback"
        sites, spent, benefit = self._summarise(
            chosen, affected, demand, weights, site_cents, meal_cents
        )
        _, baseline_spent, baseline_benefit = self._summarise(
            baseline_allocation, affected, demand, weights, site_cents, meal_cents
        )
        meals = int(chosen.sum())
        total_demand = int(demand.sum())
        assumptions = dict(
            budget=budget,
            site_cost=site_cost,
            meal_cost=meal_cost,
            meals_per_site=capacity,
            max_sites=max_sites,
            participation_rate=uptake,
            senior_weight=senior_weight,
            radius_m=params.get("radius_m", 800),
            currency="SGD",
            period="one day",
            candidate_sites="Unverified subzone representative points",
        )
        sensitivity = []
        assigned_per_zone = chosen.sum(axis=1) if n else np.zeros(0)
        for p in sorted(set([max(0.001, uptake / 2), uptake, min(1, uptake * 2)])):
            ds = np.array([math.ceil(z["residents"] * p) for z in affected])
            fulfilled = int(np.minimum(ds, assigned_per_zone).sum())
            sensitivity.append(
                dict(
                    participation_rate=round(p, 4),
                    estimated_demand=int(ds.sum()),
                    planned_meals=meals,
                    matched_meals=fulfilled,
                    unmet_demand=max(0, int(ds.sum()) - fulfilled),
                    potential_surplus_meals=max(0, meals - fulfilled),
                )
            )
        return dict(
            analysis=analysis,
            assumptions=assumptions,
            sites=sites,
            summary=dict(
                budget=budget,
                spent=spent,
                unspent=_money(budget - spent),
                total_meals=meals,
                estimated_demand=total_demand,
                unmet_demand=max(0, total_demand - meals),
                sites_selected=len(sites),
                weighted_benefit=round(benefit, 3),
                baseline_weighted_benefit=round(baseline_benefit, 3),
                improvement_pct=round(100 * (benefit - baseline_benefit) / baseline_benefit, 1)
                if baseline_benefit
                else 0,
                solver_status=status,
            ),
            baseline=dict(
                name="Largest demand first",
                total_meals=int(baseline_allocation.sum()),
                weighted_benefit=round(baseline_benefit, 3),
                spent=baseline_spent,
            ),
            sensitivity=sensitivity,
            explanation=(
                f"For {analysis['date']}, {len(affected)} subzones lose a listed hawker centre within "
                f"{int(params.get('radius_m', 800))} m under this model. Assuming {uptake:.1%} participation, "
                f"the scenario requires {total_demand:,} meals. This plan allocates {meals:,} meals across "
                f"{len(sites)} proposed collection localities for S${spent:,.2f} per day. "
                "Meal allocations favour areas with a higher senior share, subject to the chosen budget, site capacity and reach. "
                "A coordinator must verify real demand, a suitable venue, accessible routes and operator capacity before acting."
            ),
            limitations=analysis["limitations"]
            + [
                "Meal uptake, daily setup cost, per-meal cost and site capacity are editable assumptions, not measured or quoted values.",
                "Collection localities are candidate geographic points, not confirmed available premises. No provider or venue has agreed to deliver this plan.",
                "Senior weighting is a policy preference applied to aggregate demographics, not an estimate of individual vulnerability.",
                "Sensitivity holds allocations fixed. Potential surplus is a meal-count scenario, not an estimate of measured food waste.",
            ],
            model_version=MODEL_VERSION,
            source_fingerprint=self.fingerprint,
        )

    @staticmethod
    def _greedy(demand, weights, adjacency, budget, site_cost, meal_cost, capacity, max_sites):
        n = len(demand)
        alloc = np.zeros((n, n), dtype=int)
        remaining = demand.copy()
        opened: set[int] = set()
        for _ in range(min(max_sites, n)):
            if budget < site_cost + meal_cost:
                break
            candidates = [
                (int(remaining[adjacency[:, j]].sum()), j) for j in range(n) if j not in opened
            ]
            if not candidates:
                break
            volume, j = max(candidates, key=lambda pair: (pair[0], -pair[1]))
            if volume == 0:
                break
            cap = min(capacity, (budget - site_cost) // meal_cost)
            budget -= site_cost
            opened.add(j)
            # Largest remaining subzone first is the deliberately simple operational baseline.
            for i in sorted(np.where(adjacency[:, j])[0], key=lambda i: (-remaining[i], i)):
                take = min(int(remaining[i]), cap)
                alloc[i, j] = take
                remaining[i] -= take
                cap -= take
                budget -= take * meal_cost
                if cap == 0:
                    break
        return alloc

    @staticmethod
    def _summarise(allocation, zones, demand, weights, site_cost, meal_cost):
        sites = []
        for j in range(len(zones)):
            meals = int(allocation[:, j].sum())
            if meals == 0:
                continue
            z = zones[j]
            receiving = np.where(allocation[:, j] > 0)[0]
            sites.append(
                dict(
                    zone_id=z["id"],
                    name=z["name"],
                    planning_area=z["planning_area"],
                    lat=z["lat"],
                    lng=z["lng"],
                    meals=meals,
                    estimated_demand=int(sum(demand[i] for i in receiving)),
                    cost=(site_cost + meals * meal_cost) / 100,
                    covered_zone_ids=[zones[i]["id"] for i in receiving],
                    allocations=[
                        dict(zone_id=zones[i]["id"], meals=int(allocation[i, j])) for i in receiving
                    ],
                    priority_weighted_meals=round(float(np.sum(allocation[:, j] * weights)), 3),
                )
            )
        spent = sum(s["cost"] for s in sites)
        benefit = float(np.sum(allocation.sum(axis=1) * weights)) if len(zones) else 0
        return sites, _money(spent), benefit
