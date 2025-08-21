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
    LOG_SUMMARY_PROMPT , 
    RAG_RETRIEVAL_PROMPT
)
from agents.tools import get_search_web_tool , get_search_books_tool
from utils import log_function_call
from agents.enums import PlannerType
from db.retrievers import DocumentRetriever
from lancedb.rerankers import CrossEncoderReranker
import os

class PlannerGraph(Graph):
    
    def __init__(
        self,
        llm,
        db_manager: FitnessDB,
        book_retriever: DocumentRetriever,
        planner_type:PlannerType = PlannerType.FITNESS,
        num_results = 3,
        use_rag_data = True
        # use_web_search = False
    ):
        super().__init__(llm, UserMessages)
        self.db_manager = db_manager
        self.planner_sys_prompt = FITNESS_SYSTEM_PROMPT if planner_type == PlannerType.FITNESS else DIET_PLANNING_SYSTEM_PROMPT
        self.search_web_prompt = WEBSEARCH_PROMPT
        self.search_doc_prompt = RAG_RETRIEVAL_PROMPT
        self.use_rag_data = use_rag_data
        self.planner_type = 'fitness' if planner_type == PlannerType.FITNESS else 'dietry'
        
        self.summarizer = LogSummarizerGraph(llm, db_manager, LOG_SUMMARY_PROMPT).compile() 
        self.book_retriever = book_retriever
        self.search_doc = get_search_books_tool(
            self.book_retriever,
            type_doc = self.planner_type,
            num_results = num_results
         )
        self.planner_type = planner_type
        self.reranker = CrossEncoderReranker(device=os.environ['DEVICE'])

        # self.use_web_search = use_web_search
        # if self.use_web_search:
        #     self.search_web = get_search_web_tool(num_results = num_results)

    

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
    def node_search_doc(self, state):
        user_info = self.db_manager.get_user(state['user_id'])
        prompt = self.search_doc_prompt.format(
            user_info = user_info,
        )
        prompt += self._check_summary(state)
        messages = [
            SystemMessage(
                content=prompt
            )
        ] + state['messages']
        llm_with_tool = self.llm.bind_tools([self.search_doc])
        response = llm_with_tool.invoke(messages )
        return {"messages": [response]}


    @log_function_call
    def node_plan(self, state):
        
        user_info = self.db_manager.get_user(state['user_id'])
        prompt = self.planner_sys_prompt.format(user_info = user_info)
        prompt += self._check_summary(state)
        out = dict()
        selected_context = []
        if self.use_rag_data:
            search_queries = [call['args']['query'] for call in state['messages'][-1].tool_calls]
            main_query = state['messages'][-2].content + "\n" + str(user_info)
            search_results = [self.book_retriever.search(query, self.planner_type.value) for query in search_queries]
            reranked_results = self.reranker.rerank_multivector(search_results, main_query, deduplicate=True).to_pandas().to_dict()
            reranked_results = sorted(reranked_results['text'].items())
            reranked_results = [r[1] for r in reranked_results]
            selected_context.extend(reranked_results)

        # if self.use_web_search:
        #     web_contexts = json.loads(state['messages'][-3].content)
        #     selected_context += self._get_top_contexts(web_contexts)
            prompt += self._get_context_prompt(selected_context)
            out['contexts'] = selected_context
        
        messages = [
             SystemMessage(
                content = prompt
            )
        ] + state['messages']
        response = self.llm.invoke(messages)
        out['messages'] = [response]
        return out
    
    
    def compile(self):
        graph_builder = StateGraph(self.message_class)
        graph_builder.add_node("node_log_summary", self.node_log_summary)

        if self.use_rag_data:
            graph_builder.add_node("node_search_doc", self.node_search_doc)
            # graph_builder.add_node("node_search_doc_tool", ToolNode([self.search_doc]))
        
        graph_builder.add_node("node_plan", self.node_plan)
        
        # graph_builder.add_node("node_search_web", self.node_search_web) 
        # graph_builder.add_node("node_search_web_tool", ToolNode([self.search_web]))

        if self.use_rag_data:
            graph_builder.add_edge(START, "node_log_summary")
            graph_builder.add_edge("node_log_summary", "node_search_doc")
            # graph_builder.add_edge("node_log_summary", "node_search_web")
            # graph_builder.add_edge("node_search_web", "node_search_web_tool")
            # graph_builder.add_edge("node_search_doc", "node_search_doc_tool")
            graph_builder.add_edge("node_search_doc", "node_plan")
            graph_builder.add_edge("node_plan", END)
            self.graph_compiled = graph_builder.compile(checkpointer=False)
        else:
            graph_builder.add_edge(START, "node_log_summary")
            graph_builder.add_edge("node_log_summary", "node_plan")
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

        selected_contexts = set()
        sorted_contexts = sorted(contexts, key = lambda x: x['score'])
        sorted_contexts = [c['content'] for c in sorted_contexts]
        for context in sorted_contexts:
            selected_contexts.add(context)
            if len(selected_contexts) == top_n:
                break
        return list(selected_contexts)
    
    
    def _get_context_prompt(self, contexts):
        if not contexts:
            return ""
        return """
        \n\n
        # Web Search Results
        
        {contexts}
        """.format(contexts = '\n\n'.join(contexts))
        
        