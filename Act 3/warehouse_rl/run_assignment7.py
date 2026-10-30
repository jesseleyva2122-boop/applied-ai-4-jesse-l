"""Run the provided wage demo with a recorded seed and export its raw results.

Memoization repeats identical deterministic graph queries without changing wages,
orders, actions or path choices. Pass --no-cache to use original graph methods.
"""
import argparse
import json
import os
from pathlib import Path
import random
import numpy as np


def install_graph_cache():
    from environment.warehouse_grid import WarehouseGrid
    from environment.employee import Employee
    original_neighbors = WarehouseGrid.get_neighbors
    original_path = Employee._calculate_path
    path_cache = {}

    def cached_neighbors(self, x, y):
        key = (self.cell_types.tobytes(), self.item_grid.tobytes(), x, y)
        cache = getattr(self, '_assignment7_neighbor_cache', None)
        if cache is None:
            cache = {}
            self._assignment7_neighbor_cache = cache
        if key not in cache:
            if len(cache) > 8192:
                cache.clear()
            cache[key] = tuple(original_neighbors(self, x, y))
        return list(cache[key])

    def cached_path(self, grid):
        if not self.target_position:
            return
        pair = (self.position, self.target_position)
        if pair in self.failed_paths:
            self.failed_paths.clear()
        key = (grid.cell_types.tobytes(), grid.item_grid.tobytes(),
               self.position, self.target_position,
               frozenset(self.traffic_jam_zones), frozenset(self.global_traffic_zones),
               self.last_collision_position)
        if key in path_cache:
            path, failed = path_cache[key]
            self.path = list(path)
            if failed:
                self.failed_paths.add(pair)
            return
        original_path(self, grid)
        if len(path_cache) > 50000:
            path_cache.clear()
        path_cache[key] = (tuple(self.path), pair in self.failed_paths)

    WarehouseGrid.get_neighbors = cached_neighbors
    Employee._calculate_path = cached_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=20261029)
    parser.add_argument('--no-cache', action='store_true')
    args = parser.parse_args()
    os.environ.setdefault('MPLBACKEND', 'Agg')
    import multi_objective_demo as demo
    np.random.seed(args.seed)
    random.seed(args.seed)
    original_env = demo.WarehouseEnv
    original_run = demo.run_multi_objective_experiment
    output = Path(__file__).resolve().parent / 'results' / 'assignment7'
    output.mkdir(parents=True, exist_ok=True)

    def seeded_env(*positional, **keyword):
        keyword.setdefault('seed', args.seed)
        return original_env(*positional, **keyword)

    def capture(*positional, **keyword):
        results = original_run(*positional, **keyword)
        (output / 'results.json').write_text(
            json.dumps(results, indent=2, default=lambda x: x.item()) + '\n')
        return results

    demo.WarehouseEnv = seeded_env
    demo.run_multi_objective_experiment = capture
    if not args.no_cache:
        install_graph_cache()
    os.chdir(output)
    demo.main()


if __name__ == '__main__':
    main()
