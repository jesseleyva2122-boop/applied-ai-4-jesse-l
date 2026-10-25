#!/usr/bin/env python3
"""
Jesse Leyva — Assignment 5 Warehouse Simulation.

Observed-demand layout search is implemented in LayoutOptimizer. The public
skeleton_optimization factory and action format remain compatible with main.py.
A fixed five-worker/one-manager support policy prevents random staffing from
bankrupting the warehouse before layout improvements can be evaluated.
"""

import numpy as np
from typing import Dict, Optional
from .standardized_agents import BaselineAgent
from .layout_optimizer import LayoutOptimizer

class SkeletonOptimizationAgent(BaselineAgent):
    """
    Template for students to implement their own optimization algorithms.
    
    Students should replace the naive methods with:
    - Economic models for staffing decisions
    - Hungarian algorithm for order assignment  
    - Greedy search for layout optimization
    - Multi-objective optimization techniques
    """
    
    def __init__(self, env):
        super().__init__(env)
        self.name = "JesseLayoutOptimization"
        
        # Enable unlimited hiring for true economic optimization
        self.env._unlimited_hiring = True
        
        # Students can add their own state tracking here
        self.layout_optimizer = LayoutOptimizer(env, interval=100, association_weight=0.0, relocation_weight=0.0)
        self.performance_metrics = []
        self.decision_history = []
        
        # Students can add algorithm parameters here
        # Example: Hungarian algorithm matrices, greedy search parameters, etc.
        self.staffing_parameters = {
            'hire_threshold_ratio': 3.0,
            'fire_threshold_ratio': 2.0,
            'profit_threshold': 0
        }
        
        # Students can implement adaptive parameters that change based on performance
        self.adaptive_optimization_enabled = False
        
    def reset(self):
        """Reset agent state - students should expand this"""
        self.layout_optimizer.reset()
        self.action_history = []
        self.reward_history = []
        # This is a prescriptive search, not a trained neural network.
    
    def get_action(self, observation: Dict) -> Dict:
        """
        Generate action based on observation.
        Layout proposals use observed demand and legal, reachable storage slots.
        """
        
        # Extract basic info from observation
        current_timestep = observation['time'][0]
        financial_state = observation['financial']  # [profit, revenue, costs, burn_rate]
        queue_info = observation['order_queue']
        employee_info = observation['employees']
        
        action = {
            'staffing_action': self._get_naive_staffing_action(financial_state, employee_info),
            'layout_swap': self._get_naive_layout_action(current_timestep),
            'order_assignments': self._get_naive_order_assignments(queue_info, employee_info)
        }
        
        # Keep an auditable action history.
        self.action_history.append(action.copy())
        
        return action
    
    def _get_naive_staffing_action(self, financial_state, employee_info) -> int:
        """
        WEEK 2 STEP 1: Staffing decisions - students should improve this!
        
        Fixed support policy used to isolate layout effects from staffing.
        """
        
        # Stable support policy: one manager can execute relocations and five
        # workers handle orders. Read actual roles, not observation column 5
        # (which contains target distance, not the manager flag).
        if not any(employee.is_manager for employee in self.env.employees):
            return 3
        workers = sum(not employee.is_manager for employee in self.env.employees)
        return 1 if workers < 5 else 0

    def _get_naive_layout_action(self, current_timestep) -> list:
        """
        WEEK 1 STEP 1: Layout optimization - students should improve this!
        
        Uses the tested observed-frequency local search in LayoutOptimizer.
        """
        
        return self.layout_optimizer.choose_swap(int(current_timestep))

    def _get_naive_order_assignments(self, queue_info, employee_info) -> list:
        """
        WEEK 2 STEP 2: Order assignment - students should improve this!
        
        Current problems:
        - Ignores employee locations
        - No consideration of order priority/value
        - Random assignments regardless of efficiency
        - Doesn't check if employees are actually available
        """
        
        # TODO WEEK 2 STEP 2: Students should implement intelligent order assignment
        # Current approach: Random assignments
        
        assignments = [0] * 20  # No assignments by default
        
        # Count how many employees we have (very naive)
        num_employees = int(np.sum(employee_info[:, 0] > 0))
        
        # Randomly assign first few orders to first few employees
        if num_employees > 0:
            for i in range(min(3, num_employees)):  # Only assign 3 orders max
                if np.random.random() < 0.6:  # 60% chance to assign
                    assignments[i] = (i % num_employees) + 1  # Random employee
        
        return assignments
    
    def record_reward(self, reward: float):
        """
        WEEK 3 STEP 1: Reward tracking and learning - students should expand this
        
        TODO WEEK 3 STEP 1: Students should implement:
        - Proper reward tracking
        - Performance analysis
        - Adaptive parameter adjustment
        - Multi-objective optimization
        """
        self.reward_history.append(reward)
        
    def should_update_policy(self) -> bool:
        """
        WEEK 3 STEP 2: Policy updates and adaptation - students should improve this
        
        TODO WEEK 3 STEP 2: Students should implement proper update schedules
        """
        return len(self.action_history) % 50 == 0  # Arbitrary update frequency
    
    def get_performance_metrics(self) -> Dict:
        """
        Get agent performance metrics for analysis
        Students can use this to debug their improvements
        """
        if not self.reward_history:
            return {"avg_reward": 0, "total_actions": 0}
        
        return {
            "avg_reward": np.mean(self.reward_history[-100:]),  # Last 100 rewards
            "total_actions": len(self.action_history),
            "layout_decisions": len(self.layout_optimizer.decisions),
            "recent_performance": np.mean(self.reward_history[-10:]) if len(self.reward_history) >= 10 else 0
        }


def create_skeleton_optimization_agent(env) -> SkeletonOptimizationAgent:
    """Factory function to create skeleton Optimization agent"""
    return SkeletonOptimizationAgent(env)


# TODO: Students should implement these advanced components:

class StudentOptimizationAgent(SkeletonOptimizationAgent):
    """Backward-compatible name for the completed student implementation."""
    pass
