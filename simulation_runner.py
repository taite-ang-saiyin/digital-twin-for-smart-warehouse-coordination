#!/usr/bin/env python3
"""
Simulation runner that integrates with Member 1's JSON logging system
"""

import logging
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional

from src.robot.robot import Robot
from src.robot.robot_factory import RobotFactory
from src.communication.environment_interface import EnvironmentInterface

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimulationRunner:
    """
    Runs the simulation and generates JSON logs compatible with Member 1's format
    
    This class simulates the environment for testing robot behaviors.
    In the final project, Member 1 will provide the actual simulation engine.
    """
    
    def __init__(self, log_filename: Optional[str] = None):
        """
        Initialize the simulation runner
        
        Args:
            log_filename: Name of log file (auto-generated if None)
        """
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        if log_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"logs/simulation_log_{timestamp}.json"
        else:
            log_filename = f"logs/{log_filename}"
        
        self.log_file = open(log_filename, 'w')
        self.env_interface = EnvironmentInterface(log_callback=self.write_log)
        self.robots: Dict[str, Robot] = {}
        self.current_tick = 0
        self.max_ticks = 100
        self.running = False
        
        logger.info(f"Simulation initialized, logging to {log_filename}")
    
    def write_log(self, event_json: str):
        """Write JSON event to log file"""
        self.log_file.write(event_json + "\n")
        self.log_file.flush()
    
    def add_robot(self, robot: Robot):
        """Add a robot to the simulation"""
        self.robots[robot.id] = robot
        # Update environment interface
        self.env_interface.robot_positions[robot.id] = robot.position
        self.env_interface.grid_occupancy[robot.position] = robot.id
        logger.info(f"Added robot {robot.id} to simulation at {robot.position}")
    
    def add_robots(self, robots: List[Robot]):
        """Add multiple robots to the simulation"""
        for robot in robots:
            self.add_robot(robot)
    
    def tick_start(self):
        """Start a new simulation tick"""
        self.current_tick += 1
        self.env_interface.process_tick_start(self.current_tick)
        
        # Write TICK_START event (Member 1's format)
        event = {
            "t": self.current_tick,
            "type": "TICK_START"
        }
        self.write_log(json.dumps(event))
        
        logger.debug(f"=== Tick {self.current_tick} started ===")
    
    def run_step(self):
        """Run one simulation step (all robots act once)"""
        self.tick_start()
        
        # Let each robot decide and perform its action
        for robot_id, robot in self.robots.items():
            self.run_robot_step(robot)
    
    def run_robot_step(self, robot: Robot):
        """
        Run one step for a single robot
        
        This implements a simple decision loop. In the final project,
        this would be replaced by the robot's own decision making.
        """
        # Get robot's decision
        action_description = robot.decide_next_action()
        
        if robot.status.name == "IDLE":
            # If idle, try to move to a target (for demo purposes)
            if not hasattr(robot, 'demo_target'):
                # Set a demo target based on robot role
                if robot.role.value == 'picker':
                    robot.demo_target = (15, 5)  # Go to shelves
                elif robot.role.value == 'packer':
                    robot.demo_target = (5, 15)  # Go to packing station
                else:
                    robot.demo_target = (10, 10)  # Go to center
            
            # Move towards target
            robot.move_to(robot.demo_target[0], robot.demo_target[1])
        
        elif robot.status.name == "MOVING":
            # Continue moving towards destination
            if robot.destination:
                robot.move_to(robot.destination[0], robot.destination[1])
        
        elif robot.status.name == "CHARGING":
            # Continue charging
            robot.charge()
        
        elif robot.status.name == "WAITING":
            # Robot is waiting - this is already logged by the move method
            pass
    
    def run_simulation(self, ticks: Optional[int] = None):
        """
        Run the simulation for specified number of ticks
        
        Args:
            ticks: Number of ticks to run (uses max_ticks if None)
        """
        if ticks:
            self.max_ticks = ticks
        
        self.running = True
        logger.info(f"Starting simulation for {self.max_ticks} ticks with {len(self.robots)} robots")
        
        try:
            for tick in range(self.max_ticks):
                self.run_step()
                time.sleep(0.05)  # Small delay to make logs readable
            
            logger.info("Simulation completed successfully")
            
        except KeyboardInterrupt:
            logger.info("Simulation stopped by user")
        finally:
            self.running = False
            self.log_file.close()
    
    def get_simulation_stats(self) -> Dict:
        """Get statistics from the simulation"""
        stats = {
            'total_ticks': self.current_tick,
            'robots': {}
        }
        
        for robot_id, robot in self.robots.items():
            stats['robots'][robot_id] = robot.get_status_report()
        
        return stats
    
    def print_summary(self):
        """Print simulation summary"""
        print("\n" + "="*60)
        print("SIMULATION SUMMARY")
        print("="*60)
        
        for robot_id, robot in self.robots.items():
            status = robot.get_status_report()
            print(f"\nRobot {status['id']} ({status['role']}):")
            print(f"  ├─ Final position: {status['position']}")
            print(f"  ├─ Battery: {status['battery']}%")
            print(f"  ├─ Status: {status['status']}")
            print(f"  ├─ Moves made: {status['moves_made']}")
            print(f"  ├─ Waits made: {status['waits_made']}")
            print(f"  └─ Tasks completed: {status['tasks_completed']}")
        
        print(f"\nLog saved to: {self.log_file.name}")
    
    def replay_log(self, log_filename: str):
        """
        Replay a log file to see what happened
        
        Args:
            log_filename: Path to log file
        """
        log_path = f"logs/{log_filename}" if not log_filename.startswith('logs/') else log_filename
        
        logger.info(f"Replaying log: {log_path}")
        print("\n" + "="*60)
        print("LOG REPLAY")
        print("="*60)
        
        try:
            with open(log_path, 'r') as f:
                for line in f:
                    event = json.loads(line.strip())
                    t = event.get('t')
                    event_type = event.get('type')
                    
                    if event_type == 'TICK_START':
                        print(f"\n--- Tick {t} ---")
                    
                    elif event_type == 'ROBOT_MOVE':
                        robot_id = event['robot_id']
                        from_pos = event['from']
                        to_pos = event['to']
                        print(f"  {robot_id}: {from_pos} -> {to_pos}")
                    
                    elif event_type == 'ROBOT_WAIT':
                        robot_id = event['robot_id']
                        reason = event['reason']
                        print(f"  {robot_id}: WAIT ({reason})")
                    
                    elif event_type == 'ROBOT_PICK':
                        robot_id = event['robot_id']
                        item_id = event['item_id']
                        print(f"  {robot_id}: PICK {item_id}")
                    
                    elif event_type == 'ROBOT_DROP':
                        robot_id = event['robot_id']
                        item_id = event['item_id']
                        print(f"  {robot_id}: DROP {item_id}")
                    
                    elif event_type == 'ROBOT_CHARGE_START':
                        robot_id = event['robot_id']
                        station_id = event['station_id']
                        print(f"  {robot_id}: CHARGE START at {station_id}")
                    
                    elif event_type == 'ROBOT_CHARGE_END':
                        robot_id = event['robot_id']
                        station_id = event['station_id']
                        print(f"  {robot_id}: CHARGE END at {station_id}")
        
        except FileNotFoundError:
            logger.error(f"Log file not found: {log_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in log file")

