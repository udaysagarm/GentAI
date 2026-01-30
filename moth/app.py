import streamlit as st
from agent import run_agent
from langchain_core.messages import HumanMessage, AIMessage

st.set_page_config(page_title="Moth AI", page_icon="🦋")
print("Moth AI (Model: Gemini 2.0)")

st.title("Moth AI")
st.subheader("Your Personal Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [] # For LangChain

# Initialize Background Scheduler
# Initialize Background Scheduler
from scheduler_engine import get_scheduler
scheduler = get_scheduler()

# Sidebar for Active Schedules
st.sidebar.title("⏳ Active Schedules")
scheduler = get_scheduler()
jobs = scheduler.get_jobs()
if jobs:
    for job in jobs:
        col1, col2 = st.sidebar.columns([0.8, 0.2])
        with col1:
            st.write(f"**Task:** {job.name}")
            st.caption(f"Next Run: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        with col2:
            if st.button("🗑️", key=f"del_{job.id}"):
                try:
                    scheduler.remove_job(job.id)
                    st.success("Deleted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        st.sidebar.divider()
else:
    st.sidebar.info("No tasks currently scheduled.")

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
            response_text = run_agent(prompt, st.session_state.chat_history)
            
            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                st.markdown(response_text)
            
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # Update LangChain history
            st.session_state.chat_history.append(HumanMessage(content=prompt))
            st.session_state.chat_history.append(AIMessage(content=response_text))
            
            # Force UI refresh to show new scheduled tasks immediately
            st.rerun()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"DEBUG: App Error Inputs - Prompt: {prompt}, History Type: {type(st.session_state.chat_history)}")
            st.error(f"An error occurred: {e}")
