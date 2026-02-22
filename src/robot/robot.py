"""
Main Robot Class
Handles all robot behaviors, sensors, and actuators
"""

import logging
from typing import List, Tuple, Dict, Optional, Any
from .robot_status import RobotStatus, RobotRole, Direction

logger = logging.getLogger(__name__)

class Robot:
    """
    Autonomous robot agent for warehouse operations
    
    Attributes:
        id: Unique robot identifier
        position: Current (x, y) coordinates
        status: Current robot state
        role: Type of robot (picker, packer, etc.)
        battery_level: Current battery percentage
    """
    
    def __init__(self, robot_id: str, start_position: Tuple[int, int], env_interface):
        """
        Initialize a new robot
        
        Args:
            robot_id: Unique identifier (e.g., 'r1', 'r2')
            start_position: Initial (x, y) coordinates
            env_interface: Interface to Member 1's environment
        """
        # Core attributes
        self.id = robot_id
        self.position = start_position
        self.orientation = Direction.NORTH
        self.battery_level = 100.0
        self.battery_drain_rate = 0.1
        self.charge_rate = 2.0
        
        # Status management
        self.status = RobotStatus.IDLE
        self.task_queue = []
        self.current_task = None
        self.wait_reason = None
        self.blocked_count = 0
        
        # Capabilities
        self.role = RobotRole.UNIVERSAL
        self.carrying_item = None
        self.capacity = 1
        self.allowed_tasks = ['MOVE', 'PICK', 'DROP', 'CHARGE']
        
        # Navigation
        self.path = []
        self.destination = None
        self.last_move_time = 0
        self.consecutive_failures = 0
        
        # Environment interface (Member 1's API)
        self.env = env_interface
        
        # Sensors
        self.sensor_range = 3
        self.detection_range = 2
        
        # Performance tracking
        self.total_distance_traveled = 0
        self.tasks_completed = 0
        self.moves_made = 0
        self.waits_made = 0
        self.start_time = 0
        self.idle_time = 0
        
        logger.info(f"Robot {self.id} created at {self.position}")
    
    # ========== ACTUATORS ==========
    
    def move(self, direction: str) -> bool:
        """
        Move robot in specified direction
        Generates ROBOT_MOVE or ROBOT_WAIT event in Member 1's log
        
        Args:
            direction: 'UP', 'DOWN', 'LEFT', 'RIGHT'
            
        Returns:
            True if move successful, False if blocked or invalid
        """
        # Convert direction string to delta
        dx, dy = self._direction_to_delta(direction)
        
        # Calculate new position
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        new_pos = (new_x, new_y)
        
        # Validate move
        if not self.env.is_valid_cell(new_x, new_y):
            self.status = RobotStatus.BLOCKED
            self.wait_reason = "OUT_OF_BOUNDS"
            self.consecutive_failures += 1
            logger.debug(f"Robot {self.id} cannot move {direction} - out of bounds")
            return False
        
        # Check if cell is occupied
        if not self.env.is_cell_free(new_x, new_y):
            # Cell is occupied - robot must wait
            self.status = RobotStatus.WAITING
            self.wait_reason = "CELL_OCCUPIED"
            self.waits_made += 1
            self.consecutive_failures += 1
            
            # Generate WAIT event for Member 1's log
            self.env.robot_wait(self.id, reason="CELL_OCCUPIED")
            logger.debug(f"Robot {self.id} waiting at {self.position} - cell {new_pos} occupied")
            return False
        
        # Check battery
        if self.battery_level <= 0:
            self.status = RobotStatus.ERROR
            self.wait_reason = "BATTERY_DEPLETED"
            self.env.robot_wait(self.id, reason="BATTERY_DEPLETED")
            return False
        
        # Execute the move - generates JSON event for Member 1
        if self.env.robot_move(self.id, self.position, new_pos):
            # Update internal state
            old_pos = self.position
            self.position = new_pos
            self.battery_level = max(0, self.battery_level - self.battery_drain_rate)
            self.total_distance_traveled += 1
            self.moves_made += 1
            self.consecutive_failures = 0
            
            # Update orientation
            self.orientation = Direction.from_string(direction)
            
            logger.debug(f"Robot {self.id} moved from {old_pos} to {new_pos}")
            
            # Update status
            if self.status in [RobotStatus.BLOCKED, RobotStatus.WAITING]:
                self.status = RobotStatus.MOVING
                self.wait_reason = None
            
            return True
        
        return False
    
    def move_to(self, target_x: int, target_y: int) -> bool:
        """
        Move one step towards target coordinates
        Uses simple Manhattan distance (will be replaced by Member 3's path planning)
        
        Args:
            target_x: Target x coordinate
            target_y: Target y coordinate
            
        Returns:
            True if move was attempted, False if already at target
        """
        if self.position == (target_x, target_y):
            return True
        
        # Calculate direction to move
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        
        # Try to move in the most beneficial direction
        if abs(dx) > abs(dy):
            if dx > 0:
                return self.move('RIGHT')
            else:
                return self.move('LEFT')
        else:
            if dy > 0:
                return self.move('DOWN')
            else:
                return self.move('UP')
    
    def pick_item(self, item_id: str) -> bool:
        """
        Pick up an item from current location
        
        Args:
            item_id: Identifier of item to pick
            
        Returns:
            True if pick successful
        """
        if self.carrying_item is not None:
            logger.warning(f"Robot {self.id} cannot pick {item_id} - already carrying {self.carrying_item}")
            return False
        
        if len(self.task_queue) + (1 if self.current_task else 0) >= self.capacity:
            logger.warning(f"Robot {self.id} at capacity")
            return False
        
        # Generate PICK event for Member 1
        self.env.robot_pick(self.id, self.position, item_id)
        
        self.carrying_item = item_id
        self.status = RobotStatus.PICKING
        logger.info(f"Robot {self.id} picked up item {item_id}")
        return True
    
    def drop_item(self, item_id: str) -> bool:
        """
        Drop an item at current location
        
        Args:
            item_id: Identifier of item to drop
            
        Returns:
            True if drop successful
        """
        if self.carrying_item != item_id:
            logger.warning(f"Robot {self.id} cannot drop {item_id} - carrying {self.carrying_item}")
            return False
        
        # Generate DROP event for Member 1
        self.env.robot_drop(self.id, self.position, item_id)
        
        self.carrying_item = None
        self.status = RobotStatus.IDLE
        logger.info(f"Robot {self.id} dropped item {item_id}")
        return True
    
    def start_charging(self) -> bool:
        """
        Begin charging at current location
        
        Returns:
            True if charging started successfully
        """
        # Check if at charging station
        if not self.env.is_charging_station(self.position[0], self.position[1]):
            logger.warning(f"Robot {self.id} cannot charge - not at charging station")
            return False
        
        station_id = self.env.get_station_at(self.position[0], self.position[1])
        
        # Generate CHARGE_START event
        self.env.robot_charge_start(self.id, station_id)
        
        self.status = RobotStatus.CHARGING
        self.current_task = {"type": "CHARGE", "station": station_id}
        logger.info(f"Robot {self.id} started charging at {station_id}")
        return True
    
    def charge(self) -> bool:
        """
        Perform one charging tick
        
        Returns:
            True if still charging
        """
        if self.status == RobotStatus.CHARGING:
            self.battery_level = min(100, self.battery_level + self.charge_rate)
            if self.battery_level >= 100:
                self.stop_charging()
            return True
        return False
    
    def stop_charging(self) -> bool:
        """
        Stop charging and release station
        
        Returns:
            True if stopped successfully
        """
        if self.status == RobotStatus.CHARGING:
            station_id = self.current_task["station"]
            
            # Generate CHARGE_END event
            self.env.robot_charge_end(self.id, station_id)
            
            self.status = RobotStatus.IDLE
            self.current_task = None
            logger.info(f"Robot {self.id} stopped charging")
            return True
        return False
    
    # ========== SENSORS ==========
    
    def detect_obstacles(self) -> List[Dict]:
        """
        Detect obstacles within sensor range
        
        Returns:
            List of detected obstacles with position and type
        """
        obstacles = []
        x, y = self.position
        
        for dx in range(-self.sensor_range, self.sensor_range + 1):
            for dy in range(-self.sensor_range, self.sensor_range + 1):
                if dx == 0 and dy == 0:
                    continue
                    
                check_x, check_y = x + dx, y + dy
                
                if self.env.is_valid_cell(check_x, check_y):
                    if not self.env.is_cell_free(check_x, check_y):
                        # Check if it's a robot or static obstacle
                        robot_id = self.env.get_robot_at(check_x, check_y)
                        obstacles.append({
                            'position': (check_x, check_y),
                            'type': 'ROBOT' if robot_id else 'OBSTACLE',
                            'robot_id': robot_id,
                            'distance': abs(dx) + abs(dy),
                            'direction': self._get_direction_to(dx, dy)
                        })
        
        return sorted(obstacles, key=lambda o: o['distance'])
    
    def get_nearby_robots(self) -> List[Dict]:
        """
        Detect other robots within detection range
        
        Returns:
            List of nearby robots with positions
        """
        nearby = []
        x, y = self.position
        
        all_robots = self.env.get_all_robot_positions()
        
        for robot_id, pos in all_robots.items():
            if robot_id != self.id:
                distance = abs(x - pos[0]) + abs(y - pos[1])
                if distance <= self.detection_range:
                    nearby.append({
                        'id': robot_id,
                        'position': pos,
                        'distance': distance,
                        'direction': self._get_direction_to(pos[0] - x, pos[1] - y)
                    })
        
        return sorted(nearby, key=lambda r: r['distance'])
    
    def get_battery_status(self) -> Dict:
        """
        Get battery information
        
        Returns:
            Battery status dictionary
        """
        return {
            'level': self.battery_level,
            'percentage': self.battery_level,
            'critical': self.battery_level < 20,
            'low': self.battery_level < 30,
            'needs_charging': self.battery_level < 15,
            'estimated_operations': int(self.battery_level / self.battery_drain_rate)
        }
    
    # ========== TASK MANAGEMENT ==========
    
    def assign_task(self, task: Dict):
        """
        Assign a new task to the robot
        
        Args:
            task: Task dictionary with type, location, etc.
        """
        if task['type'] not in self.allowed_tasks:
            logger.warning(f"Robot {self.id} cannot do task type: {task['type']}")
            return
        
        self.task_queue.append(task)
        logger.info(f"Robot {self.id} assigned task: {task}")
        
        if self.status == RobotStatus.IDLE:
            self._start_next_task()
    
    def _start_next_task(self) -> bool:
        """Start the next task in queue"""
        if not self.task_queue:
            self.status = RobotStatus.IDLE
            return False
        
        self.current_task = self.task_queue.pop(0)
        self.status = RobotStatus.MOVING
        
        # Set destination based on task type
        if self.current_task['type'] == 'MOVE':
            self.destination = tuple(self.current_task['location'])
        elif self.current_task['type'] == 'PICK':
            self.destination = tuple(self.current_task['item_location'])
        elif self.current_task['type'] == 'DROP':
            self.destination = tuple(self.current_task['station_location'])
        elif self.current_task['type'] == 'CHARGE':
            self.destination = tuple(self.current_task['station_location'])
        
        logger.info(f"Robot {self.id} started task: {self.current_task['type']} to {self.destination}")
        return True
    
    def complete_current_task(self):
        """Mark current task as complete"""
        if self.current_task:
            self.tasks_completed += 1
            logger.info(f"Robot {self.id} completed task: {self.current_task['type']}")
            self.current_task = None
            self._start_next_task()
    
    def get_task_progress(self) -> Optional[Dict]:
        """
        Get progress on current task
        
        Returns:
            Progress dictionary or None if no task
        """
        if not self.current_task or not self.destination:
            return None
        
        # Calculate distance to destination
        distance = abs(self.position[0] - self.destination[0]) + \
                  abs(self.position[1] - self.destination[1])
        
        # Estimate total distance (simplified)
        if not hasattr(self, '_task_start_pos'):
            self._task_start_pos = self.position
        
        total_distance = abs(self._task_start_pos[0] - self.destination[0]) + \
                        abs(self._task_start_pos[1] - self.destination[1])
        
        progress = 1 - (distance / total_distance) if total_distance > 0 else 1.0
        
        return {
            'task_type': self.current_task['type'],
            'progress': max(0, min(1, progress)),
            'destination': self.destination,
            'distance_remaining': distance,
            'eta': distance * 2  # Rough estimate
        }
    
    # ========== DECISION MAKING ==========
    
    def decide_next_action(self) -> Optional[str]:
        """
        Decide what action to take next based on current state
        
        Returns:
            Action description or None
        """
        if self.status == RobotStatus.IDLE:
            # Check if need to charge
            if self.battery_level < 20:
                # Find nearest charging station
                charging_stations = [(2, 2), (18, 18)]  # Hardcoded for demo
                if charging_stations:
                    # Find closest
                    nearest = min(charging_stations, 
                                key=lambda s: abs(s[0]-self.position[0]) + abs(s[1]-self.position[1]))
                    self.destination = nearest
                    self.status = RobotStatus.MOVING
                    return f"Moving to charging station at {nearest}"
            
            return "Idle - waiting for tasks"
        
        elif self.status == RobotStatus.MOVING:
            if self.position == self.destination:
                # Arrived at destination
                if self.current_task:
                    if self.current_task['type'] == 'CHARGE':
                        self.start_charging()
                        return "Started charging"
                    elif self.current_task['type'] == 'PICK':
                        self.pick_item(self.current_task.get('item_id', 'unknown'))
                        self.complete_current_task()
                        return "Picked up item"
                    elif self.current_task['type'] == 'DROP':
                        self.drop_item(self.carrying_item)
                        self.complete_current_task()
                        return "Dropped item"
                return "Arrived at destination"
            
            # Check for obstacles
            obstacles = self.detect_obstacles()
            immediate_obstacles = [o for o in obstacles if o['distance'] <= 1]
            
            if immediate_obstacles:
                return f"Blocked by {len(immediate_obstacles)} obstacles"
            
            # Continue moving
            return f"Moving to {self.destination}"
        
        elif self.status == RobotStatus.CHARGING:
            return f"Charging... Battery: {self.battery_level:.1f}%"
        
        elif self.status == RobotStatus.WAITING:
            return f"Waiting: {self.wait_reason}"
        
        return "Unknown state"
    
    def calculate_utility(self, task: Dict) -> float:
        """
        Calculate utility of a task for this robot
        
        Args:
            task: Task to evaluate
            
        Returns:
            Utility score (higher is better)
        """
        utility = 0.0
        
        if task['type'] == 'CHARGE':
            # Higher utility if battery is low
            utility = (100 - self.battery_level) * 2
        else:
            # Distance-based utility
            task_location = task.get('location') or task.get('item_location') or task.get('station_location')
            if task_location:
                distance = abs(self.position[0] - task_location[0]) + \
                          abs(self.position[1] - task_location[1])
                utility = 100 / (distance + 1)
            
            # Priority boost
            if task.get('priority') == 'HIGH':
                utility *= 2
            elif task.get('priority') == 'LOW':
                utility *= 0.5
            
            # Role-based adjustment
            if self.role == RobotRole.PICKER and task['type'] == 'PICK':
                utility *= 1.5
            elif self.role == RobotRole.PACKER and task['type'] == 'PACK':
                utility *= 1.5
        
        return utility
    
    # ========== UTILITY METHODS ==========
    
    def _direction_to_delta(self, direction: str) -> Tuple[int, int]:
        """Convert direction string to delta coordinates"""
        directions = {
            'UP': (0, -1),
            'DOWN': (0, 1),
            'LEFT': (-1, 0),
            'RIGHT': (1, 0),
            'NORTH': (0, -1),
            'SOUTH': (0, 1),
            'WEST': (-1, 0),
            'EAST': (1, 0)
        }
        return directions.get(direction.upper(), (0, 0))
    
    def _get_direction_to(self, dx: int, dy: int) -> str:
        """Get direction string to a relative position"""
        if abs(dx) > abs(dy):
            return 'RIGHT' if dx > 0 else 'LEFT'
        else:
            return 'DOWN' if dy > 0 else 'UP'
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report"""
        return {
            'id': self.id,
            'position': self.position,
            'battery': round(self.battery_level, 1),
            'status': self.status.name,
            'role': self.role.value,
            'carrying_item': self.carrying_item,
            'tasks_completed': self.tasks_completed,
            'distance_traveled': self.total_distance_traveled,
            'moves_made': self.moves_made,
            'waits_made': self.waits_made,
            'wait_reason': self.wait_reason,
            'current_task': self.current_task['type'] if self.current_task else None,
            'tasks_in_queue': len(self.task_queue),
            'consecutive_failures': self.consecutive_failures
        }
    
    def __str__(self) -> str:
        """String representation"""
        return f"Robot[{self.id}] at {self.position} ({self.status.name})"