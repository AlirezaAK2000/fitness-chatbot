from enum import Enum


class PlannerType(Enum):
    FITNESS = 'fitness'
    DIET = 'dietry'


class TaskType(Enum):
    FITNESS = 'fitness'
    DIET = 'dietry'
    PROGRESS_LOG = 'progress_log'
    UNKNOWN = 'unknown'