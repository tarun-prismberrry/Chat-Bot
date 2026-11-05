from langgraph.graph import StateGraph, START, END, add_messages
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from typing import TypedDict, Literal, Annotated
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.checkpoint.memory import InMemorySaver
import operator


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


checkpointer = InMemorySaver()
graph = StateGraph(ChatState)

graph.add_node('chat_node', chat_node)

graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

workflow = graph.compile(checkpointer=checkpointer)


