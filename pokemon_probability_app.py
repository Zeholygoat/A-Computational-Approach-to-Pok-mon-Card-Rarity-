"""
Pokémon TCG rarity probability explorer
=======================================
Research-aligned Streamlit GUI for the manuscript:
"Computational Modelling of Pokémon TCG Rarity".

Baseline scenario: p = 0.0117 (1.17%) per booster pack, matching the
working parameter in the supplied research code. The 0.0094 and 0.0140
values are shown as low/high sensitivity scenarios derived from the
reported +/- 0.23 percentage-point range. Do not call these confidence
bounds unless the original source's methodology supports that interpretation.

IMPORTANT MODEL SCOPE
- The modeled event is at least one hit from a selected rarity category.
- It is not an individual-card probability and does not model card values.
- It assumes independent packs with a constant per-pack probability p.
- Simulation validates implementation under the model; it does not validate
  whether the source-derived p is representative of real-world pack outcomes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

APP_TITLE = "Pokémon TCG · Rarity Probability Lab"
BASELINE_P = 0.0117
LOW_P = 0.0094
HIGH_P = 0.0140
DEFAULT_PACK_PRICE = 9.22  # illustrative USD value from the original script
DEFAULT_SEED = 20261013
DEFAULT_SIMULATIONS = 200_000


# Mathematical model is maintained separately for testing and reuse.
from pokemon_probability_core import (
    BASELINE_P, LOW_P, HIGH_P, DEFAULT_PACK_PRICE, DEFAULT_SEED,
    DEFAULT_SIMULATIONS, probability_at_least_one, probability_none,
    expected_hits, packs_for_target, probability_curve, threshold_table,
    simulate_at_least_one, run_simulation_grid, cost_summary,
)


# ---------------------------------------------------------------------------
# Streamlit user interface.
# ---------------------------------------------------------------------------

st.set_page_config(page_title=APP_TITLE, page_icon="🃏", layout="wide")
st.title(APP_TITLE)
st.caption("A reproducible probability calculator, sensitivity explorer, and Monte Carlo validation GUI.")

with st.sidebar:
    st.header("Model settings")
    scenario = st.selectbox(
        "Starting probability scenario",
        ["Research baseline (1.17%)", "Low sensitivity (0.94%)", "High sensitivity (1.40%)", "Custom probability"],
        help="Low/high values are sensitivity scenarios from the original code, not verified confidence limits.",
    )
    if scenario.startswith("Research"):
        selected_p = BASELINE_P
    elif scenario.startswith("Low"):
        selected_p = LOW_P
    elif scenario.startswith("High"):
        selected_p = HIGH_P
    else:
        selected_p = st.number_input(
            "Per-pack hit probability (%)", min_value=0.0, max_value=100.0,
            value=BASELINE_P * 100, step=0.01, format="%.4f"
        ) / 100.0
    st.metric("Selected per-pack probability", f"{selected_p:.4%}")
    st.divider()
    st.caption("Research assumptions")
    st.markdown(
        "- Independent booster packs\n"
        "- Constant per-pack probability\n"
        "- Category-level hit, not a named individual card\n"
        "- Simulation is model-based, not observed pack data"
    )

tab_overview, tab_explorer, tab_targets, tab_sim, tab_sensitivity, tab_budget, tab_method = st.tabs([
    "Overview", "Probability explorer", "Target finder", "Monte Carlo", "Sensitivity", "Budget & cost", "Methods"
])

with tab_overview:
    st.subheader("At-a-glance result")
    left, middle, right, fourth = st.columns(4)
    default_n = 100
    q100 = probability_at_least_one(default_n, selected_p)
    left.metric("P(at least one) · 100 packs", f"{q100:.2%}")
    middle.metric("P(no hit) · 100 packs", f"{probability_none(default_n, selected_p):.2%}")
    target_95 = packs_for_target(0.95, selected_p)
    right.metric("Packs for ≥95% modelled chance", "Not possible" if target_95 is None else f"{target_95:,}")
    fourth.metric("Expected hits · 100 packs", f"{expected_hits(default_n, selected_p):.2f}")

    curve_max = st.slider("Maximum pack count for overview curve", 50, 1000, 400, 25)
    curve = probability_curve(curve_max, selected_p)
    fig = px.line(curve, x="packs", y="probability_at_least_one",
                  labels={"packs": "Booster packs opened", "probability_at_least_one": "Probability of ≥1 category-level hit"},
                  title="Cumulative probability under the selected per-pack assumption")
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    st.info("A higher cumulative probability does not guarantee a hit. Each pack is modelled as a separate independent attempt.")

with tab_explorer:
    st.subheader("How many packs are you considering?")
    c1, c2 = st.columns(2)
    with c1:
        pack_count = st.number_input("Number of booster packs", min_value=0, max_value=1_000_000, value=100, step=1)
    with c2:
        explorer_p_pct = st.number_input("Per-pack probability (%)", min_value=0.0, max_value=100.0,
                                         value=selected_p * 100, step=0.01, format="%.4f")
    explorer_p = explorer_p_pct / 100
    n = int(pack_count)
    p_at_least = probability_at_least_one(n, explorer_p)
    p_none = probability_none(n, explorer_p)
    a, b, c, d = st.columns(4)
    a.metric("At least one hit", f"{p_at_least:.4%}")
    b.metric("No hits", f"{p_none:.4%}")
    c.metric("Expected category hits", f"{expected_hits(n, explorer_p):.4f}")
    d.metric("Minimum packs for ≥50%", "Not possible" if packs_for_target(.5, explorer_p) is None else f"{packs_for_target(.5, explorer_p):,}")
    st.markdown("**Interpretation:** this is the modelled chance of one or more hits from the selected rarity category across the entered number of packs.")
    if n <= 5000:
        single = probability_curve(n, explorer_p)
        st.plotly_chart(px.line(single, x="packs", y="probability_at_least_one",
                                labels={"packs": "Packs opened", "probability_at_least_one": "P(≥1 hit)"},
                                title="Probability as packs accumulate").update_yaxes(tickformat=".0%"),
                        use_container_width=True)
    else:
        st.caption("Curve hidden for very large pack counts to keep the interface responsive.")
    detail = pd.DataFrame([{
        "packs": n, "per_pack_probability": explorer_p,
        "probability_at_least_one": p_at_least, "probability_none": p_none,
        "expected_hits": expected_hits(n, explorer_p)
    }])
    st.download_button("Download this calculation (CSV)", detail.to_csv(index=False).encode("utf-8"),
                       file_name="pokemon_probability_calculation.csv", mime="text/csv")

with tab_targets:
    st.subheader("Find the minimum pack count for a target probability")
    t1, t2 = st.columns(2)
    with t1:
        target_pct = st.slider("Desired chance of at least one hit (%)", min_value=1, max_value=99, value=95)
    with t2:
        target_p_pct = st.number_input("Per-pack probability for target finder (%)", min_value=0.0, max_value=100.0,
                                       value=selected_p * 100, step=0.01, format="%.4f")
    target_p = target_p_pct / 100
    target = target_pct / 100
    required = packs_for_target(target, target_p)
    if required is None:
        st.warning("At a 0% per-pack probability, no finite number of packs can achieve a positive target.")
    else:
        achieved = probability_at_least_one(required, target_p)
        previous = probability_at_least_one(max(0, required - 1), target_p)
        x, y, z = st.columns(3)
        x.metric("Minimum packs", f"{required:,}")
        y.metric("Probability at that count", f"{achieved:.4%}")
        z.metric("Probability one pack fewer", f"{previous:.4%}")
        st.caption("The minimum is checked against the analytical formula, including an adjacent-pack check.")
    targets_df = threshold_table(target_p)
    targets_df["target_probability"] = targets_df["target_probability"].map(lambda x: f"{x:.1%}")
    for col in ["achieved_probability", "probability_none_at_threshold"]:
        targets_df[col] = targets_df[col].map(lambda x: "N/A" if pd.isna(x) else f"{x:.4%}")
    st.markdown("**Common probability thresholds**")
    st.dataframe(targets_df, use_container_width=True, hide_index=True)
    st.download_button("Download threshold table (CSV)", threshold_table(target_p).to_csv(index=False).encode("utf-8"),
                       file_name="pokemon_target_thresholds.csv", mime="text/csv")

with tab_sim:
    st.subheader("Monte Carlo verification")
    st.write("Each simulated trial represents opening the selected number of independent packs and recording whether at least one category hit occurred.")
    s1, s2, s3 = st.columns(3)
    with s1:
        sim_pack_count = st.number_input("Packs per simulated trial", min_value=0, max_value=100_000, value=100, step=1)
    with s2:
        sim_runs = st.select_slider("Number of simulation repetitions", options=[1_000, 5_000, 10_000, 50_000, 100_000, 200_000, 500_000, 1_000_000], value=200_000)
    with s3:
        sim_seed = st.number_input("Random seed", min_value=0, max_value=2_147_483_647, value=DEFAULT_SEED, step=1)
    sim_p_pct = st.number_input("Simulation per-pack probability (%)", min_value=0.0, max_value=100.0,
                                value=selected_p * 100, step=0.01, format="%.4f")
    if st.button("Run Monte Carlo simulation", type="primary"):
        result = simulate_at_least_one(int(sim_pack_count), sim_p_pct / 100, int(sim_runs), int(sim_seed))
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Theoretical probability", f"{result.theoretical_probability:.4%}")
        m2.metric("Monte Carlo estimate", f"{result.simulated_probability:.4%}")
        m3.metric("Absolute difference", f"{abs(result.simulated_probability-result.theoretical_probability):.4%}")
        m4.metric("MC standard error", f"{result.simulation_standard_error:.4%}")
        st.write(f"Approximate 95% Monte Carlo error interval: **{result.simulation_ci_low:.4%} to {result.simulation_ci_high:.4%}**.")
        st.caption("This interval describes finite simulation variability around the simulated estimate. It does not represent uncertainty in the real-world pull-rate parameter.")
        sim_df = pd.DataFrame([result.__dict__])
        st.dataframe(sim_df, use_container_width=True)
        st.download_button("Download simulation result (CSV)", sim_df.to_csv(index=False).encode("utf-8"),
                           file_name="pokemon_monte_carlo_result.csv", mime="text/csv")
    st.markdown("#### Compare multiple pack counts")
    grid_text = st.text_input("Pack counts separated by commas", "10, 25, 50, 100, 196, 255, 392")
    grid_runs = st.select_slider("Repetitions per pack count", options=[1_000, 5_000, 10_000, 50_000, 100_000, 200_000], value=50_000, key="grid_runs")
    if st.button("Run comparison grid"):
        try:
            counts = sorted(set(int(x.strip()) for x in grid_text.split(",") if x.strip()))
            if not counts or any(x < 0 for x in counts):
                raise ValueError("Enter one or more non-negative integer pack counts.")
            grid = run_simulation_grid(counts, sim_p_pct / 100, int(grid_runs), int(sim_seed))
            st.dataframe(grid, use_container_width=True, hide_index=True)
            st.plotly_chart(px.scatter(grid, x="packs", y="simulated_probability",
                                       error_y=1.96 * grid["simulation_standard_error"],
                                       labels={"packs": "Packs per trial", "simulated_probability": "Simulated P(≥1 hit)"},
                                       title="Monte Carlo estimates by pack count"),
                            use_container_width=True)
            st.download_button("Download simulation grid (CSV)", grid.to_csv(index=False).encode("utf-8"),
                               file_name="pokemon_monte_carlo_grid.csv", mime="text/csv")
        except Exception as exc:
            st.error(str(exc))

with tab_sensitivity:
    st.subheader("Sensitivity to the assumed per-pack probability")
    st.write("The original script uses 0.94%, 1.17%, and 1.40% as low, baseline, and high scenarios.")
    sens_max = st.slider("Maximum packs in sensitivity chart", 25, 1000, 400, 25, key="sens_max")
    sens_counts = st.multiselect("Pack counts for the comparison table", [10, 25, 50, 59, 86, 100, 150, 196, 255, 300, 392, 500, 750, 1000],
                                 default=[50, 100, 196, 255, 392])
    scenario_map = {"Low sensitivity (0.94%)": LOW_P, "Baseline (1.17%)": BASELINE_P, "High sensitivity (1.40%)": HIGH_P}
    frames = []
    for label, prob in scenario_map.items():
        frame = probability_curve(sens_max, prob)
        frame["scenario"] = label
        frames.append(frame)
    sens = pd.concat(frames, ignore_index=True)
    fig = px.line(sens, x="packs", y="probability_at_least_one", color="scenario",
                  labels={"packs": "Packs opened", "probability_at_least_one": "P(≥1 category hit)", "scenario": "Scenario"},
                  title="How the assumed per-pack rate changes cumulative probability")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    rows = []
    for count in sens_counts:
        row = {"packs": count}
        for label, prob in scenario_map.items():
            row[label] = probability_at_least_one(count, prob)
        rows.append(row)
    sens_table = pd.DataFrame(rows)
    st.dataframe(sens_table.style.format({c: "{:.4%}" for c in sens_table.columns if c != "packs"}),
                 use_container_width=True, hide_index=True)
    st.download_button("Download sensitivity table (CSV)", sens_table.to_csv(index=False).encode("utf-8"),
                       file_name="pokemon_sensitivity_analysis.csv", mime="text/csv")
    st.warning("The low/high values are scenario inputs derived from the supplied script's reported ±0.23 percentage-point figure. Confirm the source's statistical meaning before describing them as a formal confidence interval.")

with tab_budget:
    st.subheader("Optional spending arithmetic")
    st.write("This estimates expenditure only. It does not estimate card resale value, expected profit, or whether opening packs is financially worthwhile.")
    b1, b2, b3 = st.columns(3)
    with b1:
        budget_packs = st.number_input("Packs to price", min_value=0, max_value=1_000_000, value=100, step=1)
    with b2:
        unit_price = st.number_input("Price per pack (USD, illustrative default)", min_value=0.0, max_value=1_000_000.0,
                                     value=DEFAULT_PACK_PRICE, step=0.25, format="%.2f")
    with b3:
        budget = st.number_input("Budget (USD)", min_value=0.0, max_value=100_000_000.0, value=100.0, step=5.0, format="%.2f")
    cost = cost_summary(int(budget_packs), unit_price, budget)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total cost", f"${cost['total_cost']:,.2f}")
    c2.metric("Packs within budget", "Unlimited at $0" if unit_price == 0 else f"{cost['affordable_packs']:,}")
    if unit_price == 0:
        budget_prob = probability_at_least_one(1_000_000, selected_p)
        c3.metric("Modelled chance", f"{probability_at_least_one(int(budget_packs), selected_p):.2%}")
    else:
        c3.metric("Chance within budget (selected p)", f"{probability_at_least_one(int(cost['affordable_packs']), selected_p):.2%}")
    st.caption("The original $9.22 price is illustrative and may not reflect current prices, region, product, taxes, or shipping.")

with tab_method:
    st.subheader("Equations and assumptions")
    st.latex(r"q(n,p)=P(X\\geq 1)=1-(1-p)^n")
    st.latex(r"P(X=0)=(1-p)^n")
    st.latex(r"E[X]=np")
    st.latex(r"n_q=\\left\\lceil\\frac{\\log(1-q)}{\\log(1-p)}\\right\\rceil")
    st.markdown("""
