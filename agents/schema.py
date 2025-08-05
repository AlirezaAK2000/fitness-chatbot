from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from typing import List, Literal
from agents.enums import TaskType

class UserMessages(MessagesState):
    user_id: int
    log_summary: str
    summarized_fitness_plan: str
    summarized_diet_plan: str
    task_type: TaskType
    contexts: List[str]


class Task(BaseModel):

    type: Literal['fitness', 'diet', 'progress_log', 'unknown'] = Field(
        description= "Indicating the type of task based on user's chat."
    )