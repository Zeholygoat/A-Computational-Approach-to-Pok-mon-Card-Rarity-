# Research and reproducibility notes

## Parameters carried forward from the supplied script
- Baseline per-pack probability: 0.0117.
- Low scenario: 0.0094.
- High scenario: 0.0140.
- Default Monte Carlo repetitions: 200,000.
- Default random seed: 20261013.
- Illustrative pack price in the original script: USD 9.22.

## Interpretation safeguards
- Low/high values are sensitivity scenarios unless the source establishes a formal interval.
- The study's outcome is category-level, not the odds of one specific card.
- The model assumes independent packs and constant p.
- Simulation estimates are generated data, not observed physical pack outcomes.
- The Monte Carlo interval describes simulation estimation variability, not uncertainty in the empirical pull-rate estimate.
- Price arithmetic does not imply expected return, profitability, or card value.

## Before publication
1. Confirm and cite the original pull-rate source and its sampling methodology.
2. Re-run the tests and regenerate all tables/figures from the final code.
3. Record Python and library versions used for the final results.
4. Preserve the exact parameter values, repetitions, seed and export settings in the manuscript.
