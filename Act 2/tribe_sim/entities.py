import pygame
import random
import math
from config import *

def get_central_spawn_position():
    """Generate a random spawn position within the central spawn zone"""
    # Generate random position within circle
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, SPAWN_ZONE_RADIUS)
    
    x = SPAWN_ZONE_CENTER_X + math.cos(angle) * distance
    y = SPAWN_ZONE_CENTER_Y + math.sin(angle) * distance
    
    # Ensure position is within simulation bounds
    x = max(GATHERER_RADIUS, min(SIMULATION_WIDTH - GATHERER_RADIUS, x))
    y = max(GATHERER_RADIUS, min(SIMULATION_HEIGHT - GATHERER_RADIUS, y))
    
    return x, y

class Gatherer:
    def __init__(self, x=None, y=None, genes=None):
        if x is None or y is None:
            self.x, self.y = get_central_spawn_position()
        else:
            self.x, self.y = x, y
        self.energy = GATHERER_START_ENERGY
        self.age = 0
        self.alive = True
        self.food_collected = 0
        self.death_timer = 0
        self.interaction_cooldown = 0
        self.tribe_name = "ga"
        
        # Initialize genes
        if genes is None:
            self.genes = {
                'speed': random.uniform(*GENE_RANGES['speed']),
                'caution': random.uniform(*GENE_RANGES['caution']),
                'search_pattern': random.uniform(*GENE_RANGES['search_pattern']),
                'efficiency': random.uniform(*GENE_RANGES['efficiency']),
                'cooperation': random.uniform(*GENE_RANGES['cooperation'])
            }
        else:
            self.genes = genes.copy()
        
        # Movement state
        self.target_x = self.x
        self.target_y = self.y
        self.search_grid_x = 0
        self.search_grid_y = 0
        self.trail = []
        
    def update(self, predators, food_items):
        if not self.alive:
            if self.death_timer < 10:
                self.death_timer += 1
            return
        
        # Decrement interaction cooldown
        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= 1
            
        self.age += 1
        
        # Energy decay
        self.energy -= ENERGY_DECAY_RATE * self.genes['efficiency']
        if self.energy <= 0:
            self.alive = False
            return
        
        # Check for nearby predators
        fleeing = False
        for predator in predators:
            distance = math.sqrt((self.x - predator.x)**2 + (self.y - predator.y)**2)
            if distance < self.genes['caution']:
                # Flee from predator
                flee_x = self.x - predator.x
                flee_y = self.y - predator.y
                if flee_x != 0 or flee_y != 0:
                    flee_length = math.sqrt(flee_x**2 + flee_y**2)
                    flee_x /= flee_length
                    flee_y /= flee_length
                    self.x += flee_x * self.genes['speed']
                    self.y += flee_y * self.genes['speed']
                    fleeing = True
                    break
        
        if not fleeing:
            # Move towards food or explore
            nearest_food = self.find_nearest_food(food_items)
            if nearest_food:
                # Move towards nearest food
                dx = nearest_food.x - self.x
                dy = nearest_food.y - self.y
                distance = math.sqrt(dx**2 + dy**2)
                if distance > 0:
                    dx /= distance
                    dy /= distance
                    self.x += dx * self.genes['speed']
                    self.y += dy * self.genes['speed']
            else:
                # Explore using search pattern
                self.explore()
        
        # Keep within bounds
        self.x = max(GATHERER_RADIUS, min(SIMULATION_WIDTH - GATHERER_RADIUS, self.x))
        self.y = max(GATHERER_RADIUS, min(SIMULATION_HEIGHT - GATHERER_RADIUS, self.y))
        
        # Update trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)
    
    def find_nearest_food(self, food_items):
        if not food_items:
            return None
        
        nearest = None
        min_distance = float('inf')
        
        for food in food_items:
            distance = math.sqrt((self.x - food.x)**2 + (self.y - food.y)**2)
            if distance < min_distance:
                min_distance = distance
                nearest = food
        
        return nearest
    
    def explore(self):
        # Blend between random walk and systematic search
        random_component = 1 - self.genes['search_pattern']
        systematic_component = self.genes['search_pattern']
        
        if random.random() < random_component:
            # Random walk
            angle = random.uniform(0, 2 * math.pi)
            self.x += math.cos(angle) * self.genes['speed']
            self.y += math.sin(angle) * self.genes['speed']
        else:
            # Systematic grid search
            grid_size = 50
            target_x = (self.search_grid_x * grid_size) % SIMULATION_WIDTH
            target_y = (self.search_grid_y * grid_size) % SIMULATION_HEIGHT
            
            dx = target_x - self.x
            dy = target_y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance < 20:  # Reached target
                self.search_grid_x += 1
                if self.search_grid_x * grid_size >= SIMULATION_WIDTH:
                    self.search_grid_x = 0
                    self.search_grid_y += 1
                if self.search_grid_y * grid_size >= SIMULATION_HEIGHT:
                    self.search_grid_y = 0
            else:
                dx /= distance
                dy /= distance
                self.x += dx * self.genes['speed']
                self.y += dy * self.genes['speed']
    
    def collect_food(self, food):
        self.energy = min(GATHERER_MAX_ENERGY, self.energy + FOOD_ENERGY_VALUE)
        self.food_collected += 1
    
    def collect_fractional_food(self, food, portion):
        """Collect a fractional amount of food based on sharing"""
        energy_gain = FOOD_ENERGY_VALUE * portion
        self.energy = min(GATHERER_MAX_ENERGY, self.energy + energy_gain)
        self.food_collected += portion
    
    def calculate_fitness(self):
        # STUDENT ASSIGNMENT 1: Implement a better fitness function
        # Current version only considers survival time - very basic!
        #
        # Available variables to consider:
        # - self.age: how long this gatherer has survived
        # - self.food_collected: total food gathered
        # - self.energy: current energy level (0-100)
        # - self.alive: whether still alive
        # - self.genes: dict with 'speed', 'caution', 'search_pattern', 'efficiency', 'cooperation'
        #
        # Strategy hints:
        # 1. Balance survival vs resource gathering (both matter!)
        # 2. Consider rewarding efficient gatherers (more food per time alive)
        # 3. Maybe penalize overly cautious gatherers who survive but gather little?
        # 4. Could reward cooperation or punish antisocial behavior
        # 5. Think about edge cases: dead vs alive, high energy vs low energy
        #
        # Remember: Higher fitness = more likely to reproduce!
        
        # Balance survival, resource gathering, remaining energy, and gathering efficiency.
        survival_score = self.age / 100.0
        food_score = self.food_collected * 2.0
        energy_score = max(0.0, self.energy) / GATHERER_MAX_ENERGY
        food_rate = self.food_collected / max(1, self.age) * 100.0
        alive_bonus = 1.0 if self.alive else 0.0

        # Food is weighted strongly so agents cannot score well by only hiding.
        # Survival and remaining energy still reward agents that avoid predators.
        fitness = (
            0.35 * survival_score
            + 0.35 * food_score
            + 0.15 * energy_score
            + 0.10 * food_rate
            + 0.05 * alive_bonus
        )
        return max(0.0, fitness)
    
    def take_damage(self):
        """Handle death/life loss"""
        self.alive = False
    
    def get_color(self):
        if not self.alive:
            alpha = max(0, 255 - (self.death_timer * 25))
            return (*COLORS['gatherer_low'], alpha)
        
        fitness = self.calculate_fitness()
        if fitness < 0.5:
            # Red to Yellow
            ratio = fitness / 0.5
            r = 255
            g = int(255 * ratio)
            b = 0
        else:
            # Yellow to Green
            ratio = min(1.0, (fitness - 0.5) / 0.5)
            r = int(255 * (1 - ratio))
            g = 255
            b = 0
        
        return (r, g, b)

