# Pokémon TCG Rarity Probability Lab

A Streamlit GUI and reproducible Python toolkit based on the supplied research code and the manuscript *Computational Modelling of Pokémon TCG Rarity*.

## Features

- Interactive probability calculator for a chosen number of booster packs.
- Target finder: minimum packs needed for a selected cumulative probability (e.g. 50%, 90%, 95%, 99%).
- Theoretical cumulative probability and probability of no hit.
- Expected number of category-level hits under the binomial model.
- Monte Carlo simulation with a user-controlled repetition count and random seed.
- Simulation-vs-theory comparison across multiple pack counts.
- Low / baseline / high sensitivity analysis.
- Optional pack-price and budget arithmetic.
- CSV downloads for calculations, threshold tables, simulation results, and sensitivity analysis.
- Boundary handling and automated unit tests for the mathematical functions.

## Run the GUI

Use Python 3.10 or newer.

```bash
python -m venv .venv
```

macOS / Linux:
```bash
source .venv/bin/activate
```

Windows:
```powershell
.venv\Scripts\activate
```

Install dependencies and launch:
```bash
python -m pip install -r requirements.txt
streamlit run pokemon_probability_app.py
```

Streamlit will print a local URL (usually `http://localhost:8501`) to open in your browser.

## Run the tests

```bash
pytest -q
```

## Model and manuscript alignment

The starting parameter is `p = 0.0117` (1.17% per booster pack), matching the working baseline in the supplied code. The low/high sensitivity scenarios are `0.0094` and `0.0140`, derived from the supplied code's `1.17% ± 0.23 percentage points` statement.

**Source caution:** the app deliberately labels the low/high values as sensitivity scenarios. Verify the original source's methodology before calling the reported ±0.23 percentage points a formal 95% confidence interval.

For independent packs with constant per-pack hit probability `p`, the core model is:

- `P(at least one hit) = 1 - (1-p)^n`
- `P(no hit) = (1-p)^n`
- `E[number of hits] = n*p`
- Minimum `n` for target `q`: `ceil(log(1-q) / log(1-p))`

The event is a hit from the selected **rarity category**, not a specific named card. Analytical/simulation agreement is an implementation check and does not independently establish the real-world pull rate. The model does not estimate card value or profit.

“Packs” means booster packs, not a preconstructed 60-card deck. Use a probability estimate suitable for the exact product and event being studied.

## Files

- `pokemon_probability_app.py` — Streamlit GUI and visualizations.
- `pokemon_probability_core.py` — reusable mathematical functions and simulation engine.
- `requirements.txt` — Python dependencies.
- `test_probability.py` — automated mathematical boundary and threshold tests (tests the core without launching the GUI).
- `RESEARCH_NOTES.md` — assumptions and reproducibility notes.
