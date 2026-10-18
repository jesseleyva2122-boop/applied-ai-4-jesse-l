# Held-out benchmark results

Ten episodes per policy, seeds 7200–7209; 3,000 steps maximum per episode.

| Policy | Mean profit | Total profit | 95% t CI for mean | Full episodes |
|---|---:|---:|---:|---:|
| skeleton_optimization | $21,477.66 | $214,776.57 | [$20,618.55, $22,336.77] | 10/10 |
| intelligent_queue | $21,168.04 | $211,680.38 | [$18,894.42, $23,441.65] | 10/10 |
| no_layout | $21,081.98 | $210,819.84 | [$20,415.43, $21,748.54] | 10/10 |
| fixed_std | $20,873.70 | $208,737.03 | [$19,865.28, $21,882.12] | 10/10 |
| aggressive_swap | $20,855.15 | $208,551.46 | [$20,030.29, $21,680.00] | 10/10 |
| random_std | $12,301.46 | $123,014.57 | [$6,028.41, $18,574.51] | 10/10 |
| greedy_std | $3,658.24 | $36,582.42 | [$453.57, $6,862.91] | 9/10 |
| distance_based | $3,506.03 | $35,060.35 | [$1,229.70, $5,782.37] | 9/10 |
| intelligent_hiring | $3,428.10 | $34,281.00 | [$1,048.34, $5,807.86] | 8/10 |
| original_skeleton | $-1,008.68 | $-10,086.80 | [$-1,015.10, $-1,002.26] | 0/10 |

Final layout minus identical staffing without layout: mean $395.67; paired 95% t interval [$-216.82, $1,008.17].

Official competitor set contains the seven provided heuristics plus either the original skeleton (baseline) or final skeleton (final): baseline 8/8; final 1/8. No-layout is an ablation, not a ninth ranked competitor.
