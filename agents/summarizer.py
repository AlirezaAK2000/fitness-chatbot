from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from agents.graph import Graph
from db.db_manager import FitnessDB
from agents.state_schema import UserMessages


class SummarizerGraph(Graph):
    def __init__(self, llm, db_manager: FitnessDB, prompt: str, num_logs = 5):
        super().__init__(llm, UserMessages)
        self.db_manager = db_manager
        self.prompt = prompt
        self.num_logs = num_logs
        

    def node_summarize(self, state):
        logs = self.db_manager.get_last_progress(state['user_id'], num_logs=self.num_logs)
        if len(logs) == 0:
            return state
        
        logs = [log['details'] for log in logs]
        
        messages = [
            SystemMessage(
                content = self.prompt.format(logs = logs)
            )
        ]
        response = self.llm.invoke(messages)
        state['messages'].append(response)
        return state
    

    def compile(self):
        graph_builder = StateGraph(self.message_class)
        graph_builder.add_node("node_summarize", self.node_summarize)
        graph_builder.add_edge(START, "node_summarize")
        graph_builder.add_edge("node_summarize", END)
        self.graph_compiled = graph_builder.compile()
        return self.graph_compiled