class Predator:
    def __init__(self, x=None, y=None):
        self.x = x if x is not None else random.uniform(0, SIMULATION_WIDTH)
        self.y = y if y is not None else random.uniform(0, SIMULATION_HEIGHT)
        self.target_x = self.x
        self.target_y = self.y
        self.hunting = False
        self.hunt_target = None
        self.hunting_cooldown = 0
        
    def update(self, gatherers):
        # Update cooldown timer
        if self.hunting_cooldown > 0:
            self.hunting_cooldown -= 1
            return  # Don't move during cooldown
        
        # Find nearest gatherer within hunt radius
        self.hunting = False
        self.hunt_target = None
        min_distance = PREDATOR_HUNT_RADIUS
        
        for gatherer in gatherers:
            if gatherer.alive:
                distance = math.sqrt((self.x - gatherer.x)**2 + (self.y - gatherer.y)**2)
                if distance < min_distance:
                    min_distance = distance
                    self.hunt_target = gatherer
                    self.hunting = True
        
        if self.hunting and self.hunt_target:
            # Chase the target
            dx = self.hunt_target.x - self.x
            dy = self.hunt_target.y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            if distance > 0:
                dx /= distance
                dy /= distance
                self.x += dx * PREDATOR_SPEED
                self.y += dy * PREDATOR_SPEED
        else:
            # Wander randomly
            if abs(self.x - self.target_x) < 5 and abs(self.y - self.target_y) < 5:
                self.target_x = random.uniform(0, SIMULATION_WIDTH)
                self.target_y = random.uniform(0, SIMULATION_HEIGHT)
            
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            if distance > 0:
                dx /= distance
                dy /= distance
                self.x += dx * (PREDATOR_SPEED * 0.5)  # Slower when wandering
                self.y += dy * (PREDATOR_SPEED * 0.5)
        
        # Keep within bounds
        self.x = max(PREDATOR_SIZE, min(SIMULATION_WIDTH - PREDATOR_SIZE, self.x))
        self.y = max(PREDATOR_SIZE, min(SIMULATION_HEIGHT - PREDATOR_SIZE, self.y))
    
    def check_kills(self, all_tribes):
        if self.hunting_cooldown > 0:
            return
            
        for tribe_list in all_tribes:
            for member in tribe_list:
                if member.alive:
                    distance = math.sqrt((self.x - member.x)**2 + (self.y - member.y)**2)
                    if distance < PREDATOR_SIZE + GATHERER_RADIUS:
                        # Handle ninja special ability
                        if hasattr(member, 'take_damage'):
                            member.take_damage()
                        else:
                            member.alive = False
                        
                        # Set hunting cooldown after inflicting damage
                        self.hunting_cooldown = PREDATOR_HUNTING_COOLDOWN
                        return  # Only damage one target per frame