# ========== DEMO SCENARIOS ==========

def demo_basic_movement():
    """Demo 1: Basic robot movement"""
    print("\n" + "="*60)
    print("DEMO 1: Basic Robot Movement")
    print("="*60)
    
    sim = SimulationRunner("demo1_movement.json")
    
    # Create robots
    robot1 = RobotFactory.create_universal_robot("r1", (1, 1), sim.env_interface)
    robot2 = RobotFactory.create_picker_robot("r2", (2, 1), sim.env_interface)
    
    sim.add_robots([robot1, robot2])
    
    # Set destinations
    robot1.demo_target = (10, 10)
    robot2.demo_target = (5, 1)  # This will cause interaction
    
    sim.run_simulation(ticks=15)
    sim.print_summary()
    
    return sim

def demo_multiple_robots():
    """Demo 2: Multiple robots with different roles"""
    print("\n" + "="*60)
    print("DEMO 2: Multiple Robots with Different Roles")
    print("="*60)
    
    sim = SimulationRunner("demo2_multiple.json")
    
    # Create robots with different roles
    robots = [
        RobotFactory.create_picker_robot("picker1", (0, 0), sim.env_interface),
        RobotFactory.create_picker_robot("picker2", (19, 0), sim.env_interface),
        RobotFactory.create_packer_robot("packer1", (0, 19), sim.env_interface),
        RobotFactory.create_charger_robot("charger1", (19, 19), sim.env_interface),
        RobotFactory.create_universal_robot("universal1", (5, 5), sim.env_interface),
    ]
    
    sim.add_robots(robots)
    
    # Set different destinations
    robots[0].demo_target = (15, 5)   # Picker to shelves
    robots[1].demo_target = (5, 15)   # Picker to packing
    robots[2].demo_target = (10, 10)  # Packer to center
    robots[3].demo_target = (2, 2)    # Charger to charging station
    robots[4].demo_target = (15, 15)  # Universal to far corner
    
    sim.run_simulation(ticks=20)
    sim.print_summary()
    
    return sim

