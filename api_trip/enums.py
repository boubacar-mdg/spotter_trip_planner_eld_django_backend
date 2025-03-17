from enum import Enum

class StopType(Enum):
    START = 'start'
    REST = 'rest'
    FUEL = 'fuel'
    PICKUP = 'pickup'
    DROPOFF = 'dropoff'

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]