class NinjaTribe:
    def __init__(self, x=None, y=None):
        if x is None or y is None:
            self.x, self.y = get_central_spawn_position()
        else:
            self.x, self.y = x, y
        self.energy = GATHERER_START_ENERGY
        self.age = 0
        self.alive = True
        self.food_collected = 0
        self.death_timer = 0
        self.lives = 3  # Special ability: 3 lives
        self.interaction_cooldown = 0
        self.invulnerable_frames = 0
        
        # Hardcoded genes (base stats)
        self.genes = {
            'speed': 1.5,  # Base speed
            'caution': 50,  # Normal caution
            'search_pattern': 0.5,  # Balanced search
            'efficiency': 1.0  # Normal efficiency
        }
        
        # Movement state
        self.target_x = self.x
        self.target_y = self.y
        self.search_grid_x = 0
        self.search_grid_y = 0
        self.trail = []
        self.tribe_name = "ninja"
    
    def update(self, predators, food_items):
        if not self.alive:
            if self.death_timer < 10:
                self.death_timer += 1
            return
        
        # Decrement interaction cooldown
        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= 1
            
        self.age += 1
        
        # Energy decay
        self.energy -= ENERGY_DECAY_RATE * self.genes['efficiency']
        if self.energy <= 0:
            self.lives -= 1
            if self.lives <= 0:
                self.alive = False
            else:
                # Teleport to central spawn zone and restore energy
                self.x, self.y = get_central_spawn_position()
                self.energy = GATHERER_START_ENERGY
            return
        
        # Same movement logic as Gatherer but with hardcoded genes
        self._move(predators, food_items)
        
        # Update trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)
    
    def _move(self, predators, food_items):
        # Copy movement logic from Gatherer class
        fleeing = False
        for predator in predators:
            distance = math.sqrt((self.x - predator.x)**2 + (self.y - predator.y)**2)
            if distance < self.genes['caution']:
                flee_x = self.x - predator.x
                flee_y = self.y - predator.y
                if flee_x != 0 or flee_y != 0:
                    flee_length = math.sqrt(flee_x**2 + flee_y**2)
                    flee_x /= flee_length
                    flee_y /= flee_length
                    self.x += flee_x * self.genes['speed']
                    self.y += flee_y * self.genes['speed']
                    fleeing = True
                    break
        
        if not fleeing:
            nearest_food = self._find_nearest_food(food_items)
            if nearest_food:
                dx = nearest_food.x - self.x
                dy = nearest_food.y - self.y
                distance = math.sqrt(dx**2 + dy**2)
                if distance > 0:
                    dx /= distance
                    dy /= distance
                    self.x += dx * self.genes['speed']
                    self.y += dy * self.genes['speed']
            else:
                self._explore()
        
        # Keep within bounds
        self.x = max(GATHERER_RADIUS, min(SIMULATION_WIDTH - GATHERER_RADIUS, self.x))
        self.y = max(GATHERER_RADIUS, min(SIMULATION_HEIGHT - GATHERER_RADIUS, self.y))
    
    def _find_nearest_food(self, food_items):
        if not food_items:
            return None
        
        nearest = None
        min_distance = float('inf')
        
        for food in food_items:
            distance = math.sqrt((self.x - food.x)**2 + (self.y - food.y)**2)
            if distance < min_distance:
                min_distance = distance
                nearest = food
        
        return nearest
    
    def _explore(self):
        random_component = 1 - self.genes['search_pattern']
        systematic_component = self.genes['search_pattern']
        
        if random.random() < random_component:
            angle = random.uniform(0, 2 * math.pi)
            self.x += math.cos(angle) * self.genes['speed']
            self.y += math.sin(angle) * self.genes['speed']
        else:
            grid_size = 50
            target_x = (self.search_grid_x * grid_size) % SIMULATION_WIDTH
            target_y = (self.search_grid_y * grid_size) % SIMULATION_HEIGHT
            
            dx = target_x - self.x
            dy = target_y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance < 20:
                self.search_grid_x += 1
                if self.search_grid_x * grid_size >= SIMULATION_WIDTH:
                    self.search_grid_x = 0
                    self.search_grid_y += 1
                if self.search_grid_y * grid_size >= SIMULATION_HEIGHT:
                    self.search_grid_y = 0
            else:
                dx /= distance
                dy /= distance
                self.x += dx * self.genes['speed']
                self.y += dy * self.genes['speed']
    
    def collect_food(self, food):
        self.energy = min(GATHERER_MAX_ENERGY, self.energy + FOOD_ENERGY_VALUE)
        self.food_collected += 1
    
    def collect_fractional_food(self, food, portion):
        """Collect a fractional amount of food based on sharing"""
        energy_gain = FOOD_ENERGY_VALUE * portion
        self.energy = min(GATHERER_MAX_ENERGY, self.energy + energy_gain)
        self.food_collected += portion
    
    def take_damage(self):
        """Handle death/life loss"""
        if self.tribe_name == "ninja" and self.lives > 1:
            self.lives -= 1
            # Visual: flash white for 10 frames
            self.invulnerable_frames = 60
            # Teleport to central spawn zone and restore energy
            self.x, self.y = get_central_spawn_position()
            self.energy = GATHERER_START_ENERGY
        else:
            self.alive = False
    
    def get_color(self):
        """Return color for rendering - includes death animation"""
        if not self.alive:
            alpha = max(0, 255 - (self.death_timer * 25))
            return (255, 255, 255, alpha)  # White fading out
        else:
            return (255, 255, 255)  # White for living ninjas

