"""Greedy local search using observed demand, never future order data."""
from collections import deque
import numpy as np
from environment.employee import EmployeeState
from environment.warehouse_grid import CellType


class LayoutOptimizer:
    """Score the *whole* affected layout, including the displaced product.

    Frequency and association costs are walking-distance surrogates, not dollars.
    A positive predicted gain does not guarantee higher realized profit.
    """
    def __init__(self, env, interval=100, association_weight=0.0,
                 relocation_weight=0.0):
        self.env = env
        self.interval = interval
        self.association_weight = association_weight
        self.relocation_weight = relocation_weight
        self.reset()

    def reset(self):
        self.grid_ref = None
        self.decisions = []
        self.recent_pairs = {}

    def _prepare_geometry(self, grid):
        # Multi-source BFS measures actual aisle routes to a packing station.
        distance = {}
        todo = deque(grid.truck_bay_positions)
        for pos in todo:
            distance[pos] = 0
        while todo:
            x, y = todo.popleft()
            for nxt in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if nxt not in distance and grid.is_walkable(*nxt):
                    distance[nxt] = distance[(x,y)] + 1
                    todo.append(nxt)
        self.positions = []
        self.distances = []
        for y, x in zip(*np.where(grid.cell_types == CellType.STORAGE.value)):
            adjacent = [(int(x)+1,int(y)),(int(x)-1,int(y)),
                        (int(x),int(y)+1),(int(x),int(y)-1)]
            routes = [distance[p] for p in adjacent if p in distance]
            if routes:
                self.positions.append((int(x),int(y)))
                self.distances.append(1 + min(routes))
        self.distances = np.asarray(self.distances, dtype=float)
        self.grid_ref = grid

    def _cost(self, items, frequency, associations):
        # Multiple storage copies are supported. A product is evaluated at its
        # nearest reachable copy, rather than arbitrarily using locations[0].
        count = len(frequency)
        nearest = np.full(count, float(self.env.grid_width+self.env.grid_height)*2)
        representatives = np.zeros((count, 2))
        present = np.zeros(count, dtype=bool)
        for i, item in enumerate(items):
            if item >= 0 and self.distances[i] < nearest[item]:
                nearest[item] = self.distances[i]
                representatives[item] = self.positions[i]
                present[item] = True
        cost = float(np.dot(frequency, nearest))
        if self.association_weight:
            delta = np.abs(representatives[:,None,:]-representatives[None,:,:]).sum(axis=2)
            mask = present[:,None] & present[None,:]
            cost += self.association_weight * float(np.sum(np.triu(associations*delta*mask,1)))
        return cost

    def choose_swap(self, timestep):
        if timestep < 100 or timestep % self.interval:
            return [0, 0]
        manager = self.env._get_manager()
        if manager is None or manager.state != EmployeeState.IDLE:
            return [0, 0]
        # Do not interrupt a worker-capacity crisis with a relocation.
        workers = sum(not emp.is_manager for emp in self.env.employees)
        if len(self.env.order_queue.orders) > max(20, workers*15):
            return [0, 0]
        grid = self.env.warehouse_grid
        if self.grid_ref is not grid:
            self._prepare_geometry(grid)
        if len(self.positions) < 2:
            return [0, 0]
        frequency = np.asarray(grid.item_access_frequency, dtype=float)
        if not np.any(frequency > 0):
            return [0, 0]
        # Estimate future demand from completed accesses, with no hidden weights.
        remaining = max(0, self.env.episode_length - timestep)
        scale = remaining / max(timestep, 1)
        frequency = frequency * scale
        associations = np.asarray(grid.item_cooccurrence, dtype=float) * scale
        associations = np.where(grid.item_cooccurrence >= 3, associations, 0)
        items = np.array([grid.item_grid[y,x] for x,y in self.positions])
        initial_cost = self._cost(items, frequency, associations)
        best_gain, best_pair = 1.0, None
        # Exhaustive pair neighborhood; skip duplicate products and empty sources.
        for i in range(len(items)):
            if items[i] < 0:
                continue
            for j in range(i+1, len(items)):
                if items[i] == items[j]:
                    continue
                pair = (i,j)
                if timestep-self.recent_pairs.get(pair,-10000) < 300:
                    continue
                trial = items.copy()
                trial[i], trial[j] = trial[j], trial[i]
                a,b = self.positions[i], self.positions[j]
                travel = (abs(manager.position[0]-a[0])+abs(manager.position[1]-a[1])
                          +2*(abs(a[0]-b[0])+abs(a[1]-b[1]))+6)
                gain = initial_cost - self._cost(trial, frequency, associations)
                gain -= self.relocation_weight*travel
                if gain > best_gain:
                    best_gain, best_pair = gain, pair
        if best_pair is None:
            return [0, 0]
        i,j = best_pair
        self.recent_pairs[best_pair] = timestep
        self.decisions.append({"timestep":int(timestep),"predicted_net_distance_gain":float(best_gain),
                               "source":self.positions[i],"target":self.positions[j]})
        return [self.positions[k][1]*grid.width+self.positions[k][0] for k in (i,j)]
