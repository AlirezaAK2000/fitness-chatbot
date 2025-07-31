from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import END, START, StateGraph
from agents.graph import Graph
from db.db_manager import FitnessDB
from agents.schema import UserMessages, Task
from utils import log_function_call
from agents.planner import PlannerGraph
from agents.enums import PlannerType, TaskType
from agents.summarizer import BaseSummarizer
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.prompt import (
    TASK_DETECTION_PROMPT,
    UNKNOWN_TASK_PROMPT
)
from copy import deepcopy
from langgraph.checkpoint.memory import MemorySaver


class MainGraph(Graph):
    def __init__(
            self,
            llm: ChatGoogleGenerativeAI,
            db_manager: FitnessDB,
            last_messages: int = 3
    ):
        super().__init__(llm, UserMessages)
        self.db_manager = db_manager
        self.fitness_planner = PlannerGraph(llm, db_manager, planner_type = PlannerType.FITNESS).compile()
        self.diet_planner = PlannerGraph(llm, db_manager, planner_type = PlannerType.DIET).compile()
        self.summarizer = BaseSummarizer(llm).compile()
        self.last_messages = last_messages


    @log_function_call
    def node_task_identifier(self, state):
        messages = self._get_last_messages(state)
        messages = [
            SystemMessage(
                content = TASK_DETECTION_PROMPT
            )
        ] + messages

        llm_with_output = self.llm.with_structured_output(Task)
        response = llm_with_output.invoke(messages)

        if response.type == 'fitness':
            return {'task_type': TaskType.FITNESS}
        elif response.type == 'diet':
            return {'task_type': TaskType.DIET}
        elif response.type == 'progress_log':
            return {'task_type': TaskType.PROGRESS_LOG}
        return {'task_type': TaskType.UNKNOWN}

    
    @log_function_call
    def node_check_tasks(self, state):

        if state['task_type'] == TaskType.PROGRESS_LOG:
            return "node_save_progress_log"
        elif state['task_type'] == TaskType.UNKNOWN:
            return "node_task_unknown"
        return "node_plan"


    @log_function_call
    def node_save_progress_log(self, state):
        log = state['messages'][-1].content
        user_id = state['user_id']
        self.db_manager.create_progress_entry(user_id, log)
        return {'messages': [AIMessage(content="Your log is saved successdully.")]}
    
    
    @log_function_call
    def node_task_unknown(self, state):
        messages = self._get_last_messages(state)
        messages = [
            SystemMessage(content=UNKNOWN_TASK_PROMPT)
        ] + messages
        response = self.llm.invoke(messages)
        return {'messages': [response]}


    @log_function_call
    def node_plan(self, state: UserMessages):
        planner = self.fitness_planner if state['task_type'] == TaskType.FITNESS else self.diet_planner
        planner_state = deepcopy(state)
        planner_state['messages'] = self._get_last_messages(planner_state)
        response = planner.invoke(planner_state)

        plan = response['messages'][-1]
        summary_response = self.summarizer.invoke({"messages": [HumanMessage(content=plan.content)]})
        plan_summarized = summary_response['messages'][-1].content
        
        output = dict()
        output['messages'] = [plan]
        if state['task_type'] == TaskType.FITNESS:
            output['summarized_fitness_plan'] = plan_summarized
        else:
            output['summarized_diet_plan'] = plan_summarized
        return output


    def compile(self):
        graph_builder = StateGraph(self.message_class)
        graph_builder.add_node("node_task_identifier", self.node_task_identifier)
        graph_builder.add_node("node_save_progress_log", self.node_save_progress_log)
        graph_builder.add_node("node_task_unknown", self.node_task_unknown)
        graph_builder.add_node("node_plan", self.node_plan)
        graph_builder.add_edge(START, "node_task_identifier")
        graph_builder.add_conditional_edges("node_task_identifier", self.node_check_tasks)
        graph_builder.add_edge("node_task_unknown", END)
        graph_builder.add_edge("node_plan", END)
        graph_builder.add_edge("node_save_progress_log", END)

        memory = MemorySaver()
        self.graph_compiled = graph_builder.compile(checkpointer=memory)
        return self.graph_compiled


    def _get_last_messages(self, state):
        return state['messages'][-min(len(state['messages']), self.last_messages):]