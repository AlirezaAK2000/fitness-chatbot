from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from agents.graph import Graph
from db.db_manager import FitnessDB
from agents.state_schema import UserMessages

class PlannerGraph(Graph):
    
    def __init__(self, llm, db_manager: FitnessDB, planner_sys_prompt: str):
        super().__init__(llm, UserMessages)
        self.db_manager = db_manager
        self.planner_sys_prompt = planner_sys_prompt
        self.llm = llm
    
    
    def node_plan(self, state):
        
        user_info = self.db_manager.get_user(state['user_id'])
        messages = [
            SystemMessage(
                content = self.planner_sys_prompt.format(user_info = user_info)
            )
        ]
        response = self.llm.invoke(messages + state['messages'])
        state['messages'].append(response)
        return response

    
    def compile(self):
        graph_builder = StateGraph(self.message_class)
        graph_builder.add_node("node_plan", self.node_plan)
        graph_builder.add_edge(START, "node_plan")
        graph_builder.add_edge("node_plan", END)
        self.graph_compiled = graph_builder.compile()
        return self.graph_compiled
        
        
        
        