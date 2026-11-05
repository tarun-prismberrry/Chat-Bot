
import streamlit as st
from langgraph_backend import workflow
from langchain_core.messages import HumanMessage
import uuid

def generate_thread_id():
    thread_id=uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] =thread_id
    add_thread(st.session_state['thread_id'])

    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'][thread_id]='New Chat'

def load_conversation(thread_id):
    return workflow.get_state(config={'configurable': {'thread_id': thread_id}}).values.get('messages',[])

def generate_title(user_input):
    title = user_input.strip().replace("\n", " ")
    return title[:30] + "..." if len(title) > 30 else title

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = {}

add_thread(st.session_state['thread_id'])

st.sidebar.title('Langraph Chatbot')

if st.sidebar.button('New Chat'):
    reset_chat()

st.sidebar.header('My Conversations')

# for thread_id in st.session_state['chat_threads'][::-1]:
#     if st.sidebar.button(thread_id):
#         st.session_state['thread_id'] = thread_id
#         messages=load_conversation(thread_id)

#         temp_messages =[]
#         for message in messages:
#             if isinstance(message, HumanMessage):
#                 role ='user'
#             else:
#                 role='assistant'
#             temp_messages.append({'role': role, 'content': message.content})
#         st.session_state['message_history'] = temp_messages

for thread_id, title in  reversed(list(st.session_state['chat_threads'].items())):
    if st.sidebar.button(title, key= str(thread_id)):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_messages=[]
        for message in messages:
            if isinstance(message, HumanMessage):
                role='user'
            else:
                role='assistant'
            temp_messages.append({'role':role, 'content': message.content})
        st.session_state['message_history'] = temp_messages
        st.rerun()

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

user_input = st.chat_input('Type here')

if user_input: 
    thread_id = st.session_state['thread_id']
    if st.session_state['chat_threads'][thread_id] == "New Chat":
        st.session_state['chat_threads'][thread_id] = generate_title(user_input) # Important: only run after submission
    st.session_state['message_history'].append(
        {'role': 'user', 'content': user_input}
    )

    with st.chat_message('user'):
        st.text(user_input)

    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}

    def generate_response():
        for chunk in workflow.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config=CONFIG,
            stream_mode='messages',
            version='v2'
        ):
            if chunk['type'] == 'messages':
                message_chunk, metadata = chunk['data']

                if isinstance(message_chunk.content, str):
                    if message_chunk.content:
                        yield message_chunk.content

    with st.chat_message('assistant'):
        ai_message = st.write_stream(generate_response())

    st.session_state['message_history'].append(
        {'role': 'assistant', 'content': ai_message}
    )