class RunnerTribe:
    def __init__(self, x=None, y=None):
        if x is None or y is None:
            self.x, self.y = get_central_spawn_position()
        else:
            self.x, self.y = x, y
        self.energy = GATHERER_START_ENERGY
        self.age = 0
        self.alive = True
        self.food_collected = 0
        self.death_timer = 0
        self.interaction_cooldown = 0
        
        # Hardcoded genes - super fast, no caution
        self.genes = {
            'speed': 3.5,  # Faster than predators (2.0)
            'caution': 0,   # No fear of predators
            'search_pattern': 0.2,  # Mostly random search for speed
            'efficiency': 1.2  # Slightly less efficient due to speed
        }
        
        # Movement state
        self.target_x = self.x
        self.target_y = self.y
        self.search_grid_x = 0
        self.search_grid_y = 0
        self.trail = []
        self.tribe_name = "runner"
    
    def update(self, predators, food_items):
        if not self.alive:
            if self.death_timer < 10:
                self.death_timer += 1
            return
        
        # Decrement interaction cooldown
        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= 1
            
        self.age += 1
        
        # Energy decay
        self.energy -= ENERGY_DECAY_RATE * self.genes['efficiency']
        if self.energy <= 0:
            self.alive = False
            return
        
        # Move directly toward food (no predator avoidance)
        self._move_toward_food(food_items)
        
        # Keep within bounds
        self.x = max(GATHERER_RADIUS, min(SIMULATION_WIDTH - GATHERER_RADIUS, self.x))
        self.y = max(GATHERER_RADIUS, min(SIMULATION_HEIGHT - GATHERER_RADIUS, self.y))
        
        # Update trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)
    
    def _move_toward_food(self, food_items):
        nearest_food = self._find_nearest_food(food_items)
        if nearest_food:
            dx = nearest_food.x - self.x
            dy = nearest_food.y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            if distance > 0:
                dx /= distance
                dy /= distance
                self.x += dx * self.genes['speed']
                self.y += dy * self.genes['speed']
        else:
            # Random movement when no food visible
            angle = random.uniform(0, 2 * math.pi)
            self.x += math.cos(angle) * self.genes['speed']
            self.y += math.sin(angle) * self.genes['speed']
    
    def _find_nearest_food(self, food_items):
        if not food_items:
            return None
        
        nearest = None
        min_distance = float('inf')
        
        for food in food_items:
            distance = math.sqrt((self.x - food.x)**2 + (self.y - food.y)**2)
            if distance < min_distance:
                min_distance = distance
                nearest = food
        
        return nearest
    
    def collect_food(self, food):
        self.energy = min(GATHERER_MAX_ENERGY, self.energy + FOOD_ENERGY_VALUE)
        self.food_collected += 1
    
    def collect_fractional_food(self, food, portion):
        """Collect a fractional amount of food based on sharing"""
        energy_gain = FOOD_ENERGY_VALUE * portion
        self.energy = min(GATHERER_MAX_ENERGY, self.energy + energy_gain)
        self.food_collected += portion
    
    def take_damage(self):
        """Handle death/life loss"""
        self.alive = False
    
    def get_color(self):
        """Return color for rendering - includes death animation"""
        if not self.alive:
            alpha = max(0, 255 - (self.death_timer * 25))
            return (255, 255, 255, alpha)  # White fading out
        else:
            return (255, 255, 255)  # White for living runners

