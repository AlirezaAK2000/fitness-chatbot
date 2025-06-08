from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from typing import List, Literal

class UserMessages(MessagesState):
    user_id: int