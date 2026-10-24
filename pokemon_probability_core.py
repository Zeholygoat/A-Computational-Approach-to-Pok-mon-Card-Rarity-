"""
Reusable mathematical core for the Pokémon TCG rarity probability toolkit.
Functions are deliberately independent of the GUI so they can be tested.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

BASELINE_P = 0.0117
LOW_P = 0.0094
HIGH_P = 0.0140
DEFAULT_PACK_PRICE = 9.22
DEFAULT_SEED = 20261013
DEFAULT_SIMULATIONS = 200_000

# ---------------------------------------------------------------------------
# Core mathematical functions — separated from the GUI for testability.
# ---------------------------------------------------------------------------

def validate_probability(p: float, name: str = "p") -> float:
    """Return p as float after enforcing the probability domain [0, 1]."""
    p = float(p)
    if not math.isfinite(p) or p < 0.0 or p > 1.0:
        raise ValueError(f"{name} must be a finite probability between 0 and 1.")
    return p


def validate_pack_count(n: int) -> int:
    """Validate a non-negative integer number of booster packs."""
    if isinstance(n, bool) or int(n) != n or n < 0:
        raise ValueError("Pack count must be a non-negative integer.")
    return int(n)


def probability_at_least_one(n: int, p: float) -> float:
    """
    P(X >= 1) = 1 - (1-p)^n, for independent packs.

    log1p/expm1 improve numerical stability when p is very small.
    Boundary cases are handled explicitly.
    """
    n = validate_pack_count(n)
    p = validate_probability(p)
    if n == 0 or p == 0:
        return 0.0
    if p == 1:
        return 1.0
    return float(-math.expm1(n * math.log1p(-p)))


def probability_none(n: int, p: float) -> float:
    """P(X = 0) = (1-p)^n."""
    return 1.0 - probability_at_least_one(n, p)


def expected_hits(n: int, p: float) -> float:
    """Expected number of category-level hits over n independent packs."""
    n = validate_pack_count(n)
    p = validate_probability(p)
    return n * p


def packs_for_target(target_probability: float, p: float) -> int | None:
    """
    Smallest integer n such that P(at least one hit) >= target_probability.
    Returns None when a positive target is impossible at p=0.
    """
    q = validate_probability(target_probability, "target_probability")
    p = validate_probability(p)
    if q == 0:
        return 0
    if p == 0:
        return None
    if p == 1:
        return 1
    if q == 1:
        return None  # finite packs cannot guarantee a hit when p < 1
    # log(1-q) / log(1-p); use log1p for precision.
    raw = math.log1p(-q) / math.log1p(-p)
    n = max(0, math.ceil(raw - 1e-12))
    # Guard against floating point edge cases around exact integer thresholds.
    while probability_at_least_one(n, p) + 1e-14 < q:
        n += 1
    while n > 0 and probability_at_least_one(n - 1, p) + 1e-14 >= q:
        n -= 1
    return n


def probability_curve(max_packs: int, p: float) -> pd.DataFrame:
    """Create a theoretical cumulative probability table from 0..max_packs."""
    max_packs = validate_pack_count(max_packs)
    p = validate_probability(p)
    counts = np.arange(max_packs + 1, dtype=int)
    if p == 0:
        probs = np.zeros(len(counts))
    elif p == 1:
        probs = (counts >= 1).astype(float)
    else:
        probs = -np.expm1(counts * np.log1p(-p))
    return pd.DataFrame({
        "packs": counts,
        "probability_at_least_one": probs,
        "probability_none": 1.0 - probs,
        "expected_hits": counts * p,
    })


def threshold_table(p: float, targets: Iterable[float] = (0.50, 0.75, 0.80, 0.90, 0.95, 0.99, 0.999)) -> pd.DataFrame:
    """Return minimum pack counts and achieved probabilities for target levels."""
    p = validate_probability(p)
    rows = []
    for q in targets:
        n = packs_for_target(float(q), p)
        rows.append({
            "target_probability": float(q),
            "minimum_packs": n,
            "achieved_probability": None if n is None else probability_at_least_one(n, p),
            "probability_none_at_threshold": None if n is None else probability_none(n, p),
        })
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class SimulationResult:
    pack_count: int
    probability: float
    repetitions: int
    seed: int
    simulated_probability: float
    theoretical_probability: float
    simulation_standard_error: float
    simulation_ci_low: float
    simulation_ci_high: float


def simulate_at_least_one(
    n: int, p: float, repetitions: int = DEFAULT_SIMULATIONS, seed: int = DEFAULT_SEED
) -> SimulationResult:
    """
    Simulate repeated openings of n packs and estimate the share with >=1 hit.
    Each repetition is one independent experiment consisting of n packs.
    The reported interval is an approximate 95% interval for Monte Carlo
    estimation error only—not uncertainty in the real-world pull rate.
    """
    n = validate_pack_count(n)
    p = validate_probability(p)
    repetitions = int(repetitions)
    if repetitions < 1:
        raise ValueError("Simulation repetitions must be at least 1.")
    if repetitions > 5_000_000:
        raise ValueError("Use 5,000,000 repetitions or fewer in one run.")
    if seed < 0:
        raise ValueError("Random seed must be non-negative.")

    rng = np.random.default_rng(int(seed))
    observed = float((rng.binomial(n, p, size=repetitions) >= 1).mean())
    theory = probability_at_least_one(n, p)
    se = math.sqrt(theory * (1.0 - theory) / repetitions)
    return SimulationResult(
        pack_count=n,
        probability=p,
        repetitions=repetitions,
        seed=int(seed),
        simulated_probability=observed,
        theoretical_probability=theory,
        simulation_standard_error=se,
        simulation_ci_low=max(0.0, observed - 1.96 * se),
        simulation_ci_high=min(1.0, observed + 1.96 * se),
    )


def run_simulation_grid(
    pack_counts: Iterable[int], p: float, repetitions: int, seed: int
) -> pd.DataFrame:
    """Simulate a reproducible grid of pack counts using deterministic seed offsets."""
    rows = []
    for i, n in enumerate(pack_counts):
        result = simulate_at_least_one(int(n), p, repetitions, seed + i)
        rows.append({
            "packs": result.pack_count,
            "per_pack_probability": result.probability,
            "repetitions": result.repetitions,
            "seed": result.seed,
            "theoretical_probability": result.theoretical_probability,
            "simulated_probability": result.simulated_probability,
            "simulation_standard_error": result.simulation_standard_error,
            "simulation_95pct_low": result.simulation_ci_low,
            "simulation_95pct_high": result.simulation_ci_high,
            "absolute_difference": abs(
                result.simulated_probability - result.theoretical_probability
            ),
        })
    return pd.DataFrame(rows)


def cost_summary(pack_count: int, unit_price: float, budget: float) -> dict:
    """Basic expenditure arithmetic; does not estimate resale value or profit."""
    pack_count = validate_pack_count(pack_count)
    unit_price = float(unit_price)
    budget = float(budget)
    if not math.isfinite(unit_price) or unit_price < 0:
        raise ValueError("Unit price must be finite and non-negative.")
    if not math.isfinite(budget) or budget < 0:
        raise ValueError("Budget must be finite and non-negative.")
    affordable = math.inf if unit_price == 0 else math.floor(budget / unit_price)
    return {
        "pack_count": pack_count,
        "unit_price": unit_price,
        "total_cost": pack_count * unit_price,
        "budget": budget,
        "affordable_packs": affordable,
        "budget_probability": None if affordable is math.inf else probability_at_least_one(affordable, BASELINE_P),
    }


