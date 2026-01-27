import streamlit as st
from agent import run_agent
from langchain_core.messages import HumanMessage, AIMessage

st.set_page_config(page_title="Gent AI", page_icon="🤖")

st.title("Gent AI 🤖")
st.subheader("Your Personal Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [] # For LangChain

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What can I do for you today?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Thinking..."):
        try:
            # Generate response
            response = run_agent(prompt, st.session_state.chat_history)
            
            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Update LangChain history
            st.session_state.chat_history.append(HumanMessage(content=prompt))
            st.session_state.chat_history.append(AIMessage(content=response))
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
