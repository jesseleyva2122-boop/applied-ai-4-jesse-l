# Assignment 7: Measured Results

## Reproduce

From `Act 3/warehouse_rl`:

```bash
python -m pip install -r requirements.txt
python run_assignment7.py
```

The required original entry point remains `python multi_objective_demo.py`. The wrapper calls that unchanged demo with seed 20261029, five episodes per wage, a maximum of 2,000 steps per episode, and all 20 supplied configurations. It saves raw episode data and the demo plot. The checked-in CSV and this table summarize the saved run. `--no-cache` disables equivalent graph-query memoization. The original and cached runs agreed on the first three configurations at the printed precision. A separate full 2,000-step first-episode comparison also matched every recorded reward, info dictionary, employee position, route and assignment exactly (SHA-256 trace `e533458bb952e2bd7ac60d0181a8cc647d51c833d8218c368f43f2f39bac2059`); the cache includes grid contents, positions and traffic state, with copies of paths returned to callers.

The demo and its six core input modules were byte-checked against repository commit `f08bf424770ff5967e3cd770231b74cce2d3ccab`. This experiment uses the demo's `WageStrategyAgent` family; it does not run or change the previous assignment's `skeleton_optimization` policy.

## All 20 measured configurations

| Nominal wage/step | Mean episode profit | Mean final completion | Pareto maximal? |
|---:|---:|---:|:---:|
| $0.15 | $12,034.66 | 31.583% | No |
| $0.20 | $13,455.82 | 34.796% | No |
| $0.25 | $15,878.95 | 40.790% | Yes |
| $0.30 | $13,928.50 | 47.191% | Yes |
| $0.40 | $14,205.20 | 44.812% | Yes |
| $0.50 | $11,064.98 | 49.055% | No |
| $0.60 | $10,557.26 | 52.548% | Yes |
| $0.70 | $13,052.56 | 50.061% | Yes |
| $0.80 | $7,112.88 | 41.385% | No |
| $0.90 | $7,511.11 | 47.265% | No |
| $1.00 | $10,359.39 | 57.340% | Yes |
| $1.20 | $5,856.14 | 51.427% | No |
| $1.40 | $6,058.01 | 57.549% | Yes |
| $1.60 | $953.14 | 50.097% | No |
| $1.80 | $4,107.37 | 65.885% | Yes |
| $2.00 | $420.36 | 62.126% | No |
| $2.50 | $-1,008.82 | 66.128% | No |
| $3.00 | $-1,006.32 | 69.880% | Yes |
| $3.50 | $-1,011.42 | 57.625% | No |
| $4.00 | $-1,015.66 | 48.946% | No |

## Interpretation and limitations

- Both objectives are maximized. A point is dominated only when another configuration has at least as much mean profit and mean final completion, and is strictly better on at least one. Dominance was calculated from unrounded values. All nine nondominated points are named in the two-paragraph reflection.
- Service is `avg_completion_rate`, the mean of the final episode completion ratios. Its denominator includes completed, cancelled and still-outstanding orders. This is different from `avg_service_rate`, which averages periodic samples. Profit is a mean per episode, not a sum across five episodes.
- The $3.00 setting reached profit below -$1,000 in all five episodes, triggering early bankruptcy termination. Its 69.880% completion does not represent a full 2,000-step sustainable operation.
- Recommendation: nominal $0.70 for new hires. Relative to $0.25, mean profit falls by $2,826.39 (17.800%) and completion improves by 9.272 percentage points. This is a business judgment on the sampled frontier, not a statistically proven optimum.
- Wage mapping issue in the supplied code: nominal $0.30 hires at $0.50; nominal $0.50 and $0.60 hire at $0.80. The two initial employees always start at $0.50. Other listed wage settings, including the recommended $0.70, map to their stated new-hire wage.
- The original demo reuses one environment and its order generator across episodes and configurations. It does not supply matched demand streams or fully independent replications. Customer satisfaction and random arrivals can confound wage comparisons. A follow-up should recreate generators and compare configurations across multiple common demand seeds.
- Five episodes per configuration are exploratory. Small frontier differences, particularly $1.00 versus $1.40 service, should not be treated as statistically established. This is the frontier among observed means, not every possible policy or a guaranteed population frontier.
- The printed “sweet spot” chooses profit divided by wage; it is not a Pareto or executive preference calculation. Its $0.15 choice is dominated by $0.25 in these results.
- Employee turnover is not modeled. Any retention benefit from higher wages is an expectation to validate separately, not a simulation finding.

## Submission

The requested two-paragraph reflection is at [`WAREHOUSE_ASSIGNMENT_7.md`](../../../../WAREHOUSE_ASSIGNMENT_7.md). Raw episode records are in [`results.json`](results.json), all configuration means are in [`results.csv`](results.csv), and the completed console output is in [`simulation.log`](simulation.log).
