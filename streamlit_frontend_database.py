
import streamlit as st
from langgraph_tool_backend import workflow, retrieve_all_threads, update_thread_title, add_thread
from langchain_core.messages import HumanMessage, AIMessageChunk, AIMessage, ToolMessage, SystemMessage
import uuid
import tempfile 
import os 
from rag_pipeline import ingest_document

def generate_thread_id():
    thread_id=uuid.uuid4()
    return str(thread_id)

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] =thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['chat_threads'] = retrieve_all_threads()

    st.session_state['message_history'] = []

# def add_thread(thread_id):
#     if thread_id not in st.session_state['chat_threads']:
#         st.session_state['chat_threads'][thread_id]='New Chat'


def get_display_content(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))

        return "\n".join(parts)

    return ""



def load_conversation(thread_id):
    messages = workflow.get_state(
        config={"configurable": {"thread_id": thread_id}}
    ).values.get("messages", [])



    temp_messages = []
    for message in messages:
        print("MESSAGE TYPE:", type(message))
        print("MESSAGE:", message)
    for message in messages:

        # Handle dictionary messages
        if isinstance(message, dict):
            role = message.get("role")
            content = message.get("content", "")

            if role in ("user", "assistant") and content:
                temp_messages.append({
                    "role": role,
                    "content": get_display_content(content)
                })

            continue

        # Handle LangChain messages
        if isinstance(message, HumanMessage):
            role = "user"

        elif isinstance(message, AIMessage):
            if message.tool_calls:
                continue
            role = "assistant"

        else:
            # Ignore ToolMessage and other internal messages
            continue

        content = get_display_content(message.content)

        if content:
            temp_messages.append({
                "role": role,
                "content": content
            })

    return temp_messages

def generate_title(user_input):
    title = user_input.strip().replace("\n", " ")
    return title[:30] + "..." if len(title) > 30 else title


# ************Session SETUP **************************

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

add_thread(st.session_state['thread_id'])

st.sidebar.title('Langraph Chatbot')

if st.sidebar.button('New Chat'):
    reset_chat()


uploaded_file = st.sidebar.file_uploader(
    "Upload a document",
    type = ["pdf", "txt", "docx"]
)
if uploaded_file is not None:

    if st.sidebar.button("Process document"):

        suffix = os.path.splitext(uploaded_file.name)[1]

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name

        try:
            result = ingest_document(
                file_path=temp_path,
                thread_id=st.session_state["thread_id"],
            )

            st.sidebar.success(
                f"Processed {result['chunks_created']} chunks"
            )

        finally:
            os.remove(temp_path)



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


for thread_id, title in reversed(
    list(st.session_state['chat_threads'].items())
):
    if st.sidebar.button(title, key=str(thread_id)):

        st.session_state['thread_id'] = thread_id

        st.session_state['message_history'] = load_conversation(
            thread_id
        )

        st.rerun()




for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

user_input = st.chat_input('Type here')

if user_input: 
    thread_id = st.session_state['thread_id']
    if st.session_state['chat_threads'].get(thread_id, "New Chat")== "New Chat":
        title = generate_title(user_input) # Important: only run after submission
        update_thread_title(thread_id, title)
        st.session_state['chat_threads'][thread_id]= title
    st.session_state['message_history'].append(
        {'role': 'user', 'content': user_input}
    )
 
    with st.chat_message('user'):
        st.text(user_input)

    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']},
              'metadata': {'thread_id': st.session_state['thread_id']},
              'run_name': 'chat_turn'}

    def generate_response(status):
        """Stream visible text while updating the agent's progress"""
        current_phase = 'thinking'
        for chunk in workflow.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config=CONFIG,
            stream_mode=['messages', 'updates'],
            version='v2'
        ):
            if chunk['type'] == 'updates':
                updates = chunk['data']
                
                if "chat_node" in updates:
                    node_updates = updates['chat_node']
                    messages= node_updates.get('messages',[])
                    if isinstance(messages, list):
                        last = messages[-1] if messages else None
                    else:
                        last = messages
                    if last is not None:
                        tool_calls = getattr(last, "tool_calls", [])

                        if tool_calls:
                            names=[
                                call.get("name", "tool")
                                for call in tool_calls
                            ]
                            status.update(
                                label=f"Running: {','.join(names)}",
                                state='running',
                                expanded = True
                            )
                            current_phase = 'tools'
                    if 'tools' in updates:
                        status.update(
                            label="Tools finished. Perparing the answer .....",
                            state= 'running',
                            expanded = True
                        )
                        current_phase = 'answer '
            elif chunk['type'] == 'messages':
                message_chunk, metadata = chunk['data']
                if metadata.get('langgraph_node')!='chat_node':
                    continue
                if isinstance(message_chunk, AIMessageChunk):
                    if isinstance(message_chunk.content, str) :
                        if message_chunk.content:
                            if current_phase != 'answer':
                                status.update(
                                    label ="Generating answer...",
                                    state= 'running',
                                    expanded = True
                                )
                                current_phase='answer'
                            yield message_chunk.content


    with st.chat_message('assistant'):
        with st.status("Thinking about your question....", expanded=True) as status:
            try:
                reponse_parts = list(generate_response(status))
                ai_message = "".join(reponse_parts)
                status.update(
                    label = 'Response complete',
                    state='complete',
                    expanded=False
                )
            except Exception as e:
                status.update(
                    label="Something went wrong",
                    state='error',
                    expanded=True
                )
                st.error(f"Error generating response: {e}")
                raise
        st.markdown(ai_message)
        

    st.session_state['message_history'].append(
        {'role': 'assistant', 'content': ai_message}
    )