class FarmerTribe:
    def __init__(self, x=None, y=None):
        if x is None or y is None:
            self.x, self.y = get_central_spawn_position()
        else:
            self.x, self.y = x, y
        self.energy = GATHERER_START_ENERGY
        self.age = 0
        self.alive = True
        self.food_collected = 0
        self.death_timer = 0
        self.interaction_cooldown = 0
        
        # Hardcoded genes - base speed, gets double food
        self.genes = {
            'speed': 1.5,  # Base speed
            'caution': 75,  # High caution (careful farmers)
            'search_pattern': 0.8,  # Systematic search
            'efficiency': 0.8  # More efficient
        }
        
        # Movement state
        self.target_x = self.x
        self.target_y = self.y
        self.search_grid_x = 0
        self.search_grid_y = 0
        self.trail = []
        self.tribe_name = "farmer"
    
    def update(self, predators, food_items):
        if not self.alive:
            if self.death_timer < 10:
                self.death_timer += 1
            return
        
        # Decrement interaction cooldown
        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= 1
            
        self.age += 1
        
        # Energy decay
        self.energy -= ENERGY_DECAY_RATE * self.genes['efficiency']
        if self.energy <= 0:
            self.alive = False
            return
        
        # Same movement logic as Gatherer but with hardcoded genes
        self._move(predators, food_items)
        
        # Update trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)
    
    def _move(self, predators, food_items):
        # Copy movement logic from Gatherer class
        fleeing = False
        for predator in predators:
            distance = math.sqrt((self.x - predator.x)**2 + (self.y - predator.y)**2)
            if distance < self.genes['caution']:
                flee_x = self.x - predator.x
                flee_y = self.y - predator.y
                if flee_x != 0 or flee_y != 0:
                    flee_length = math.sqrt(flee_x**2 + flee_y**2)
                    flee_x /= flee_length
                    flee_y /= flee_length
                    self.x += flee_x * self.genes['speed']
                    self.y += flee_y * self.genes['speed']
                    fleeing = True
                    break
        
        if not fleeing:
            nearest_food = self._find_nearest_food(food_items)
            if nearest_food:
                dx = nearest_food.x - self.x
                dy = nearest_food.y - self.y
                distance = math.sqrt(dx**2 + dy**2)
                if distance > 0:
                    dx /= distance
                    dy /= distance
                    self.x += dx * self.genes['speed']
                    self.y += dy * self.genes['speed']
            else:
                self._explore()
        
        # Keep within bounds
        self.x = max(GATHERER_RADIUS, min(SIMULATION_WIDTH - GATHERER_RADIUS, self.x))
        self.y = max(GATHERER_RADIUS, min(SIMULATION_HEIGHT - GATHERER_RADIUS, self.y))
    
    def _find_nearest_food(self, food_items):
        if not food_items:
            return None
        
        nearest = None
        min_distance = float('inf')
        
        for food in food_items:
            distance = math.sqrt((self.x - food.x)**2 + (self.y - food.y)**2)
            if distance < min_distance:
                min_distance = distance
                nearest = food
        
        return nearest
    
    def _explore(self):
        random_component = 1 - self.genes['search_pattern']
        systematic_component = self.genes['search_pattern']
        
        if random.random() < random_component:
            angle = random.uniform(0, 2 * math.pi)
            self.x += math.cos(angle) * self.genes['speed']
            self.y += math.sin(angle) * self.genes['speed']
        else:
            grid_size = 50
            target_x = (self.search_grid_x * grid_size) % SIMULATION_WIDTH
            target_y = (self.search_grid_y * grid_size) % SIMULATION_HEIGHT
            
            dx = target_x - self.x
            dy = target_y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance < 20:
                self.search_grid_x += 1
                if self.search_grid_x * grid_size >= SIMULATION_WIDTH:
                    self.search_grid_x = 0
                    self.search_grid_y += 1
                if self.search_grid_y * grid_size >= SIMULATION_HEIGHT:
                    self.search_grid_y = 0
            else:
                dx /= distance
                dy /= distance
                self.x += dx * self.genes['speed']
                self.y += dy * self.genes['speed']
    
    def collect_food(self, food):
        # Double food value!
        self.energy = min(GATHERER_MAX_ENERGY, self.energy + (FOOD_ENERGY_VALUE * 2))
        self.food_collected += 1
    
    def collect_fractional_food(self, food, portion):
        """Collect a fractional amount of food based on sharing - farmers get double!"""
        energy_gain = FOOD_ENERGY_VALUE * 2 * portion  # Double food value
        self.energy = min(GATHERER_MAX_ENERGY, self.energy + energy_gain)
        self.food_collected += portion
    
    def take_damage(self):
        """Handle death/life loss"""
        self.alive = False
    
    def get_color(self):
        """Return color for rendering - includes death animation"""
        if not self.alive:
            alpha = max(0, 255 - (self.death_timer * 25))
            return (255, 255, 255, alpha)  # White fading out
        else:
            return (255, 255, 255)  # White for living farmers

