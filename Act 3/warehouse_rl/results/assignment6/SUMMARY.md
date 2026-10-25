# Assignment 6 Benchmark Results
Jesse Leyva | October 25, 2026

## Before and after

Each policy ran 10 fresh 3,000-step episodes, seeds 9100–9109. Rank is against the same seven supplied heuristics, replacing the previous student policy with the final one. Both rank first, but the profit margin increases substantially.

| Student policy | Placement | Mean profit per episode | Total profit across 10 episodes | 95% CI for mean profit | Mean completion rate |
| --- | --- | ---: | ---: | --- | ---: |
| Previous layout policy | 1 / 8 | $21,922.18 | $219,221.78 | $21,020.08 to $22,824.27 | 40.06% |
| Final integrated policy | 1 / 8 | $45,084.78 | $450,847.80 | $44,171.36 to $45,998.20 | 70.41% |

Mean profit increases by $23,162.60, or 105.66%. The paired 95% CI for the mean gain is $22,236.67 to $24,088.54.

## Full comparison

This table includes both student versions for audit, so it has nine policies. Each policy uses fresh environments to prevent flags, hooks, or order-generator state leaking between policies.

| Rank | Policy | Mean profit | Total profit | 95% CI for mean |
| ---: | --- | ---: | ---: | --- |
| 1 | skeleton_optimization | $45,084.78 | $450,847.80 | $44,171.36 to $45,998.20 |
| 2 | previous_layout | $21,922.18 | $219,221.78 | $21,020.08 to $22,824.27 |
| 3 | aggressive_swap | $20,590.92 | $205,909.25 | $19,735.07 to $21,446.78 |
| 4 | fixed_std | $20,472.74 | $204,727.43 | $19,605.23 to $21,340.25 |
| 5 | intelligent_queue | $18,948.89 | $189,488.95 | $16,330.60 to $21,567.19 |
| 6 | random_std | $12,945.88 | $129,458.79 | $7,224.87 to $18,666.89 |
| 7 | intelligent_hiring | $2,567.73 | $25,677.31 | $-281.33 to $5,416.79 |
| 8 | greedy_std | $1,205.22 | $12,052.16 | $199.88 to $2,210.55 |
| 9 | distance_based | $1,199.92 | $11,999.24 | $-455.89 to $2,855.74 |

## Ablations

All ablations retain the previous layout optimizer. Staffing-only uses the final staffing policy with the original automatic pickup allocator. Routing-only uses the new matcher with the previous five-worker staffing policy.

| Policy | Mean profit | 95% CI for mean |
| --- | ---: | --- |
| Previous | $21,922.18 | $21,020.08 to $22,824.27 |
| Staffing only | $44,101.96 | $42,518.47 to $45,685.45 |
| Routing only | $21,627.51 | $20,605.60 to $22,649.41 |
| Integrated | $45,084.78 | $44,171.36 to $45,998.20 |

The integrated policy averages $982.82 more than staffing-only, but the paired 95% CI is $-616.67 to $2,582.30. This interval includes zero: these ten seeds do not establish a reliable incremental routing gain. Most demonstrated improvement comes from staffing. Routing-only is slightly below the previous policy on this sample.

## Iterative development

Development used seeds 8100–8102. Earlier failed variants are retained rather than hidden. These exploratory intervals are not treated as confirmatory evidence.

| Stage | Observation and refinement |
| --- | --- |
| Initial action-only matching | Identical routing ablation revealed automatic allocation bypassed the new method. Added optional intra-step hook. |
| Value divided by time | Favored quick jobs too strongly and reduced profit. Replaced with value minus estimated time cost. |
| Rejecting negative predicted margins | Some variants idled until bankruptcy. Existing wages accrue while idle, so allow all reachable matches. |
| First 20 queue entries | Missed valuable orders beyond the action window. Intra-step hook now uses full current queue with a 40-order shortlist. |
| Wage and capacity trials | Medium-wage hires and a 12-worker cap improved development means; final code was fixed before seeds 9100–9109. |

## Statistical and execution notes

- All 110 final/ablation episodes executed. Some supplied heuristics hit the simulator bankruptcy cutoff; those outcomes remain in the data. The final student policy completed all ten 3,000-step episodes.
- CIs use t(0.975, n−1) × sample standard deviation / sqrt(n). Total profit is the sum across ten episodes; CI endpoints describe the mean, not the total or a single future run.
- Demand responds to completion, satisfaction, headcount and backlog. Common seeds are reproducible initial conditions, not identical realized order streams. Completion percentages therefore have different denominators across policies.
- Profit includes the simulator collision penalty as well as wages and delivered-order revenue. No reward coefficients, wage formulas, demand logic, or collision rules were changed.
- The legacy serial CLI was interrupted after partial progress; that partial output is excluded. The completed seeded comparison is the initial/final evidence used here.
- The Pygame aggressive_swap demonstration completed with a dummy display and Agg plotting backend. This checks renderer execution in a headless environment, not a claim of desktop interaction.
- 23 unit/integration tests passed. Test output is in tests.txt; benchmark CLI output is in final_cli.txt. Baseline NumPy empty-slice warnings are inherited from the supplied heuristic code and do not interrupt the completed benchmark.
