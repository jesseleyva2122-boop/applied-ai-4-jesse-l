"""Safety and objective tests for the layout search."""
import unittest
from types import SimpleNamespace
import numpy as np
from agents.layout_optimizer import LayoutOptimizer
from environment.warehouse_grid import WarehouseGrid, CellType
from environment.employee import EmployeeState
from environment.warehouse_env import WarehouseEnv
from agents.skeleton_rl_agent import SkeletonOptimizationAgent


class LayoutTests(unittest.TestCase):
    def fixture(self):
        # A reachable aisle runs along row 1. The hot item starts far away.
        grid=WarehouseGrid(8,8,2)
        grid.cell_types[:]=CellType.EMPTY.value
        grid.item_grid[:]=-1
        grid.truck_bay_positions=[(7,1)]
        grid.cell_types[0,0]=grid.cell_types[0,6]=CellType.STORAGE.value
        grid.item_grid[0,0]=0;grid.item_grid[0,6]=1
        grid.item_access_frequency[:]=[100,1]
        manager=SimpleNamespace(is_manager=True,state=EmployeeState.IDLE,position=(7,1))
        env=SimpleNamespace(warehouse_grid=grid,grid_width=8,grid_height=8,episode_length=3000,
            employees=[manager],order_queue=SimpleNamespace(orders=[]),_get_manager=lambda:manager)
        return env,LayoutOptimizer(env)

    def test_profitable_swap_and_bounds(self):
        env,opt=self.fixture()
        action=opt.choose_swap(100)
        self.assertEqual(set(action),{0,6})
        self.assertGreater(opt.decisions[0]["predicted_net_distance_gain"],0)
        # Both endpoints are storage, never an aisle or a delivery bay.
        self.assertTrue(all(env.warehouse_grid.cell_types[a//8,a%8]==1 for a in action))

    def test_no_manager_or_no_demand(self):
        env,opt=self.fixture()
        env._get_manager=lambda:None
        self.assertEqual(opt.choose_swap(100),[0,0])
        env,opt=self.fixture();env.warehouse_grid.item_access_frequency[:]=0
        self.assertEqual(opt.choose_swap(100),[0,0])

    def test_busy_manager_and_cooldown(self):
        env,opt=self.fixture()
        env.employees[0].state=EmployeeState.RELOCATING_ITEM
        self.assertEqual(opt.choose_swap(100),[0,0])
        env.employees[0].state=EmployeeState.IDLE
        opt.choose_swap(100)
        self.assertEqual(opt.choose_swap(200),[0,0])
        opt.reset();self.assertFalse(opt.decisions);self.assertIsNone(opt.grid_ref)

    def test_displaced_hot_item_not_sacrificed(self):
        env,opt=self.fixture()
        env.warehouse_grid.item_access_frequency[:]=[1,100]
        self.assertEqual(opt.choose_swap(100),[0,0])

    def test_environment_action_and_metrics(self):
        np.random.seed(31)
        env=WarehouseEnv(episode_length=120,seed=31)
        obs,_=env.reset(seed=31);agent=SkeletonOptimizationAgent(env);agent.reset()
        for _ in range(120):
            action=agent.get_action(obs)
            self.assertTrue(env.action_space.contains(action))
            obs,reward,done,truncated,_=env.step(action)
            agent.record_reward(reward)
            if done or truncated:break
        self.assertTrue(np.isfinite(agent.get_performance_metrics()["avg_reward"]))
        env.close()

if __name__=="__main__":unittest.main()
