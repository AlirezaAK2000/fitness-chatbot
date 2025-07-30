import os

import chainlit as cl
from dotenv import load_dotenv
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.planner import PlannerGraph
from db.db_manager import FitnessDB
from werkzeug.security import check_password_hash
# from langchain_openai import ChatOpenAI

load_dotenv()


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-05-20",
    
)

db_manager = FitnessDB()
graph = PlannerGraph(llm, db_manager).compile()


@cl.password_auth_callback
def auth_callback(username: str, password: str):

    user = db_manager.get_user_by_email(username)
    if user and check_password_hash(user['password_hash'], password):
        return cl.User(
            identifier="user", metadata={"user_id": user['user_id'], "first_name": user['first_name']}
        )
    else:
        return None


@cl.on_chat_start
async def on_chat_start():
    # Set the graph as the runnable model for the session
    cl.user_session.set("runnable", graph)
    app_user = cl.user_session.get("user")
    await cl.Message(f"Hello {app_user.metadata['first_name']}").send()


@cl.on_message
async def on_message(message: cl.Message):

    app_user = cl.user_session.get("user")
    user_id = app_user.metadata['user_id']

    config = {"configurable": {"thread_id": cl.context.session.id}}
    # Create a callback handler with final answer streaming enabled.
    cb = cl.LangchainCallbackHandler(
        stream_final_answer=True,
        answer_prefix_tokens=["FINAL", "ANSWER"],
    )
    
    final_answer = cl.Message(content="")

    # Use the stream method to asynchronously stream tokens as they are generated.
    async for msg, metadata in graph.astream(
        {"messages": HumanMessage(content=message.content), 'user_id':user_id},
        stream_mode="messages",
        config=RunnableConfig(callbacks=[cb], **config),
    ):

        # Stream tokens from AI responses token by token
        if isinstance(msg, AIMessage) and ("summarize" not in metadata.get("langgraph_node", "")):
            await final_answer.stream_token(msg.content)

