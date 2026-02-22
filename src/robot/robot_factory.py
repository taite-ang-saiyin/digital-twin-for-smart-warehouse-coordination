"""
Factory for creating different types of robots
"""

import logging
from typing import Dict, Any
from .robot import Robot
from .robot_status import RobotRole

logger = logging.getLogger(__name__)

class RobotFactory:
    """Creates robots with different roles and capabilities"""
    
    @staticmethod
    def create_picker_robot(robot_id: str, start_position: tuple, env_interface) -> Robot:
        """
        Create a picker robot optimized for picking items
        
        Args:
            robot_id: Unique identifier
            start_position: Initial (x, y) coordinates
            env_interface: Environment interface
            
        Returns:
            Configured picker robot
        """
        robot = Robot(robot_id, start_position, env_interface)
        robot.role = RobotRole.PICKER
        robot.capacity = 2
        robot.battery_drain_rate = 0.15  # Pickers move more
        robot.allowed_tasks = ['MOVE', 'PICK', 'DROP']
        logger.info(f"Created PICKER robot {robot_id}")
        return robot
    
    @staticmethod
    def create_packer_robot(robot_id: str, start_position: tuple, env_interface) -> Robot:
        """
        Create a packer robot optimized for packing operations
        
        Args:
            robot_id: Unique identifier
            start_position: Initial (x, y) coordinates
            env_interface: Environment interface
            
        Returns:
            Configured packer robot
        """
        robot = Robot(robot_id, start_position, env_interface)
        robot.role = RobotRole.PACKER
        robot.capacity = 5
        robot.battery_drain_rate = 0.05  # Packers move less
        robot.allowed_tasks = ['MOVE', 'PACK', 'DROP']
        logger.info(f"Created PACKER robot {robot_id}")
        return robot
    
    @staticmethod
    def create_charger_robot(robot_id: str, start_position: tuple, env_interface) -> Robot:
        """
        Create a charger robot that assists other robots
        
        Args:
            robot_id: Unique identifier
            start_position: Initial (x, y) coordinates
            env_interface: Environment interface
            
        Returns:
            Configured charger robot
        """
        robot = Robot(robot_id, start_position, env_interface)
        robot.role = RobotRole.CHARGER
        robot.capacity = 0  # Can't carry items
        robot.battery_drain_rate = 0.1
        robot.allowed_tasks = ['MOVE', 'CHARGE', 'ASSIST']
        logger.info(f"Created CHARGER robot {robot_id}")
        return robot
    
    @staticmethod
    def create_universal_robot(robot_id: str, start_position: tuple, env_interface) -> Robot:
        """
        Create a universal robot that can do everything
        
        Args:
            robot_id: Unique identifier
            start_position: Initial (x, y) coordinates
            env_interface: Environment interface
            
        Returns:
            Configured universal robot
        """
        robot = Robot(robot_id, start_position, env_interface)
        robot.role = RobotRole.UNIVERSAL
        robot.capacity = 3
        robot.battery_drain_rate = 0.1
        robot.allowed_tasks = ['MOVE', 'PICK', 'DROP', 'PACK', 'CHARGE']
        logger.info(f"Created UNIVERSAL robot {robot_id}")
        return robot
    
    @staticmethod
    def create_from_config(config: Dict[str, Any], env_interface) -> Robot:
        """
        Create a robot from configuration dictionary
        
        Args:
            config: Robot configuration
            env_interface: Environment interface
            
        Returns:
            Configured robot
        """
        robot_type = config.get('type', 'universal').lower()
        robot_id = config['id']
        start_pos = tuple(config['start_position'])
        
        factories = {
            'picker': RobotFactory.create_picker_robot,
            'packer': RobotFactory.create_packer_robot,
            'charger': RobotFactory.create_charger_robot,
            'universal': RobotFactory.create_universal_robot
        }
        
        factory = factories.get(robot_type, RobotFactory.create_universal_robot)
        robot = factory(robot_id, start_pos, env_interface)
        
        # Apply custom configuration
        if 'battery' in config:
            robot.battery_level = config['battery']
        if 'capacity' in config:
            robot.capacity = config['capacity']
        
        return robot