import os

import chainlit as cl
from dotenv import load_dotenv
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.planner import PlannerGraph
from agents.prompt import FITNESS_SYSTEM_PROMPT
from db.db_manager import FitnessDB

load_dotenv()


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-05-20",
    
)

db_manager = FitnessDB()

graph = PlannerGraph(llm, db_manager, FITNESS_SYSTEM_PROMPT).compile()


@cl.on_chat_start
async def on_chat_start():
    # Set the graph as the runnable model for the session
    cl.user_session.set("runnable", graph)
    await cl.Message(content="Hello! I am a chatbot. How can I help you?").send()

@cl.on_message
async def on_message(message: cl.Message):

    config = {"configurable": {"thread_id": cl.context.session.id}}
    # Create a callback handler with final answer streaming enabled.
    cb = cl.LangchainCallbackHandler(
        stream_final_answer=True,
        answer_prefix_tokens=["FINAL", "ANSWER"],
    )
    
    final_answer = cl.Message(content="")

    # Use the stream method to asynchronously stream tokens as they are generated.
    async for msg, metadata in graph.astream(
        {"messages": HumanMessage(content=message.content), 'user_id':1},
        stream_mode="messages",
        config=RunnableConfig(callbacks=[cb], **config),
    ):

        # Stream tokens from AI responses token by token
        if isinstance(msg, AIMessage) and ("node_summarize_conversation" != metadata.get("langgraph_node", "")):
            await final_answer.stream_token(msg.content)