class Food:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.available = True
        self.respawn_timer = 0
        self.pulse_phase = random.uniform(0, 2 * math.pi)
    
    def update(self):
        self.pulse_phase += 0.1
        
        if not self.available:
            self.respawn_timer += 1
            if self.respawn_timer >= FOOD_RESPAWN_TIME:
                self.available = True
                self.respawn_timer = 0
    
    def collect(self):
        if self.available:
            self.available = False
            self.respawn_timer = 0
            return True
        return False
    
    def get_pulse_intensity(self):
        return 0.5 + 0.5 * math.sin(self.pulse_phase)

class InteractionManager:
    def __init__(self):
        self.interaction_effects = []
        # Outcome counters
        self.mutual_cooperation_count = 0
        self.exploitation_count = 0
        self.mutual_defection_count = 0
        self.cooperation_deaths = 0
    
    def decide_cooperation(self, gatherer):
        """Returns True if cooperates, False if defects"""
        if gatherer.tribe_name == "ninja":
            return False
        elif gatherer.tribe_name == "farmer":
            return True
        elif gatherer.tribe_name == "runner":
            return random.random() < 0.5
        else:  # GA tribe
            return random.random() < gatherer.genes['cooperation']
    
    def resolve_interaction(self, g1, g2):
        """Applies Prisoner's Dilemma payoff matrix"""
        g1_cooperates = self.decide_cooperation(g1)
        g2_cooperates = self.decide_cooperation(g2)
        
        if g1_cooperates and g2_cooperates:
            # Mutual cooperation
            g1.food_collected += 1
            g2.food_collected += 1
            outcome_color = (0, 255, 0)  # Green
            self.mutual_cooperation_count += 1
            
        elif g1_cooperates and not g2_cooperates:
            # G1 exploited by G2
            g1.food_collected = max(0, g1.food_collected - 1)
            g2.food_collected += 3
            if random.random() < EXPLOITATION_DEATH_CHANCE:
                g1.take_damage()  # Dies or loses life
                self.cooperation_deaths += 1
            outcome_color = (255, 255, 0)  # Yellow
            self.exploitation_count += 1
            
        elif not g1_cooperates and g2_cooperates:
            # G2 exploited by G1
            g1.food_collected += 3
            g2.food_collected = max(0, g2.food_collected - 1)
            if random.random() < EXPLOITATION_DEATH_CHANCE:
                g2.take_damage()  # Dies or loses life
                self.cooperation_deaths += 1
            outcome_color = (255, 255, 0)  # Yellow
            self.exploitation_count += 1
            
        else:
            # Mutual defection
            if random.random() < MUTUAL_DEFECTION_DEATH_CHANCE:
                g1.take_damage()
                self.cooperation_deaths += 1
            if random.random() < MUTUAL_DEFECTION_DEATH_CHANCE:
                g2.take_damage()
                self.cooperation_deaths += 1
            outcome_color = (255, 0, 0)  # Red
            self.mutual_defection_count += 1
        
        # Apply cooldown to prevent immediate re-interaction
        g1.interaction_cooldown = INTERACTION_COOLDOWN
        g2.interaction_cooldown = INTERACTION_COOLDOWN
        
        # Visual effects removed per user request
    
    def create_interaction_effect(self, g1, g2, color):
        """Spawns visual effect at midpoint between gatherers"""
        midpoint_x = (g1.x + g2.x) / 2
        midpoint_y = (g1.y + g2.y) / 2
        
        effect = {
            'x': midpoint_x,
            'y': midpoint_y,
            'color': color,
            'radius': 8,  # Small fixed radius
            'duration': 15,  # Shorter duration
            'current_frame': 0
        }
        self.interaction_effects.append(effect)
    
    def check_interactions(self, all_gatherers):
        """Check for interactions between gatherers of different tribes"""
        for i, g1 in enumerate(all_gatherers):
            if not g1.alive or g1.interaction_cooldown > 0:
                continue
            
            for g2 in all_gatherers[i+1:]:
                if not g2.alive or g2.interaction_cooldown > 0:
                    continue
                
                # Must be different tribes
                if g1.tribe_name == g2.tribe_name:
                    continue
                
                # Check distance
                distance = math.sqrt((g1.x - g2.x)**2 + (g1.y - g2.y)**2)
                if distance <= INTERACTION_RANGE:
                    self.resolve_interaction(g1, g2)
    
    def render_interaction_effects(self, screen):
        """Render and update all active effects"""
        for effect in self.interaction_effects:
            effect['current_frame'] += 1
            progress = effect['current_frame'] / effect['duration']
            
            alpha = int(255 * (1 - progress))
            # Draw small filled circle ping
            pygame.draw.circle(screen, effect['color'], 
                              (int(effect['x']), int(effect['y'])), 
                              effect['radius'])
            
        # Remove finished effects
        self.interaction_effects[:] = [e for e in self.interaction_effects 
                                     if e['current_frame'] < e['duration']]
    
    def get_cooperation_stats(self):
        """Return cooperation outcome statistics"""
        return {
            'mutual_cooperation': self.mutual_cooperation_count,
            'exploitation': self.exploitation_count,
            'mutual_defection': self.mutual_defection_count,
            'cooperation_deaths': self.cooperation_deaths
        }