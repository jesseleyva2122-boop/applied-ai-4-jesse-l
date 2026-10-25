# Warehouse Staffing and Pickup Optimization
Jesse Leyva — Assignment 6

## Completed implementation
- [`agents/skeleton_rl_agent.py`](agents/skeleton_rl_agent.py): `optimize_staffing()` and `optimize_order_assignments()`.
- [`agents/layout_optimizer.py`](agents/layout_optimizer.py): retains the previous unit's observed-demand layout search.
- [`reflection.md`](reflection.md): two-paragraph reflection based on the completed benchmark.
- [`results/assignment6/benchmark.json`](results/assignment6/benchmark.json): all individual episodes, placement, total profit, and 95% confidence intervals.
- [`results/assignment6/SUMMARY.md`](results/assignment6/SUMMARY.md): readable before/after table, heuristic rankings, and ablations.
- [`tests/test_staffing_routing.py`](tests/test_staffing_routing.py): hiring, firing, assignment, and integration tests.

## Run
From the repository root:
```bash
cd 'Act 3/warehouse_rl'
python -m pip install -r requirements-benchmark.txt
python -m unittest discover -s tests -v
python main.py --mode demo --agent aggressive_swap
python main.py --mode demo --agent skeleton_optimization
python main.py --mode benchmark --episodes 10
```
The benchmark uses fresh environments, seeds 9100–9109, and 3,000 steps per episode. It writes `results/assignment6/benchmark.json`. For different seeds, episode lengths, or worker processes, use `python evaluate_staffing.py --help`. A bankruptcy can end an episode early and is retained as a result. The demo was also exercised through Pygame's dummy display in the headless development environment; an interactive desktop will show the simulation window.

## Problem formulation
The decisions are how many workers to employ, which available wage action to use for new hires, whether one manager is justified, and which pending order each idle worker should collect. Product relocations continue to be selected by the previous layout algorithm. The objective is to maximize realized cumulative simulator profit, which includes delivered-order revenue, wages, and collision penalties. Matching uses an estimated contribution score rather than claiming to solve the entire stochastic warehouse optimally.

Constraints include the 20-person environment limit, one order per worker, one worker per order, no pickup assignments to managers or busy workers, reachable aisles, order deadlines, a finite episode, bankruptcy, and the need for an idle manager to relocate products. New worker wages trade off speed against payroll; extra people can also create aisle congestion. The simulator has no explicit shifts or overtime model, so the policy changes headcount over time rather than inventing shift controls.

## Staffing strategy
The policy estimates service time from currently evaluated trips. It compares the revenue one extra worker might earn over a short horizon against payroll, requiring a 50% safety margin. Hiring also requires real pending demand, busy workers, sufficient remaining time, and a safety buffer above bankruptcy. Development comparisons supported medium-wage hires ($0.50 per step) rather than the slower $0.20 option. The final policy caps picking workers at 12 and respects the total employee limit. The initial workers keep the simulator's original wages.

One manager is hired after profit exceeds $200 with enough episode time left for layout improvements. A 40-step cooldown separates staffing changes. Downsizing requires at least 160 quiet steps and excess idle capacity, with a minimum of three workers. Because the starter firing API removes the first idle employee, firing is allowed only when that employee is a worker. Explicit pickup assignments are omitted on firing ticks so shifted indices cannot target the wrong employee.

## Pickup strategy
Breadth-first search provides walking distances through aisles. A nearest-neighbor tour estimates collection and delivery time, including wage-dependent speed and handling time. Live product positions keep the estimate consistent with relocations. The Hungarian algorithm chooses unique worker/order pairs using order value minus a time cost, with modest age and deadline adjustments. A bounded shortlist of 40 high-value pending orders limits computation. It is optimal for that cost matrix, not globally optimal for future orders, congestion, or the complete warehouse.

The simulator normally assigns newly idle workers inside each step, before the next agent decision. The optional `order_assignment_policy` hook in `environment/warehouse_env.py` runs matching at that same moment, so the policy is actually used. Baselines keep their original fallback; reset clears the hook. Ordinary actions retain the original 20 assignment slots. The hook can consider the full current queue, matching the information available to the original automatic allocator. It never reads future orders or hidden item-popularity weights.

## Evaluation and limitations
The previous layout agent is saved unchanged in `agents/previous_layout_agent.py`. Previous/final policies and seven provided heuristics are evaluated independently. The original serial CLI reused one environment across agents and did not recreate the order generator for each reset; the new CLI delegates to the seeded parallel evaluator to avoid that leakage. `run_legacy_benchmark` remains available for reference. Confidence intervals use Student's t with sample standard deviation, not the legacy normal approximation. The same seed initializes policies comparably, but demand responds to queue pressure and satisfaction, so their realized orders can differ.

Development seeds 8100–8102 were used for refinement; final seeds 9100–9109 were not used to choose parameters. Archived development outputs document unsuccessful as well as successful variants. `development.json` predates the pickup hook; `development2.json` enabled a value/time score; `development3.json` tried value-minus-time with rejected negative margins; `development4.json` removed that deadlock; `development5.json` corrected full-queue visibility. The early ratio implementation is retained as a development snapshot, not the registered agent. Initial serial CLI output is partial and is not used for reported statistics.

The final tests check uniqueness, global matching, empty/unreachable queues, full-queue access, low-value service, role exclusions, hiring bounds, cooldowns, safe firing, policy reset, and actual intra-step integration. Further work should measure congestion and learn service-time estimates from completed trips. Any incremental routing gain must be judged with the ablation results, not attributed to the overall staffing improvement.

## Source and continuity
Continues the previous submission in this repository at commit `e6113c205d602317d5a5546e78da1f93ceeb50f0`. The starter simulation comes from RizeComputerScience/applied-ai-4. The previous reflection is preserved as `reflection_assignment5.md`; Assignment 5 logs and notes remain available. No trained model export is needed for this prescriptive policy.
