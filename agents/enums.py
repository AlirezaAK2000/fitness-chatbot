from enum import Enum


class PlannerType(Enum):
    FITNESS = 'fitness'
    DIET = 'diet'


class TaskType(Enum):
    FITNESS = 'fitness'
    DIET = 'diet'
    PROGRESS_LOG = 'progress_log'
    UNKNOWN = 'unknown'