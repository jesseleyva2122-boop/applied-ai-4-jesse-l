# Assignment 6 Warehouse Staffing and Routing
Jesse Leyva

The completed staffing and pickup functions continue the previous warehouse layout assignment in this repository.

- [Assignment guide and run commands](Act%203/warehouse_rl/ASSIGNMENT6.md)
- [Completed optimization functions](Act%203/warehouse_rl/agents/skeleton_rl_agent.py)
- [Two-paragraph reflection](Act%203/warehouse_rl/reflection.md)
- [Before/after results and confidence intervals](Act%203/warehouse_rl/results/assignment6/SUMMARY.md)
- [Individual benchmark episodes](Act%203/warehouse_rl/results/assignment6/benchmark.json)
- [Staffing and routing tests](Act%203/warehouse_rl/tests/test_staffing_routing.py)

The final agent ranked first against seven supplied heuristics, averaging $45,084.78 profit per episode across ten fresh test episodes, compared with $21,922.18 for the previous layout agent. The report separates the overall improvement from the smaller, uncertain incremental routing effect.
