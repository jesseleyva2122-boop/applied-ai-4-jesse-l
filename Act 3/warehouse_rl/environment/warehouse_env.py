import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from .warehouse_grid import WarehouseGrid
from .employee import Employee, EmployeeState
from .order_generator import OrderGenerator, OrderQueue, Order

class WarehouseEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}
    
    def __init__(self, 
                 grid_width: int = 20,
                 grid_height: int = 20,
                 num_item_types: int = 50,
                 max_employees: int = 20,  # Lower cap for better profit margins
                 initial_employees: int = 3,
                 episode_length: int = 7500,
                 order_arrival_rate: float = 0.5,
                 order_timeout: int = 200,
                 employee_salary: float = 0.30,  # Reduced cost to improve profitability
                 render_mode: Optional[str] = None,
                 seed: Optional[int] = None):
        
        super().__init__()
        
        # Environment parameters
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.num_item_types = num_item_types
        self.max_employees = max_employees
        self.initial_employees = initial_employees
        self.episode_length = episode_length
        self.employee_salary = employee_salary
        self.render_mode = render_mode
        
        # Initialize components
        self.warehouse_grid = WarehouseGrid(grid_width, grid_height, num_item_types)
        self.order_generator = OrderGenerator(num_item_types, order_arrival_rate, order_timeout, seed)
        self.order_queue = OrderQueue()
        
        # Employee management
        self.employees: List[Employee] = []
        self.next_employee_id = 1
        
        # Episode state
        self.current_timestep = 0
        self.total_revenue = 0.0
        self.total_costs = 0.0
        self.cumulative_profit = 0.0
        self.order_assignment_policy = None
        
        # Relocation tracking
        self.relocations_history = []  # List of {item_type, from_pos, to_pos, timestep, status}
        self.last_swap_info = None  # Track last swap for analytics
        
        # Action space: Strategic and tactical decisions
        self.action_space = spaces.Dict({
            'staffing_action': spaces.Discrete(6),  # 0: no change, 1: hire low wage, 2: fire, 3: hire manager, 4: hire medium wage, 5: hire high wage
            'layout_swap': spaces.MultiDiscrete([grid_height * grid_width, grid_height * grid_width]),  # Two positions to swap
            'order_assignments': spaces.MultiDiscrete([self.max_employees + 1] * 20)  # Assign orders to employees (0=no assignment, 1-max_employees=employee index)
        })
        
        # Observation space
        max_queue_size = 20
        max_employees_obs = self.max_employees
        
        self.observation_space = spaces.Dict({
            'warehouse_grid': spaces.Box(low=-1, high=num_item_types-1, 
                                       shape=(grid_height, grid_width), dtype=np.int32),
            'item_access_frequency': spaces.Box(low=0, high=np.inf, 
                                              shape=(num_item_types,), dtype=np.float32),
            'order_queue': spaces.Box(low=0, high=np.inf, 
                                    shape=(max_queue_size, 4), dtype=np.float32),  # [num_items, value, time_remaining, arrival_time]
            'employees': spaces.Box(low=0, high=np.inf, 
                                  shape=(max_employees_obs, 6), dtype=np.float32),  # [x, y, state, has_order, items_collected, target_distance]
            'financial': spaces.Box(low=-np.inf, high=np.inf, 
                                  shape=(4,), dtype=np.float32),  # [profit, revenue, costs, burn_rate]
            'time': spaces.Box(low=0, high=episode_length, shape=(1,), dtype=np.int32)
        })
        
        # Rendering
        self.renderer = None
        if render_mode == "human":
            try:
                try:
                    from ..visualization.pygame_renderer import PygameRenderer
                except ImportError:
                    from visualization.pygame_renderer import PygameRenderer
                self.renderer = PygameRenderer(self)
            except ImportError:
                print("Warning: Pygame not available, rendering disabled")
                self.renderer = None
    
    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[Dict, Dict]:
        super().reset(seed=seed)
        self.order_assignment_policy = None
        
        # Reset environment state
        self.current_timestep = 0
        self.total_revenue = 0.0
        self.total_costs = 0.0
        self.cumulative_profit = 0.0
        
        # Reset warehouse grid
        self.warehouse_grid = WarehouseGrid(self.grid_width, self.grid_height, self.num_item_types)
        
        # Reset order system
        self.order_queue = OrderQueue()
        
        # Reset employees
        self.employees = []
        self.next_employee_id = 1
        
        # Reset relocation tracking
        self.relocations_history = []
        
        # Create initial employees
        for _ in range(self.initial_employees):
            self._hire_employee()
        
        observation = self._get_observation()
        info = self._get_info()
        
        return observation, info
    
    def step(self, action: Dict) -> Tuple[Dict, float, bool, bool, Dict]:
        # Execute action
        reward = self._execute_action(action)
        
        # Simulate one timestep
        timestep_reward = self._simulate_timestep()
        reward += timestep_reward
        
        # Check termination conditions
        terminated = self.current_timestep >= self.episode_length
        truncated = self.cumulative_profit < -1000  # Bankruptcy
        
        # Get new observation
        observation = self._get_observation()
        info = self._get_info()
        
        # Render if needed
        if self.render_mode == "human" and self.renderer:
            self.renderer.render()
        
        return observation, reward, terminated, truncated, info
    
    def _execute_action(self, action: Dict) -> float:
        reward = 0.0
        
        # Handle staffing decisions with wage options
        staffing_action = action['staffing_action']
        unlimited_hiring = getattr(self, '_unlimited_hiring', False)
        can_hire = unlimited_hiring or len(self.employees) < self.max_employees
        
        # Allow agents to set preferred wage level
        preferred_wage = getattr(self, '_preferred_wage', None)
        
        if staffing_action == 1 and can_hire:  # Hire low wage worker
            wage = preferred_wage if preferred_wage and preferred_wage <= 0.30 else 0.20
            self._hire_employee(is_manager=False, custom_salary=wage)
        elif staffing_action == 2:  # Fire
            if len(self.employees) > 0:
                self._fire_employee()
        elif staffing_action == 3 and can_hire:  # Hire manager
            self._hire_employee(is_manager=True, custom_salary=1.0)
        elif staffing_action == 4 and can_hire:  # Hire medium wage worker
            wage = preferred_wage if preferred_wage and 0.30 < preferred_wage <= 0.60 else 0.50
            self._hire_employee(is_manager=False, custom_salary=wage)
        elif staffing_action == 5 and can_hire:  # Hire high wage worker
            wage = preferred_wage if preferred_wage and preferred_wage > 0.60 else 0.80
            self._hire_employee(is_manager=False, custom_salary=wage)
        
        # Handle layout swaps
        pos1_idx, pos2_idx = action['layout_swap']
        pos1 = (pos1_idx % self.grid_width, pos1_idx // self.grid_width)
        pos2 = (pos2_idx % self.grid_width, pos2_idx // self.grid_width)
        
        if pos1 != pos2 and self._is_valid_swap(pos1, pos2):
            # Find a manager to coordinate the swap
            manager = self._get_manager()
            if manager and manager.state == EmployeeState.IDLE:
                # Track the relocation start
                item1 = self.warehouse_grid.get_item_at_position(pos1[0], pos1[1])
                item2 = self.warehouse_grid.get_item_at_position(pos2[0], pos2[1])
                
                if item1 is not None:
                    self.relocations_history.append({
                        'item_type': item1,
                        'from_pos': pos1,
                        'to_pos': pos2,
                        'timestep': self.current_timestep,
                        'status': 'started',
                        'manager_id': manager.id
                    })
                
                manager.set_relocation_task(pos1, pos2, self.warehouse_grid)
                
                # Track swap for analytics
                self.last_swap_info = {
                    'source_item': item1,
                    'target_item': item2,
                    'source_pos': pos1,
                    'target_pos': pos2,
                    'manager_id': manager.id
                }
        
        # Handle order assignments
        order_assignments = action['order_assignments']
        orders = self.order_queue.orders[:len(order_assignments)]
        
        # Track which orders are already assigned to employees
        currently_assigned_orders = {emp.current_order_id for emp in self.employees if emp.current_order_id is not None}
        
        for i, employee_idx in enumerate(order_assignments):
            if i < len(orders) and employee_idx > 0 and (employee_idx - 1) < len(self.employees):  # 0 means no assignment
                employee = self.employees[employee_idx - 1]  # -1 because action uses 1-based indexing
                order = orders[i]
                # Only assign if employee is idle, not a manager, and order is not already claimed
                if (employee.state == EmployeeState.IDLE and 
                    not employee.is_manager and 
                    order.status == "pending"):
                    if employee.set_order(order.id, order.items):
                        # Mark order as claimed
                        order.claim()
                        # Assign employee to collect first item
                        self._assign_employee_to_order(employee, order)
                        currently_assigned_orders.add(order.id)  # Mark as assigned
        
        return reward
    
    def _simulate_timestep(self) -> float:
        timestep_reward = 0.0
        
        # Generate new orders with queue pressure feedback
        queue_length = len(self.order_queue.orders)
        num_employees = len(self.employees)
        new_orders = self.order_generator.generate_orders(self.current_timestep, queue_length, num_employees)
        for order in new_orders:
            self.order_queue.add_order(order)
        
        # Update employees with improved collision system
        # Share global traffic zones between all agents
        global_traffic_zones = set()
        for emp in self.employees:
            global_traffic_zones.update(emp.traffic_jam_zones)
        
        for employee in self.employees:
            # Share global traffic information
            employee.global_traffic_zones = global_traffic_zones
            
            # Add other employees' positions (not including current employee)
            other_positions = {emp.position for emp in self.employees if emp != employee}
            action_result = employee.step(self.warehouse_grid, other_positions)
            
            # Apply collision penalty
            if action_result['collision']:
                timestep_reward -= 0.05  # Small penalty for collisions
            
            # Track completed relocations
            if action_result.get('completed_relocation', False):
                # Mark the most recent relocation for this manager as completed
                for relocation in reversed(self.relocations_history):
                    if (relocation.get('manager_id') == employee.id and 
                        relocation['status'] == 'started'):
                        relocation['status'] = 'completed'
                        relocation['completed_timestep'] = self.current_timestep
                        # Relocation completed silently
                        break
            
            # Handle completed deliveries
            if action_result['delivered_items']:
                # Get the order ID from the action result
                completed_order_id = action_result.get('completed_order_id')
                
                if completed_order_id:
                    # Find the order that was just completed
                    order_to_complete = None
                    for order in self.order_queue.orders + self.order_queue.completed_orders:
                        if order.id == completed_order_id:
                            order_to_complete = order
                            break
                    
                    if order_to_complete:
                        # Mark order as delivered
                        order_to_complete.deliver()
                        
                        # Remove from active orders if it's there
                        if order_to_complete in self.order_queue.orders:
                            self.order_queue.orders.remove(order_to_complete)
                        
                        # Complete the order
                        revenue = self.order_queue.complete_order(order_to_complete, self.current_timestep)
                        self.total_revenue += revenue
                        timestep_reward += revenue
                        
                        # Update item co-occurrence
                        self.warehouse_grid.update_item_cooccurrence(order_to_complete.items)
                        
                        # Clear any other employees who might have the same order ID
                        for other_emp in self.employees:
                            if other_emp != employee and other_emp.current_order_id == completed_order_id:
                                # Clear stale order assignment
                                other_emp.current_order_id = None
                                other_emp.order_items = []
                                other_emp.items_collected = []
                                other_emp.target_position = None
                                other_emp.path = []
                                other_emp.state = EmployeeState.IDLE
        
        # Automatically assign idle employees to unclaimed orders
        self._auto_assign_idle_employees()
        
        # Cancel expired orders
        expired_orders = self.order_queue.cancel_expired_orders(self.current_timestep)
        
        # Update customer satisfaction every 20 timesteps (more responsive)
        if self.current_timestep % 20 == 0:
            queue_stats = self.order_queue.get_statistics()
            completion_rate = queue_stats['completion_rate']
            self.order_generator.update_customer_satisfaction(completion_rate, self.current_timestep)
        
        # Calculate costs - sum actual employee salaries
        timestep_cost = sum(emp.salary_per_timestep for emp in self.employees)
        self.total_costs += timestep_cost
        timestep_reward -= timestep_cost
        
        # Update cumulative profit
        self.cumulative_profit += timestep_reward
        
        self.current_timestep += 1
        
        return timestep_reward
    
    def _hire_employee(self, is_manager: bool = False, custom_salary: float = None):
        spawn_position = self.warehouse_grid.spawn_zones[len(self.employees) % len(self.warehouse_grid.spawn_zones)]
        if custom_salary is not None:
            salary = custom_salary
        else:
            salary = 1.0 if is_manager else self.employee_salary  # Managers cost $1 per timestep
        employee = Employee(self.next_employee_id, spawn_position, salary, is_manager)
        self.employees.append(employee)
        self.next_employee_id += 1
    
    def _fire_employee(self):
        if self.employees:
            # Fire the first idle employee, or the last employee if none are idle
            idle_employees = [emp for emp in self.employees if emp.state == EmployeeState.IDLE]
            if idle_employees:
                self.employees.remove(idle_employees[0])
            else:
                self.employees.pop()
    
    def _get_idle_employee(self) -> Optional[Employee]:
        for employee in self.employees:
            if employee.state == EmployeeState.IDLE and not employee.is_manager:
                return employee
        return None
    
    def _get_manager(self) -> Optional[Employee]:
        for employee in self.employees:
            if employee.is_manager:
                return employee
        return None
    
    def _is_valid_swap(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> bool:
        x1, y1 = pos1
        x2, y2 = pos2
        
        if not (self.warehouse_grid.is_valid_position(x1, y1) and 
                self.warehouse_grid.is_valid_position(x2, y2)):
            return False
        
        from .warehouse_grid import CellType
        return (self.warehouse_grid.cell_types[y1, x1] == CellType.STORAGE.value and
                self.warehouse_grid.cell_types[y2, x2] == CellType.STORAGE.value)
    
    def _assign_employee_to_order(self, employee: Employee, order: Order):
        # Find the closest item needed for this order
        closest_item = None
        closest_distance = float('inf')
        
        for item_type in order.items:
            item_locations = self.warehouse_grid.find_item_locations(item_type)
            for location in item_locations:
                distance = self.warehouse_grid.manhattan_distance(employee.position, location)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_item = location
        
        if closest_item:
            # Find a walkable adjacent position to the item
            target_position = self._find_walkable_adjacent_position(closest_item)
            if target_position:
                employee.calculate_path_to_target(self.warehouse_grid, target_position)
            else:
                # If no adjacent walkable position, try the item location itself
                employee.calculate_path_to_target(self.warehouse_grid, closest_item)
    
    def _find_walkable_adjacent_position(self, item_position: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Find a walkable position adjacent to an item location"""
        x, y = item_position
        
        # Check all 4 adjacent positions
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            adj_x, adj_y = x + dx, y + dy
            if self.warehouse_grid.is_walkable(adj_x, adj_y):
                return (adj_x, adj_y)
        
        return None
    
    def _auto_assign_idle_employees(self):
        """Automatically assign idle workers (not managers) to pending orders"""
        # Workers can become idle *inside* a step. Let a registered pickup
        # policy match them at this point instead of silently using value-only
        # fallback before the agent gets another decision. Defaults unchanged.
        if callable(self.order_assignment_policy):
            assignments = self.order_assignment_policy()
            for i, employee_idx in enumerate(assignments):
                if i >= len(self.order_queue.orders):
                    break
                if not (0 < employee_idx <= len(self.employees)):
                    continue
                employee = self.employees[employee_idx-1]
                order = self.order_queue.orders[i]
                if (employee.state == EmployeeState.IDLE and not employee.is_manager
                        and employee.current_order_id is None and order.status == 'pending'):
                    if employee.set_order(order.id, order.items):
                        order.claim()
                        self._assign_employee_to_order(employee, order)
            return
        idle_employees = [emp for emp in self.employees if emp.state == EmployeeState.IDLE and not emp.is_manager]
        pending_orders = [order for order in self.order_queue.orders if order.status == "pending"]
        
        # Sort orders by value (highest value first) and arrival time (oldest first)
        pending_orders.sort(key=lambda o: (-o.value, o.arrival_time))
        
        for employee in idle_employees:
            if pending_orders:
                order = pending_orders.pop(0)  # Take highest priority order
                if employee.set_order(order.id, order.items):
                    order.claim()
                    self._assign_employee_to_order(employee, order)
    
    def _get_observation(self) -> Dict:
        # Warehouse grid observation
        warehouse_obs = self.warehouse_grid.item_grid.copy()
        
        # Item access frequency
        item_freq = self.warehouse_grid.item_access_frequency.copy()
        
        # Order queue observation (pad/truncate to fixed size)
        queue_obs = np.zeros((20, 4))
        queue_state = self.order_queue.get_queue_state(self.current_timestep)
        for i, order_info in enumerate(queue_state[:20]):
            queue_obs[i] = [
                order_info['num_items'],
                order_info['value'],
                order_info['time_remaining'],
                self.current_timestep - order_info['arrival_time']
            ]
        
        # Employee observations
        employee_obs = np.zeros((self.max_employees, 6))
        for i, employee in enumerate(self.employees[:self.max_employees]):
            target_distance = 0
            if employee.target_position:
                target_distance = self.warehouse_grid.manhattan_distance(
                    employee.position, employee.target_position
                )
            
            employee_obs[i] = [
                employee.position[0],
                employee.position[1],
                employee.state.value,
                1 if employee.current_order_id else 0,
                len(employee.items_collected),
                target_distance
            ]
        
        # Financial state
        burn_rate = sum(emp.salary_per_timestep for emp in self.employees)
        financial_obs = np.array([
            self.cumulative_profit,
            self.total_revenue,
            self.total_costs,
            burn_rate
        ])
        
        # Time
        time_obs = np.array([self.current_timestep])
        
        return {
            'warehouse_grid': warehouse_obs.astype(np.int32),
            'item_access_frequency': item_freq.astype(np.float32),
            'order_queue': queue_obs.astype(np.float32),
            'employees': employee_obs.astype(np.float32),
            'financial': financial_obs.astype(np.float32),
            'time': time_obs.astype(np.int32)
        }
    
    def _get_info(self) -> Dict:
        queue_stats = self.order_queue.get_statistics()
        
        return {
            'timestep': self.current_timestep,
            'profit': self.cumulative_profit,
            'revenue': self.total_revenue,
            'costs': self.total_costs,
            'num_employees': len(self.employees),
            'queue_length': len(self.order_queue.orders),
            'orders_completed': queue_stats['completed_orders'],
            'orders_cancelled': queue_stats['cancelled_orders'],
            'completion_rate': queue_stats['completion_rate']
        }
    
    def render(self):
        if self.render_mode == "human" and self.renderer:
            return self.renderer.render()
        elif self.render_mode == "rgb_array" and self.renderer:
            return self.renderer.get_rgb_array()
        else:
            # Text-based rendering fallback
            print(f"Timestep: {self.current_timestep}")
            print(f"Profit: ${self.cumulative_profit:.2f}")
            print(f"Employees: {len(self.employees)}")
            print(f"Orders in queue: {len(self.order_queue.orders)}")
            print("-" * 40)
    
    def close(self):
        if self.renderer:
            self.renderer.close()
