"""
Interface to Member 1's JSON-based Environment Module
"""

import json
from typing import List, Tuple, Dict, Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)

class EnvironmentInterface:
    """
    API for interacting with Member 1's environment that outputs JSON logs
    
    This interface defines the contract between Member 2 (Robot Agent) and
    Member 1 (Environment & Core Simulation Engine). It provides methods for
    robots to query the environment state and generate actions that Member 1
    will log in JSON format.
    """
    
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the environment interface
        
        Args:
            log_callback: Function to call when robot generates an action
                         This will write to Member 1's JSON log file
        """
        self.log_callback = log_callback
        self.current_time = 0
        
        # Cache of current state (updated from logs)
        self.robot_positions: Dict[str, Tuple[int, int]] = {}
        self.grid_occupancy: Dict[Tuple[int, int], str] = {}
        
        # Grid configuration (from Member 1)
        self.grid_width = 20
        self.grid_height = 20
        self.obstacles: set = self._initialize_obstacles()
        self.stations: Dict[Tuple[int, int], Dict] = self._initialize_stations()
        
        logger.info("Environment Interface initialized")
    
    def _initialize_obstacles(self) -> set:
        """Initialize static obstacles (should come from Member 1)"""
        # Example obstacles - in real implementation, these come from Member 1
        return {
            (5, 5), (5, 6), (6, 5), (6, 6),  # Shelf cluster
            (10, 10), (10, 11), (11, 10), (11, 11),  # Another shelf cluster
            (15, 15),  # Single obstacle
        }
    
    def _initialize_stations(self) -> Dict[Tuple[int, int], Dict]:
        """Initialize stations (should come from Member 1)"""
        return {
            (2, 2): {'id': 'charger_1', 'type': 'charging', 'occupied': False},
            (18, 18): {'id': 'charger_2', 'type': 'charging', 'occupied': False},
            (10, 2): {'id': 'packing_1', 'type': 'packing', 'occupied': False},
            (10, 18): {'id': 'depot_1', 'type': 'depot', 'occupied': False},
        }
    
    # ========== TICK MANAGEMENT ==========
    
    def process_tick_start(self, t: int):
        """
        Called at the start of each simulation tick
        This would be called by Member 1's simulation engine
        
        Args:
            t: Current simulation time
        """
        self.current_time = t
        logger.debug(f"Tick {t} started")
    
    # ========== ROBOT ACTIONS (Generate JSON events) ==========
    
    def robot_move(self, robot_id: str, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> bool:
        """
        Request robot to move
        Generates: {"t": t, "type": "ROBOT_MOVE", "robot_id": "r1", "from": [x,y], "to": [x,y]}
        
        Args:
            robot_id: Robot identifier
            from_pos: Current position
            to_pos: Desired new position
            
        Returns:
            True if move was logged
        """
        if self.log_callback:
            event = {
                "t": self.current_time,
                "type": "ROBOT_MOVE",
                "robot_id": robot_id,
                "from": [from_pos[0], from_pos[1]],
                "to": [to_pos[0], to_pos[1]]
            }
            self.log_callback(json.dumps(event))
            
            # Update local cache
            self.robot_positions[robot_id] = to_pos
            self.grid_occupancy[to_pos] = robot_id
            if from_pos in self.grid_occupancy:
                del self.grid_occupancy[from_pos]
            
            return True
        return False
    
    def robot_wait(self, robot_id: str, reason: str = "CELL_OCCUPIED"):
        """
        Robot waits because it cannot move
        Generates: {"t": t, "type": "ROBOT_WAIT", "robot_id": "r1", "reason": "CELL_OCCUPIED"}
        
        Args:
            robot_id: Robot identifier
            reason: Reason for waiting
        """
        if self.log_callback:
            event = {
                "t": self.current_time,
                "type": "ROBOT_WAIT",
                "robot_id": robot_id,
                "reason": reason
            }
            self.log_callback(json.dumps(event))
    
    def robot_pick(self, robot_id: str, position: Tuple[int, int], item_id: str):
        """
        Robot picks up an item
        Generates: {"t": t, "type": "ROBOT_PICK", "robot_id": "r1", "position": [x,y], "item_id": "item1"}
        
        Args:
            robot_id: Robot identifier
            position: Current position
            item_id: Item being picked
        """
        if self.log_callback:
            event = {
                "t": self.current_time,
                "type": "ROBOT_PICK",
                "robot_id": robot_id,
                "position": [position[0], position[1]],
                "item_id": item_id
            }
            self.log_callback(json.dumps(event))
    
    def robot_drop(self, robot_id: str, position: Tuple[int, int], item_id: str):
        """
        Robot drops an item
        Generates: {"t": t, "type": "ROBOT_DROP", "robot_id": "r1", "position": [x,y], "item_id": "item1"}
        
        Args:
            robot_id: Robot identifier
            position: Current position
            item_id: Item being dropped
        """
        if self.log_callback:
            event = {
                "t": self.current_time,
                "type": "ROBOT_DROP",
                "robot_id": robot_id,
                "position": [position[0], position[1]],
                "item_id": item_id
            }
            self.log_callback(json.dumps(event))
    
    def robot_charge_start(self, robot_id: str, station_id: str):
        """
        Robot starts charging
        Generates: {"t": t, "type": "ROBOT_CHARGE_START", "robot_id": "r1", "station_id": "charger_1"}
        
        Args:
            robot_id: Robot identifier
            station_id: Charging station identifier
        """
        if self.log_callback:
            event = {
                "t": self.current_time,
                "type": "ROBOT_CHARGE_START",
                "robot_id": robot_id,
                "station_id": station_id
            }
            self.log_callback(json.dumps(event))
            
            # Mark station as occupied
            for pos, station in self.stations.items():
                if station['id'] == station_id:
                    station['occupied'] = True
                    break
    
    def robot_charge_end(self, robot_id: str, station_id: str):
        """
        Robot ends charging
        Generates: {"t": t, "type": "ROBOT_CHARGE_END", "robot_id": "r1", "station_id": "charger_1"}
        
        Args:
            robot_id: Robot identifier
            station_id: Charging station identifier
        """
        if self.log_callback:
            event = {
                "t": self.current_time,
                "type": "ROBOT_CHARGE_END",
                "robot_id": robot_id,
                "station_id": station_id
            }
            self.log_callback(json.dumps(event))
            
            # Mark station as free
            for pos, station in self.stations.items():
                if station['id'] == station_id:
                    station['occupied'] = False
                    break
    
    # ========== ENVIRONMENT QUERIES (For robots to check state) ==========
    
    def is_cell_free(self, x: int, y: int) -> bool:
        """
        Check if a cell is free to move into
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if cell is free, False if occupied or obstacle
        """
        # Check if cell is occupied by another robot
        if (x, y) in self.grid_occupancy:
            return False
        
        # Check if cell is an obstacle
        if (x, y) in self.obstacles:
            return False
        
        return True
    
    def is_valid_cell(self, x: int, y: int) -> bool:
        """
        Check if coordinates are within grid bounds
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if within grid
        """
        return 0 <= x < self.grid_width and 0 <= y < self.grid_height
    
    def get_cell_type(self, x: int, y: int) -> str:
        """
        Get type of cell at position
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Cell type: 'free', 'obstacle', 'station', 'charging', etc.
        """
        if not self.is_valid_cell(x, y):
            return 'invalid'
        
        if (x, y) in self.obstacles:
            return 'obstacle'
        
        if (x, y) in self.stations:
            station_type = self.stations[(x, y)]['type']
            if station_type == 'charging':
                return 'charging_station'
            return f'station_{station_type}'
        
        if (x, y) in self.grid_occupancy:
            return 'occupied_by_robot'
        
        return 'free'
    
    def get_robot_at(self, x: int, y: int) -> Optional[str]:
        """
        Get robot ID at position
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Robot ID or None
        """
        return self.grid_occupancy.get((x, y))
    
    def get_all_robot_positions(self) -> Dict[str, Tuple[int, int]]:
        """
        Get positions of all robots
        
        Returns:
            Dictionary mapping robot IDs to positions
        """
        return self.robot_positions.copy()
    
    def is_charging_station(self, x: int, y: int) -> bool:
        """
        Check if cell contains a charging station
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if charging station
        """
        station = self.stations.get((x, y))
        return station is not None and station['type'] == 'charging'
    
    def get_station_at(self, x: int, y: int) -> Optional[str]:
        """
        Get station ID at position
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Station ID or None
        """
        station = self.stations.get((x, y))
        return station['id'] if station else None
    
    def is_station_occupied(self, station_id: str) -> bool:
        """
        Check if station is occupied
        
        Args:
            station_id: Station identifier
            
        Returns:
            True if occupied
        """
        for station in self.stations.values():
            if station['id'] == station_id:
                return station.get('occupied', False)
        return False
    
    # ========== LOG PARSING ==========
    
    def update_from_log(self, log_line: str):
        """
        Parse a log line from Member 1 and update internal state
        
        Args:
            log_line: JSON log line from Member 1
        """
        try:
            event = json.loads(log_line.strip())
            t = event.get("t")
            event_type = event.get("type")
            
            if event_type == "TICK_START":
                self.process_tick_start(t)
            
            elif event_type == "ROBOT_MOVE":
                robot_id = event["robot_id"]
                from_pos = tuple(event["from"])
                to_pos = tuple(event["to"])
                
                # Update positions cache
                self.robot_positions[robot_id] = to_pos
                
                # Update grid occupancy
                if from_pos in self.grid_occupancy:
                    del self.grid_occupancy[from_pos]
                self.grid_occupancy[to_pos] = robot_id
                
                logger.debug(f"Robot {robot_id} moved from {from_pos} to {to_pos}")
            
            elif event_type == "ROBOT_WAIT":
                robot_id = event["robot_id"]
                reason = event.get("reason", "UNKNOWN")
                logger.debug(f"Robot {robot_id} waiting: {reason}")
            
            elif event_type == "ROBOT_PICK":
                robot_id = event["robot_id"]
                position = tuple(event["position"])
                item_id = event["item_id"]
                logger.debug(f"Robot {robot_id} picked {item_id} at {position}")
            
            elif event_type == "ROBOT_DROP":
                robot_id = event["robot_id"]
                position = tuple(event["position"])
                item_id = event["item_id"]
                logger.debug(f"Robot {robot_id} dropped {item_id} at {position}")
            
            elif event_type == "ROBOT_CHARGE_START":
                robot_id = event["robot_id"]
                station_id = event["station_id"]
                logger.debug(f"Robot {robot_id} started charging at {station_id}")
            
            elif event_type == "ROBOT_CHARGE_END":
                robot_id = event["robot_id"]
                station_id = event["station_id"]
                logger.debug(f"Robot {robot_id} stopped charging at {station_id}")
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse log line: {log_line}")
        except KeyError as e:
            logger.error(f"Missing field in log event: {e}")