**Definitions**
- `n`: number of booster packs opened.
- `p`: assumed probability of a hit from the selected rarity category in one pack.
- `q(n,p)`: cumulative probability of at least one category-level hit.
- `X`: number of category-level hits across `n` packs under a binomial model.

**Research-aligned limitations**
1. The supplied manuscript uses a working estimate of `p = 0.0117` (1.17%) for Temporal Forces Special Illustration Rare pulls.
2. The 0.94% and 1.40% values are sensitivity scenarios derived from the original code's reported ±0.23 percentage-point figure. Verify the underlying source before calling this a formal 95% confidence interval.
3. Analytical and simulated results share the same assumed `p`. Agreement verifies implementation behaviour; it does not prove the real-world pull rate is accurate.
4. Results apply to a category-level event, not a particular named Pokémon card.
5. The model assumes independent packs and a constant per-pack probability. It does not model product collation, weighing, mapping, card values, or financial returns.
6. “Packs” means booster packs, not a preconstructed 60-card deck. To adapt the model to another product, supply an evidence-based probability appropriate to that product.
""")
    st.subheader("Reproducibility record")
    st.code(
        f"Python: 3.10+\n"
        f"Baseline p: {BASELINE_P}\nLow scenario p: {LOW_P}\nHigh scenario p: {HIGH_P}\n"
        f"Default Monte Carlo repetitions: {DEFAULT_SIMULATIONS:,}\nDefault random seed: {DEFAULT_SEED}\n"
        f"NumPy RNG: numpy.random.default_rng (PCG64 in current NumPy versions)",
        language="text"
    )
    st.download_button("Download core model source", open(__file__, "rb").read(),
                       file_name="pokemon_probability_app.py", mime="text/x-python")
