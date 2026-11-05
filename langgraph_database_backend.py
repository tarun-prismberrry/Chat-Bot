from langgraph.graph import StateGraph, START, END, add_messages
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from typing import TypedDict, Literal, Annotated
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
import operator
import sqlite3


load_dotenv()
generator_llm = ChatGroq(
    model_name="openai/gpt-oss-20b",
    temperature=0.7,
)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    message = state['messages']
    res = generator_llm.invoke(message)
    return {'messages': res}


conn =sqlite3.connect(database='chatbot.db', check_same_thread=False)

checkpointer = SqliteSaver(conn= conn)
graph = StateGraph(ChatState)

graph.add_node('chat_node', chat_node)

graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

workflow = graph.compile(checkpointer=checkpointer)
def init_chat_table():
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_threads (
            thread_id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'New Chat'
        )
    """)
    conn.commit()

def add_thread(thread_id: str):
    conn.execute(
        """
        INSERT OR IGNORE INTO chat_threads (thread_id, title)
        VALUES (?, 'New Chat')
        """,
        (str(thread_id),)
    )
    conn.commit()

def update_thread_title(thread_id: str, title: str):
    conn.execute(
        """
        UPDATE chat_threads
        SET title = ?
        WHERE thread_id = ?
        """,
        (title, str(thread_id))
    )
    conn.commit()


def retrieve_all_threads():
    rows = conn.execute(
        "SELECT thread_id, title FROM chat_threads"
    ).fetchall()

    return {thread_id: title for thread_id, title in rows}

init_chat_table()
