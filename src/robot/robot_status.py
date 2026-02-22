from enum import Enum, auto

class RobotStatus(Enum):
    """Possible robot states"""
    IDLE = auto()
    MOVING = auto()
    PICKING = auto()
    DROPPING = auto()
    CHARGING = auto()
    BLOCKED = auto()
    ERROR = auto()
    WAITING = auto()

class RobotRole(Enum):
    """Different robot types"""
    PICKER = "picker"
    PACKER = "packer"
    CHARGER = "charger"
    UNIVERSAL = "universal"

class Direction(Enum):
    """Movement directions"""
    NORTH = (0, -1)
    EAST = (1, 0)
    SOUTH = (0, 1)
    WEST = (-1, 0)
    
    @classmethod
    def from_string(cls, direction_str):
        """Convert string to Direction"""
        mapping = {
            'UP': cls.NORTH,
            'DOWN': cls.SOUTH,
            'LEFT': cls.WEST,
            'RIGHT': cls.EAST,
            'NORTH': cls.NORTH,
            'SOUTH': cls.SOUTH,
            'EAST': cls.EAST,
            'WEST': cls.WEST
        }
        return mapping.get(direction_str.upper(), cls.NORTH)
    
    @classmethod
    def to_string(cls, direction):
        """Convert Direction to string"""
        mapping = {
            cls.NORTH: 'UP',
            cls.SOUTH: 'DOWN',
            cls.EAST: 'RIGHT',
            cls.WEST: 'LEFT'
        }
        return mapping.get(direction, 'UNKNOWN')