def demo_charging():
    """Demo 3: Robot charging behavior"""
    print("\n" + "="*60)
    print("DEMO 3: Robot Charging")
    print("="*60)
    
    sim = SimulationRunner("demo3_charging.json")
    
    # Create robot with low battery
    robot = RobotFactory.create_universal_robot("r1", (10, 10), sim.env_interface)
    robot.battery_level = 15  # Low battery
    
    sim.add_robot(robot)
    
    # Set destination to charging station
    robot.demo_target = (2, 2)  # Charging station
    
    sim.run_simulation(ticks=25)
    sim.print_summary()
    
    return sim

def recreate_member1_example():
    """Recreate the exact scenario from Member 1's example log"""
    print("\n" + "="*60)
    print("Recreating Member 1's Example Scenario")
    print("="*60)
    
    sim = SimulationRunner("member1_example.json")
    
    # Create robots exactly as in the example
    robot1 = RobotFactory.create_universal_robot("r1", (1, 1), sim.env_interface)
    robot2 = RobotFactory.create_universal_robot("r2", (2, 1), sim.env_interface)
    
    sim.add_robots([robot1, robot2])
    
    # Set destinations to match the example
    robot1.demo_target = (4, 1)  # r1 tries to go to (4,1)
    robot2.demo_target = (5, 1)  # r2 tries to go to (5,1)
    
    # Run for 10 ticks to match the example
    sim.run_simulation(ticks=10)
    sim.print_summary()
    
    # Show the generated log
    print("\n" + "="*60)
    print("Generated Log (first 15 lines):")
    print("="*60)
    with open("logs/member1_example.json", 'r') as f:
        for i, line in enumerate(f):
            if i < 15:
                print(line.strip())
    
    return sim

def main():
    """Main function"""
    print("="*60)
    print("ROBOT AGENT MODULE - MEMBER 2")
    print("Compatible with Member 1's JSON Format")
    print("="*60)
    
    print("\nAvailable demos:")
    print("1. Basic Movement (matches Member 1's example)")
    print("2. Multiple Robots with Different Roles")
    print("3. Robot Charging Behavior")
    print("4. Recreate Member 1's Exact Example")
    print("5. Run All Demos")
    print("6. Replay a Log File")
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == "1":
        demo_basic_movement()
    elif choice == "2":
        demo_multiple_robots()
    elif choice == "3":
        demo_charging()
    elif choice == "4":
        recreate_member1_example()
    elif choice == "5":
        demo_basic_movement()
        demo_multiple_robots()
        demo_charging()
        recreate_member1_example()
    elif choice == "6":
        log_files = [f for f in os.listdir('logs') if f.endswith('.json')]
        if log_files:
            print("\nAvailable log files:")
            for i, f in enumerate(log_files):
                print(f"  {i+1}. {f}")
            idx = int(input("Choose file number: ")) - 1
            if 0 <= idx < len(log_files):
                sim = SimulationRunner()
                sim.replay_log(log_files[idx])
        else:
            print("No log files found in logs/ directory")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()