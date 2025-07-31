from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from agents.graph import Graph
from db.db_manager import FitnessDB
from agents.schema import UserMessages
from langgraph.prebuilt import ToolNode
import json
from agents.summarizer import LogSummarizerGraph
from agents.prompt import (
    FITNESS_SYSTEM_PROMPT,
    DIET_PLANNING_SYSTEM_PROMPT,
    WEBSEARCH_PROMPT,
    LOG_SUMMARY_PROMPT
)
from agents.tools import get_search_web_tool
from utils import log_function_call
from agents.enums import PlannerType

class PlannerGraph(Graph):
    
    def __init__(
        self,
        llm,
        db_manager: FitnessDB,
        planner_type:PlannerType = PlannerType.FITNESS,
        web_num_results = 5
    ):
        super().__init__(llm, UserMessages)
        self.db_manager = db_manager
        self.planner_sys_prompt = FITNESS_SYSTEM_PROMPT if planner_type == PlannerType.FITNESS else DIET_PLANNING_SYSTEM_PROMPT
        self.search_web_prompt = WEBSEARCH_PROMPT
        self.summarizer = LogSummarizerGraph(llm, db_manager, LOG_SUMMARY_PROMPT).compile() 
        self.search_web = get_search_web_tool(num_results=web_num_results)
        self.planner_type = planner_type
    

    @log_function_call
    def node_log_summary(self, state):
        log_summarized_msgs = self.summarizer.invoke({'user_id': state['user_id']})
        if log_summarized_msgs['messages']:
            return {'log_summary': log_summarized_msgs['messages'][0].content}
        return {'log_summary': None}
        

    @log_function_call
    def node_search_web(self, state):
        user_info = self.db_manager.get_user(state['user_id'])
        prompt = self.search_web_prompt.format(
            user_info = user_info,
        )
        prompt += self._check_summary(state)
        messages = [
            SystemMessage(
                content=prompt
            )
        ] + state['messages']
        llm_with_tool = self.llm.bind_tools([self.search_web])
        response = llm_with_tool.invoke(messages )
        return {"messages": [response]}
    

    @log_function_call
    def node_plan(self, state):
        
        user_info = self.db_manager.get_user(state['user_id'])
        prompt = self.planner_sys_prompt.format(user_info = user_info)
        prompt += self._check_summary(state)
        contexts = json.loads(state['messages'][-1].content)
        selected_context = self._get_top_contexts(contexts)
        prompt += self._get_context_prompt(selected_context)
        
        messages = [
             SystemMessage(
                content = prompt
            )
        ] + state['messages']
        response = self.llm.invoke(messages)
        return {'messages': response}
    
    
    def compile(self):
        graph_builder = StateGraph(self.message_class)
        graph_builder.add_node("node_log_summary", self.node_log_summary)
        graph_builder.add_node("node_search_web", self.node_search_web)
        graph_builder.add_node("node_search_web_tool", ToolNode([self.search_web]))
        graph_builder.add_node("node_plan", self.node_plan)
        graph_builder.add_edge(START, "node_log_summary")
        graph_builder.add_edge("node_log_summary", "node_search_web")
        graph_builder.add_edge("node_search_web", "node_search_web_tool")
        graph_builder.add_edge("node_search_web_tool", "node_plan")
        graph_builder.add_edge("node_plan", END)
        self.graph_compiled = graph_builder.compile(checkpointer=False)
        return self.graph_compiled


    def _check_summary(self, state):
        if not state.get('log_summary'):
            return ""
        
        return """
        \n\n
        # Progress Log of User

        Here is the summary of the user's last activities:
        {log}
        """.format(log = state['log_summary'])
    
    
    def _get_top_contexts(self, contexts, top_n = 5):
        if not contexts:
            return []
        print(contexts[0].keys())
        sorted_contexts = sorted(contexts, key = lambda x: x['score'])
        sorted_contexts = [c['content'] for c in sorted_contexts]
        return sorted_contexts[-min(top_n, len(sorted_contexts)):]
    
    
    def _get_context_prompt(self, contexts):
        if not contexts:
            return ""
        return """
        \n\n
        # Web Search Results
        
        {contexts}
        """.format(contexts = '\n\n'.join(contexts))
        
        