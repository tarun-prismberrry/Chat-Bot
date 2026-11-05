
import streamlit as st
from langgraph_backend import workflow
from langchain_core.messages import HumanMessage

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

user_input = st.chat_input('Type here')

if user_input:  # Important: only run after submission
    st.session_state['message_history'].append(
        {'role': 'user', 'content': user_input}
    )

    with st.chat_message('user'):
        st.text(user_input)

    CONFIG = {'configurable': {'thread_id': '1'}}

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
