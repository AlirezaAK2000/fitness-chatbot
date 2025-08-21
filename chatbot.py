import os

import chainlit as cl
from dotenv import load_dotenv
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.main import MainGraph
from db.db_manager import FitnessDB
from werkzeug.security import check_password_hash
# from langchain_openai import ChatOpenAI

WELCOME_MESSAGE = """
**👋 Welcome to Your Personal Fitness Assistant!**

Hello {first_name},
I’m here to help you achieve your health and fitness goals with smart, personalized guidance. Here’s what I can do for you:

### ✅ **1. Create a Custom Workout Plan**
- Tailored to your **goals** (weight loss, muscle gain, endurance, etc.)
- Adjusted for your **fitness level**, available equipment, and schedule
- Includes **warm-up, main workout, and cool-down** with clear instructions and benefits

### ✅ **2. Design a Personalized Diet Plan**
- Matches your **dietary preferences** (vegetarian, gluten-free, etc.)
- Aligned with your **fitness goals and calorie needs**
- Provides balanced meals, snacks, and **macro breakdowns** (optional)
- Simple, practical, and easy to follow

### ✅ **3. Log and Track Your Progress**
- Share your workout or diet details (e.g., “July 10: 5x5 squats at 85 kg, 20-min run”)
- I’ll save your progress so you can **stay on track and review later**
- Can summarize your logs into **clear progress reports**

---

💡 **How to Get Started:**
- To **create a workout plan**, tell me your goal (e.g., “I want to build strength and train 4 days/week”)
- To **design a diet plan**, share your preferences (e.g., “I’m vegetarian and want to lose weight”)
- To **log progress**, just type your recent workout or meal details (e.g., “July 15: 30-min run, felt great”)

I’m here to keep you consistent, informed, and motivated!  
**What would you like to do first — workout plan, diet plan, or log your progress?**

"""

load_dotenv()


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-05-20",
    
)

db_manager = FitnessDB()
graph = MainGraph(llm, db_manager).compile()


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
    await cl.Message(WELCOME_MESSAGE.format(first_name = app_user.metadata['first_name'])).send()


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

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)