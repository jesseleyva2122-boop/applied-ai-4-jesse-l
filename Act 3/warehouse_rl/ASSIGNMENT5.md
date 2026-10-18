# Assignment 5 Warehouse Simulation
Jesse Leyva

## Where to find the work
- Layout implementation: `agents/layout_optimizer.py`, `LayoutOptimizer.choose_swap`.
- Registered agent: `agents/skeleton_rl_agent.py`, `skeleton_optimization`.
- Original agent preserved unchanged: `agents/original_skeleton.py`.
- Experiments and raw per-episode data: `results/`.
- Two-paragraph reflection and final statistics: `reflection.md`.
- Tests: `tests/test_layout_optimizer.py`.

## Problem formulation
The business objective is to maximize delivered-order revenue minus wages and
other simulated operating costs over an episode. Product-to-slot placement,
order-to-worker assignment, and staffing/wage choices are decision variables.
This assignment optimizes placement; it uses five workers and one manager as a
controlled support policy. It retains the starter order-assignment behavior and
the simulator's routing and automatic assignment, rather than claiming to solve
staffing, routing, and layout jointly.

Constraints include storage-only endpoints, reachable aisles, one product per
slot, preservation of existing product copies, an available manager, worker
capacity, the episode horizon, and the simulator's bankruptcy cutoff. A proposal
is submitted as an action: the agent never teleports products, edits revenue,
reads future orders, or executes a swap directly.

The search minimizes sum(observed projected accesses × distance to the nearest
reachable copy). Distance to a delivery bay is computed by multi-source BFS
through the actual aisle network, including one final step to the storage cell.
Every candidate is scored after swapping *both* products. The optional association
term penalizes separation of frequently co-ordered products; an optional movement
penalty charges estimated manager travel. These are distance surrogates, not
guaranteed dollar savings. The final parameter choice is based on development
measurements, not assumptions that more complicated scoring must work better.

## Implementation and trade-offs
Every 100 steps after a 100-step observation period, search all distinct storage
pairs if a manager is idle and the queue is manageable. Skip pairs attempted
within 300 steps. Require predicted improvement greater than one distance unit;
otherwise return the no-op [0, 0]. Geometry is cached only for the current grid
and reset every episode. Multiple copies of a product are evaluated by the
nearest reachable copy.

Moving a popular item closer can displace another valuable product or consume
manager time. Clustering related products can also move them farther from the
delivery bay. The combined score exposes those trade-offs, while the benchmarks
determine whether they produce real profit. Observed accesses can underrepresent
hard-to-retrieve items; future work should compare an arrival-demand estimate.

The original skeleton misread employee-observation column 5 as a manager flag;
it actually contains target distance. The support policy uses employee roles
directly. Its profit gain is explicitly separated from the layout contribution
by a five-worker/one-manager no-layout ablation. The location-query optimization
in warehouse_grid.py uses NumPy to return the same row-major coordinates as the
original loops; it changes runtime, not simulation rules.

## Reproduce
From this directory:
```bash
pip install -r requirements.txt
python main.py --mode demo --agent aggressive_swap
python main.py --mode benchmark --episodes 10
python -m unittest discover -s tests -v
OPENBLAS_NUM_THREADS=1 python evaluate_layout.py --episodes 10 --seed 7200 --workers 8 --agents greedy_std,random_std,fixed_std,intelligent_hiring,intelligent_queue,distance_based,aggressive_swap,original_skeleton,no_layout,skeleton_optimization --output results/heldout_benchmark.json
```

A headless machine can use SDL_VIDEODRIVER=dummy, SDL_AUDIODRIVER=dummy and
MPLBACKEND=Agg for the visual-demo smoke test. This verifies rendering initializes
but does not imply a human watched an interactive display.

## Evaluation protocol
Development uses seeds 6100–6102. It compares the untouched starter, stable
staffing without swaps, frequency-only placement, an association-weight .15
variant, and that association variant with relocation-weight 1. The saved
development results retain the parameters used then: its label
skeleton_optimization represents the rejected movement-penalty candidate, not
the final selected policy. Frequency-only placement was selected before the
held-out run. Final parameters are interval 100, association weight 0 and
relocation weight 0.

Held-out evaluation uses ten fresh seeds, 7200–7209, and 3,000-step episodes.
Each agent gets a fresh environment and RNG initialization for each episode.
Adaptive order generation responds to outcomes, so identical seeds do not imply
identical realized order streams. The seven provided heuristic agents remain
unchanged. Rank the starter among those seven plus the starter; rank the final
agent among those seven plus the final agent. Ablations are additional diagnostic
comparisons, not extra competitors added to inflate ranking.

Report mean episode profit, the sum across ten episodes, and a Student-t 95%
confidence interval for the mean with sample SD (ddof=1). The stock CLI uses a
normal 1.96 multiplier and population SD instead; its approximate intervals are
identified separately. A confidence interval for a mean is not a range expected
to contain 95% of future episodes. Use a paired-seed difference interval when
comparing the layout with stable staffing, and avoid treating overlapping or
non-overlapping marginal intervals as a formal significance test. Ten seeds are
limited evidence, not a universal performance guarantee.
