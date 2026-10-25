"""Contract and decision tests for the staffing/pickup algorithms."""

import unittest
from unittest.mock import patch
from environment.warehouse_env import WarehouseEnv
from environment.employee import EmployeeState
from environment.order_generator import Order
from agents.skeleton_rl_agent import SkeletonOptimizationAgent


class OptimizationTests(unittest.TestCase):
    def setUp(self):
        self.env = WarehouseEnv(seed=101, episode_length=3000)
        self.obs, _ = self.env.reset(seed=101)
        self.agent = SkeletonOptimizationAgent(self.env)

    def tearDown(self):
        self.env.close()

    def pending(self, n=6):
        self.env.order_queue.orders = [Order(i + 1, [0], 200, 0) for i in range(n)]

    def test_empty_queue_no_hiring_or_assignments(self):
        self.assertEqual(self.agent.optimize_staffing(), 0)
        self.assertEqual(self.agent.optimize_order_assignments(), [0] * 20)

    def test_hiring_has_margin_and_respects_cooldown(self):
        self.pending()
        for e in self.env.employees:
            e.state = EmployeeState.MOVING
        self.assertEqual(self.agent.optimize_staffing(), 4)
        self.agent.last_staff_change = 0
        self.assertEqual(self.agent.optimize_staffing(), 0)

    def test_no_late_hire_or_hire_at_cap(self):
        self.pending()
        for e in self.env.employees:
            e.state = EmployeeState.MOVING
        self.env.current_timestep = 2990
        self.assertEqual(self.agent.optimize_staffing(), 0)
        self.env.current_timestep = 0
        self.agent.max_workers = 3
        self.assertEqual(self.agent.optimize_staffing(), 0)

    def test_no_hire_with_poor_marginal_revenue(self):
        self.pending()
        for o in self.env.order_queue.orders:
            o.value = 0.01
        for e in self.env.employees:
            e.state = EmployeeState.MOVING
        self.assertEqual(self.agent.optimize_staffing(), 0)

    def test_manager_dependency(self):
        self.env.current_timestep = 200
        self.env.cumulative_profit = 500
        self.assertEqual(self.agent.optimize_staffing(), 3)

    def test_fire_only_sustained_idle_worker(self):
        self.env._hire_employee()
        self.env.current_timestep = 300
        self.agent.low_demand_since = 0
        self.assertEqual(self.agent.optimize_staffing(), 2)
        self.env.employees[0].is_manager = True
        self.assertEqual(self.agent.optimize_staffing(), 0)

    def test_global_assignment_beats_greedy(self):
        self.pending(2)
        self.env.employees = self.env.employees[:2]
        # Greedy takes 1 then 100; global matching takes 2 then 2.
        times = {(1, 1): 1, (1, 2): 2, (2, 1): 2, (2, 2): 100}
        self.agent.estimate_trip = lambda e, o: times[e.id, o.id]
        a = self.agent.optimize_order_assignments()
        self.assertEqual(a[:2], [2, 1])

    def test_managers_busy_and_claimed_excluded(self):
        self.pending(4)
        self.env.employees[0].is_manager = True
        self.env.employees[1].state = EmployeeState.MOVING
        self.env.employees[1].current_order_id = 2
        self.env.order_queue.orders[1].status = "claimed"
        self.agent.estimate_trip = lambda e, o: 20
        a = self.agent.optimize_order_assignments()
        self.assertEqual(a[1], 0)
        self.assertEqual([x for x in a if x], [3])

    def test_twenty_slot_bounds_and_uniqueness(self):
        self.pending(25)
        self.agent.estimate_trip = lambda e, o: 20
        a = self.agent.optimize_order_assignments()
        self.assertEqual(len(a), 20)
        selected = [x for x in a if x]
        self.assertEqual(len(selected), len(set(selected)))
        self.assertTrue(all(0 <= x <= self.env.max_employees for x in a))

    def test_firing_tick_has_no_stale_assignments(self):
        with patch.object(self.agent, "optimize_staffing", return_value=2):
            self.assertEqual(
                self.agent.get_action(self.obs)["order_assignments"], [0] * 20
            )

    def test_unreachable_items_do_not_crash_solver(self):
        self.pending(2)
        self.agent.estimate_trip = lambda e, o: float("inf")
        self.assertEqual(self.agent.optimize_order_assignments(), [0] * 20)

    def test_full_queue_hook_can_pick_beyond_twenty(self):
        self.pending(25)
        self.env.order_queue.orders[24].value = 2000
        self.agent.estimate_trip = lambda e, o: 20
        self.assertGreater(self.agent.optimize_order_assignments(limit=None)[24], 0)

    def test_low_value_work_does_not_deadlock(self):
        self.pending(1)
        self.env.order_queue.orders[0].value = 1
        self.agent.estimate_trip = lambda e, o: 100
        self.assertGreater(self.agent.optimize_order_assignments()[0], 0)

    def test_intra_step_hook_assigns_newly_idle_workers(self):
        self.pending(2)
        self.agent.estimate_trip = lambda e, o: 20
        self.env.order_assignment_policy = (
            lambda: self.agent.optimize_order_assignments(limit=None)
        )
        self.env._auto_assign_idle_employees()
        self.assertEqual(
            sum(e.current_order_id is not None for e in self.env.employees), 2
        )

    def test_environment_reset_removes_previous_policy(self):
        self.env.order_assignment_policy = lambda: [1] * 20
        self.env.reset(seed=1)
        self.assertIsNone(self.env.order_assignment_policy)

    def test_reset_clears_caches_and_history(self):
        self.agent._distances(self.env.employees[0].position)
        self.agent.staffing_history.append({})
        self.agent.reset()
        self.assertEqual(self.agent.distance_maps, {})
        self.assertEqual(self.agent.staffing_history, [])

    def test_aisle_distances_obey_walls(self):
        p = self.env.employees[0].position
        d = self.agent._distances(p)
        self.assertEqual(d[p], 0)
        # The starter's spawn cell itself can be nonwalkable; subsequent cells
        # must be walkable. Employees may start there and step into an aisle.
        self.assertTrue(
            all(x == p or self.env.warehouse_grid.is_walkable(*x) for x in d)
        )

    def test_short_episode_action_contract(self):
        self.env.episode_length = 120
        for _ in range(120):
            a = self.agent.get_action(self.obs)
            self.assertTrue(self.env.action_space.contains(a))
            self.obs, _, done, truncated, _ = self.env.step(a)
            if done or truncated:
                break


if __name__ == "__main__":
    unittest.main()
