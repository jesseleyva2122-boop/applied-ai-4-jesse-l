"""Jesse Leyva: economic staffing and Hungarian pickup matching.

Reads current simulator objects for roles, item lists, wages and deadlines that
are absent from the compact observations. Does not inspect future demand.
"""
from collections import deque
import numpy as np
from scipy.optimize import linear_sum_assignment
from .standardized_agents import BaselineAgent
from .layout_optimizer import LayoutOptimizer
from environment.employee import EmployeeState

class SkeletonOptimizationAgent(BaselineAgent):
    def __init__(self, env, max_workers=10, wage_action=4, routing=True):
        super().__init__(env)
        self.name = 'JesseIntegratedOptimization'
        self.max_workers = min(max_workers, max(1, env.max_employees-1))
        self.wage_action, self.routing = wage_action, routing
        self.env._unlimited_hiring = False
        self.layout_optimizer = LayoutOptimizer(env, interval=100)
        self.reset()

    def reset(self):
        self.layout_optimizer.reset()
        self.last_staff_change = -100
        self.low_demand_since = None
        self.action_history, self.reward_history, self.staffing_history = [], [], []
        self.distance_maps, self.geometry = {}, None
        self.service_estimate = 60.0

    def get_action(self, observation):
        self.env.order_assignment_policy = self.optimize_order_assignments if self.routing else None
        staffing = self.optimize_staffing()
        # Firing changes indices before assignments execute. Use the simulator's
        # safe automatic assignment on that tick instead of stale indices.
        assignments = self.optimize_order_assignments() if self.routing and staffing != 2 else [0]*20
        action = {'staffing_action': staffing,
                  'layout_swap': self.layout_optimizer.choose_swap(self.env.current_timestep),
                  'order_assignments': assignments}
        if staffing:
            self.last_staff_change = self.env.current_timestep
            self.staffing_history.append({'time': self.env.current_timestep, 'action': staffing})
        self.action_history.append(action)
        return action

    def optimize_staffing(self):
        """Compare estimated extra revenue with payroll; use cooldown/hysteresis.

        The fire action removes the first idle person. Only fire when that
        person is a worker, preserving the layout manager and active orders.
        """
        env = self.env
        now, remaining = env.current_timestep, env.episode_length-env.current_timestep
        workers = [e for e in env.employees if not e.is_manager]
        pending = [o for o in env.order_queue.orders if o.status == 'pending']
        idle = [e for e in workers if e.state == EmployeeState.IDLE]
        if pending: self.low_demand_since = None
        elif self.low_demand_since is None: self.low_demand_since = now
        if now-self.last_staff_change < 40: return 0
        # One manager is the dependency for the previous layout optimizer.
        if (not env._get_manager() and len(env.employees)<env.max_employees
                and now>=100 and env.cumulative_profit>200 and remaining>400):
            return 3
        wage = {1:.20, 4:.50, 5:.80}[self.wage_action]
        speed = {1:2/3, 4:1.2, 5:1.5}[self.wage_action]
        value = float(np.mean([o.value for o in pending])) if pending else 0
        duration = self.service_estimate/speed
        horizon = min(remaining, 200)
        benefit = min(len(pending), horizon/duration)*value
        cost = horizon*wage
        pressure = len(pending)/max(1,len(workers))
        if (not idle and len(workers)<self.max_workers and len(env.employees)<env.max_employees
                and remaining>duration+40 and (pressure>=.8 or len(workers)<4)
                and benefit>1.5*cost and env.cumulative_profit>-700):
            return self.wage_action
        low_for = now-self.low_demand_since if self.low_demand_since is not None else 0
        first_idle = next((e for e in env.employees if e.state==EmployeeState.IDLE), None)
        if (len(workers)>3 and len(idle)>=2 and low_for>=160
                and first_idle is not None and not first_idle.is_manager):
            return 2
        return 0

    def _distances(self, start):
        grid = self.env.warehouse_grid
        if self.geometry is not grid:
            self.geometry, self.distance_maps = grid, {}
        start = tuple(start)
        if start not in self.distance_maps:
            distances, todo = {start:0}, deque([start])
            while todo:
                x,y = todo.popleft()
                for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                    if p not in distances and grid.is_walkable(*p):
                        distances[p] = distances[(x,y)]+1
                        todo.append(p)
            self.distance_maps[start] = distances
        return self.distance_maps[start]

    def estimate_trip(self, employee, order):
        """Aisle-aware nearest-neighbor tour plus packing, a cost surrogate.

        Live item locations account for layout changes. The movement engine
        retains actual route choice and collisions; this is not an ETA guarantee.
        """
        grid, position = self.env.warehouse_grid, tuple(employee.position)
        distance, remaining = 0, list(order.items)
        while remaining:
            candidates, reach = [], self._distances(position)
            for k,item in enumerate(remaining):
                for x,y in grid.find_item_locations(item):
                    for p in ((x,y+1),(x+1,y),(x,y-1),(x-1,y)):
                        if p in reach: candidates.append((reach[p],k,p))
            if not candidates: return float('inf')
            leg,k,position = min(candidates)
            distance += leg
            remaining.pop(k)
        reach = self._distances(position)
        delivery = min((reach.get(tuple(p),float('inf')) for p in grid.truck_bay_positions),default=float('inf'))
        speed = max(.1,employee.base_speed_multiplier)
        return (distance+delivery)/speed + (len(order.items)+1)*max(1,int(2/speed))

    def optimize_order_assignments(self):
        """Hungarian matching maximizes current value/time with age and urgency.

        Only pending orders in the 20 action slots and idle nonmanagers qualify.
        Worker/order uniqueness is enforced globally, rather than greedily.
        """
        assignments, env = [0]*20, self.env
        workers = [(i,e) for i,e in enumerate(env.employees[:env.max_employees])
                   if not e.is_manager and e.state==EmployeeState.IDLE and e.current_order_id is None]
        claimed = {e.current_order_id for e in env.employees if e.current_order_id is not None}
        orders = [(i,o) for i,o in enumerate(env.order_queue.orders[:20])
                  if o.status=='pending' and o.id not in claimed]
        if not workers or not orders: return assignments
        costs, durations = np.zeros((len(workers),len(orders))), []
        for row,(_,employee) in enumerate(workers):
            for col,(_,order) in enumerate(orders):
                duration = self.estimate_trip(employee,order)
                if not np.isfinite(duration):
                    costs[row,col] = 1e6
                    continue
                durations.append(duration*employee.base_speed_multiplier)
                age = max(0,env.current_timestep-order.arrival_time)
                bonus = 1+min(age/400,.75)
                if order.deadline is not None:
                    slack = order.deadline-env.current_timestep
                    bonus *= 1.4 if duration<=slack<duration+80 else .2 if slack<duration else 1
                if duration>=env.episode_length-env.current_timestep: bonus *= .1
                costs[row,col] = -order.value*bonus/(duration+10)
        if durations: self.service_estimate = .9*self.service_estimate+.1*float(np.median(durations))
        rows,cols = linear_sum_assignment(costs)
        for r,c in zip(rows,cols):
            if costs[r,c]<0: assignments[orders[c][0]] = workers[r][0]+1
        return assignments

    # Preserve worksheet entry points.
    def _get_naive_staffing_action(self,financial_state=None,employee_info=None):
        return self.optimize_staffing()
    def _get_naive_order_assignments(self,queue_info=None,employee_info=None):
        return self.optimize_order_assignments()
    def _get_naive_layout_action(self,current_timestep):
        return self.layout_optimizer.choose_swap(int(current_timestep))
    def record_reward(self,reward): self.reward_history.append(float(reward))
    def get_performance_metrics(self):
        return {'total_actions':len(self.action_history),'staffing_changes':len(self.staffing_history),
                'avg_reward':float(np.mean(self.reward_history[-100:])) if self.reward_history else 0.0,
                'layout_decisions':len(self.layout_optimizer.decisions)}

def create_skeleton_optimization_agent(env): return SkeletonOptimizationAgent(env)

class StudentOptimizationAgent(SkeletonOptimizationAgent):
    """Compatibility name for the completed implementation."""
