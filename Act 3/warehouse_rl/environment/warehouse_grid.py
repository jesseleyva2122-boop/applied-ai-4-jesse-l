import numpy as np
from typing import Tuple, List, Optional
from enum import Enum

class CellType(Enum):
    EMPTY = 0
    STORAGE = 1
    PACKING_STATION = 2
    SPAWN_ZONE = 3
    TEMP_STORAGE = 4  # Temporary storage bank for item shifting

class WarehouseGrid:
    def __init__(self, width: int = 30, height: int = 30, num_item_types: int = 50):
        self.width = width
        self.height = height
        self.num_item_types = num_item_types
        
        # Grid showing cell types
        self.cell_types = np.zeros((height, width), dtype=int)
        
        # Grid showing which item type is stored at each location (-1 for no item)
        self.item_grid = np.full((height, width), -1, dtype=int)
        
        # Track access frequency for each item type
        self.item_access_frequency = np.zeros(num_item_types)
        
        # Track item co-occurrence matrix
        self.item_cooccurrence = np.zeros((num_item_types, num_item_types))
        
        # Initialize the warehouse layout
        self._initialize_layout()
    
    def _initialize_layout(self):
        # Simple truck bay: 4 packing stations on the right edge
        truck_bay_x = self.width - 1
        truck_bay_positions = []
        
        # Create 4 packing stations vertically in the middle-right
        mid_y = self.height // 2
        for y in [mid_y - 2, mid_y - 1, mid_y, mid_y + 1]:
            if 0 <= y < self.height:
                self.cell_types[y, truck_bay_x] = CellType.PACKING_STATION.value
                truck_bay_positions.append((truck_bay_x, y))
        
        # Store positions
        self.packing_station = truck_bay_positions[0] if truck_bay_positions else (truck_bay_x, mid_y)
        self.truck_bay_positions = truck_bay_positions
        # Created packing stations silently
        
        # Set spawn zones (corners)
        spawn_positions = [
            (2, 2), (self.width - 3, 2), 
            (2, self.height - 3), (self.width - 3, self.height - 3)
        ]
        self.spawn_zones = []
        for x, y in spawn_positions:
            self.cell_types[y, x] = CellType.SPAWN_ZONE.value
            self.spawn_zones.append((x, y))
        
        # Create main corridors (2-wide)
        self._create_main_corridors()
        
        # Create temporary storage bank (near packing station)
        self._create_temp_storage_bank()
        
        # Create storage blocks with items
        self._create_storage_blocks()
        
        # Ensure connectivity
        self._ensure_connectivity()
    
    def _create_main_corridors(self):
        """Create 2-wide main corridors for navigation"""
        mid_x, mid_y = self.width // 2, self.height // 2
        
        # Main horizontal corridor - 2 cells wide
        for corridor_offset in [-1, 0]:  # Two rows for horizontal corridor  
            y = mid_y + corridor_offset
            if 0 <= y < self.height:
                for x in range(self.width - 1):  # Stop before truck bay
                    if (self.is_valid_position(x, y) and 
                        self.cell_types[y, x] not in [CellType.PACKING_STATION.value, CellType.SPAWN_ZONE.value]):
                        self.cell_types[y, x] = CellType.EMPTY.value
        
        # Main vertical corridor - 2 cells wide
        for corridor_offset in [-1, 0]:  # Two columns for vertical corridor
            x = mid_x + corridor_offset
            if 0 <= x < self.width - 1:  # Stop before truck bay column
                for y in range(self.height):
                    if (self.is_valid_position(x, y) and 
                        self.cell_types[y, x] not in [CellType.PACKING_STATION.value, CellType.SPAWN_ZONE.value]):
                        self.cell_types[y, x] = CellType.EMPTY.value
        
        # Connect spawn zones to main corridors
        for spawn_x, spawn_y in self.spawn_zones:
            # Horizontal connection to vertical corridor
            start_x, end_x = min(spawn_x, mid_x), max(spawn_x, mid_x)
            for x in range(start_x, end_x + 1):
                if (self.is_valid_position(x, spawn_y) and 
                    self.cell_types[spawn_y, x] not in [CellType.PACKING_STATION.value, CellType.SPAWN_ZONE.value]):
                    self.cell_types[spawn_y, x] = CellType.EMPTY.value
            
            # Vertical connection to horizontal corridor  
            start_y, end_y = min(spawn_y, mid_y), max(spawn_y, mid_y)
            for y in range(start_y, end_y + 1):
                if (self.is_valid_position(spawn_x, y) and 
                    self.cell_types[y, spawn_x] not in [CellType.PACKING_STATION.value, CellType.SPAWN_ZONE.value]):
                    self.cell_types[y, spawn_x] = CellType.EMPTY.value
    
    
    
    def _create_temp_storage_bank(self):
        """Create a temporary storage bank near the truck bay"""
        truck_bay_x = self.width - 1
        truck_bay_y = self.height // 2
        
        # Create temporary storage area to the left of truck bay (near delivery point)
        temp_storage_positions = []
        for dy in [-1, 0, 1]:  # 3 rows
            for dx in [-3, -2]:  # 2 columns, offset left from truck bay
                x, y = truck_bay_x + dx, truck_bay_y + dy
                if (self.is_valid_position(x, y) and 
                    self.cell_types[y, x] == CellType.EMPTY.value):
                    self.cell_types[y, x] = CellType.TEMP_STORAGE.value
                    self.item_grid[y, x] = -1  # Start empty
                    temp_storage_positions.append((x, y))
        
        self.temp_storage_positions = temp_storage_positions
    
    
    def is_truck_bay_position(self, position: Tuple[int, int]) -> bool:
        """Check if position is any truck bay delivery point"""
        return position in self.truck_bay_positions
    
    def get_nearest_truck_bay_position(self, from_position: Tuple[int, int]) -> Tuple[int, int]:
        """Get the nearest truck bay position from a given position"""
        min_distance = float('inf')
        nearest_bay = self.truck_bay_positions[0]
        
        for bay_pos in self.truck_bay_positions:
            distance = self.manhattan_distance(from_position, bay_pos)
            if distance < min_distance:
                min_distance = distance
                nearest_bay = bay_pos
        
        return nearest_bay
    
    def _create_storage_blocks(self):
        """Create a simple fixed warehouse layout with 25 2x2 storage blocks"""
        storage_positions = []
        empty_storage_positions = []
        
        # Fixed layout: 25 storage blocks (2x2 each) following exact pattern:
        # ########################
        # #......................#
        # #..S..SS..SS..SS..SS..#
        # #..S..SS..SS..SS..SS..#
        # #......................#
        # #......................#
        # #..S..SS..SS..SS..SS..#
        # #..S..SS..SS..SS..SS..#
        # (etc. for 5 rows of 5 blocks)
        
        # 25 storage blocks (2x2 each) positioned with exact spacing pattern
        block_positions = [
            # Row 1 (y=2): 5 blocks spaced as: ..S..SS..SS..SS..SS
            (2, 2),   (5, 2),   (8, 2),   (11, 2),  (14, 2),
            # Row 2 (y=6): Same x positions
            (2, 6),   (5, 6),   (8, 6),   (11, 6),  (14, 6),
            # Row 3 (y=10): Same x positions  
            (2, 10),  (5, 10),  (8, 10),  (11, 10), (14, 10),
            # Row 4 (y=14): Same x positions
            (2, 14),  (5, 14),  (8, 14),  (11, 14), (14, 14),
            # Row 5 (y=18): Same x positions
            (2, 18),  (5, 18),  (8, 18),  (11, 18), (14, 18)
        ]
        
        item_index = 0
        for block_idx, (start_x, start_y) in enumerate(block_positions):
            # Create 2x2 storage block
            for dy in range(2):
                for dx in range(2):
                    x, y = start_x + dx, start_y + dy
                    if self.is_valid_position(x, y):
                        self.cell_types[y, x] = CellType.STORAGE.value
                        storage_positions.append((x, y))
                        
                        # Every 4th storage position is empty for reorganization
                        if len(storage_positions) % 8 == 0:
                            self.item_grid[y, x] = -1
                            empty_storage_positions.append((x, y))
                        else:
                            # Assign item types cyclically
                            item_type = item_index % self.num_item_types
                            self.item_grid[y, x] = item_type
                            item_index += 1
        
        self.storage_positions = storage_positions
        self.empty_storage_positions = empty_storage_positions
        # Created storage positions silently
    
    def _ensure_connectivity(self):
        """Ensure all walkable spaces are connected using flood fill"""
        # Find all walkable positions
        walkable_positions = set()
        for y in range(self.height):
            for x in range(self.width):
                if self.is_walkable(x, y):
                    walkable_positions.add((x, y))
        
        if not walkable_positions:
            return
        
        # Start flood fill from packing station (guaranteed walkable)
        visited = set()
        queue = [self.packing_station]
        visited.add(self.packing_station)
        
        # Flood fill to find all connected walkable spaces
        while queue:
            current_x, current_y = queue.pop(0)
            
            # Check all 4 neighbors
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = current_x + dx, current_y + dy
                neighbor_pos = (nx, ny)
                
                if (neighbor_pos in walkable_positions and 
                    neighbor_pos not in visited):
                    visited.add(neighbor_pos)
                    queue.append(neighbor_pos)
        
        # Find unreachable walkable positions
        unreachable = walkable_positions - visited
        
        # For each unreachable position, create a path to the main network
        for unreachable_x, unreachable_y in unreachable:
            self._connect_isolated_space(unreachable_x, unreachable_y, visited)
            visited.add((unreachable_x, unreachable_y))
    
    def _connect_isolated_space(self, x: int, y: int, connected_spaces: set):
        """Connect an isolated walkable space to the main network"""
        # Find the closest connected space
        min_distance = float('inf')
        closest_connected = None
        
        for conn_x, conn_y in connected_spaces:
            distance = self.manhattan_distance((x, y), (conn_x, conn_y))
            if distance < min_distance:
                min_distance = distance
                closest_connected = (conn_x, conn_y)
        
        if closest_connected is None:
            return
        
        # Create a path from isolated space to closest connected space
        current_x, current_y = x, y
        target_x, target_y = closest_connected
        
        # Simple pathfinding: move toward target, clearing obstacles
        while (current_x, current_y) != (target_x, target_y):
            # Move one step closer to target
            if current_x < target_x:
                next_x, next_y = current_x + 1, current_y
            elif current_x > target_x:
                next_x, next_y = current_x - 1, current_y
            elif current_y < target_y:
                next_x, next_y = current_x, current_y + 1
            else:
                next_x, next_y = current_x, current_y - 1
            
            # Clear the path by making it walkable
            if self.is_valid_position(next_x, next_y):
                if self.cell_types[next_y, next_x] == CellType.STORAGE.value:
                    # Convert storage to empty corridor
                    self.cell_types[next_y, next_x] = CellType.EMPTY.value
                    self.item_grid[next_y, next_x] = -1
                elif (self.cell_types[next_y, next_x] != CellType.PACKING_STATION.value and 
                      self.cell_types[next_y, next_x] != CellType.SPAWN_ZONE.value):
                    # Make sure it's walkable
                    self.cell_types[next_y, next_x] = CellType.EMPTY.value
                
                current_x, current_y = next_x, next_y
            else:
                break
    
    def get_item_at_position(self, x: int, y: int) -> Optional[int]:
        if not self.is_valid_position(x, y):
            return None
        return self.item_grid[y, x] if self.item_grid[y, x] != -1 else None
    
    def set_item_at_position(self, x: int, y: int, item_type: int):
        if not self.is_valid_position(x, y):
            print(f"WARNING: set_item_at_position failed - invalid position ({x}, {y})")
            return False
        
        # Check if the target position is a storage cell (required for placing items)
        if self.cell_types[y, x] != CellType.STORAGE.value:
            print(f"WARNING: set_item_at_position failed - position ({x}, {y}) is not storage (type: {self.cell_types[y, x]})")
            return False
        
        # Place the item in the storage cell
        self.item_grid[y, x] = item_type
        # Item placement successful (debug silenced)
        return True
    
    def pick_item_at_position(self, x: int, y: int) -> Optional[int]:
        """Pick an item from inventory (item remains, this just returns the type)"""
        if not self.is_valid_position(x, y):
            return None
        item = self.item_grid[y, x]
        # Items stay in place - this represents picking from stock, not removing the stock
        return item if item != -1 else None
    
    def remove_item_at_position(self, x: int, y: int) -> Optional[int]:
        """Remove item (for relocation tasks only)"""
        if not self.is_valid_position(x, y):
            return None
        item = self.item_grid[y, x]
        self.item_grid[y, x] = -1
        return item if item != -1 else None
    
    def find_item_locations(self, item_type: int) -> List[Tuple[int, int]]:
        # Equivalent row-major scan, vectorized for repeated routing queries.
        ys, xs = np.where(self.item_grid == item_type)
        return list(zip(xs.tolist(), ys.tolist()))

    def is_valid_position(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a position is walkable by agents"""
        if not self.is_valid_position(x, y):
            return False
        cell_type = self.cell_types[y, x]
        
        # Storage locations are NEVER walkable - agents cannot pass through them
        if cell_type == CellType.STORAGE.value:
            return False
        
        # Temp storage is walkable only if empty
        elif cell_type == CellType.TEMP_STORAGE.value:
            return self.item_grid[y, x] == -1
        
        # EMPTY, PACKING_STATION, and SPAWN_ZONE are always walkable
        return cell_type in [CellType.EMPTY.value, CellType.PACKING_STATION.value, CellType.SPAWN_ZONE.value]
    
    def can_access_storage(self, x: int, y: int) -> bool:
        """Check if an agent can access a storage location for pickup/swap operations"""
        if not self.is_valid_position(x, y):
            return False
        
        # Must be a storage location
        if self.cell_types[y, x] != CellType.STORAGE.value:
            return False
        
        # Check if there's at least one adjacent walkable cell
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            adj_x, adj_y = x + dx, y + dy
            if self.is_walkable(adj_x, adj_y):
                return True
        
        return False
    
    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        neighbors = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                neighbors.append((nx, ny))
        return neighbors
    
    def manhattan_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    def update_item_access(self, item_type: int):
        self.item_access_frequency[item_type] += 1
    
    def update_item_cooccurrence(self, item_types: List[int]):
        for i, item1 in enumerate(item_types):
            for item2 in item_types[i+1:]:
                self.item_cooccurrence[item1, item2] += 1
                self.item_cooccurrence[item2, item1] += 1
    
    def swap_items(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> bool:
        x1, y1 = pos1
        x2, y2 = pos2
        
        if not (self.is_valid_position(x1, y1) and self.is_valid_position(x2, y2)):
            return False
        
        if not (self.cell_types[y1, x1] == CellType.STORAGE.value and 
                self.cell_types[y2, x2] == CellType.STORAGE.value):
            return False
        
        # Swap the items
        item1 = self.item_grid[y1, x1]
        item2 = self.item_grid[y2, x2]
        self.item_grid[y1, x1] = item2
        self.item_grid[y2, x2] = item1
        
        return True
    
    def get_state(self) -> dict:
        return {
            'cell_types': self.cell_types.copy(),
            'item_grid': self.item_grid.copy(),
            'item_access_frequency': self.item_access_frequency.copy(),
            'item_cooccurrence': self.item_cooccurrence.copy(),
            'packing_station': self.packing_station,
            'spawn_zones': self.spawn_zones.copy()
        }