import logging
from apscheduler.schedulers.background import BackgroundScheduler
from tools.gmail import send_email
import streamlit as st
from tzlocal import get_localzone

# Configure logging
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.WARNING)

@st.cache_resource
def get_scheduler():
    scheduler = BackgroundScheduler(timezone=str(get_localzone()))
    scheduler.start()
    return scheduler

def execute_scheduled_task(task_prompt: str, model_name: str = "gemini-2.0-flash"):
    """
    Executes a scheduled task by running the agent and emailing the result.
    """
    print(f"⏰ EXECUTING SCHEDULED TASK: {task_prompt}")
    
    # Lazy import to avoid circular dependency
    from agent import run_agent
    
    try:
        # Run the agent
        # We pass an empty chat history as this is a new, isolated task
        result = run_agent(task_prompt, chat_history=[])
        
        output_text = result['output'] if isinstance(result, dict) else result
        model_used = result['model_used'] if isinstance(result, dict) else "Unknown"

        # Email the result to the user (assuming 'me' is the user)
        # In a real multi-user app, we'd need the user's email address passed in
        subject = f"Scheduled Task Result: {task_prompt[:30]}..."
        email_body = f"Task: {task_prompt}\n\nModel Used: {model_used}\n\nResult:\n{output_text}"
        
        print(f"📧 Sending email for task: {task_prompt}")
        
        # We need to know who to send it to. 
        # For this personal assistant, we'll assume the user sends it to themselves.
        # Ideally, we should fetch the user's email address, but 'me' works for the API if we want to send TO me FROM me.
        # But send_email requires a 'to' address. 
        # Let's try to get the user's profile or just hardcode a placeholder if we can't find it.
        # Actually, let's just use the 'get_profile' equivalent or ask user.
        # For now, to keep it simple and robust for a personal bot, 
        # let's try to send to the same email we are authenticated with, 
        # OR just log it if we can't easily find the "to" address.
        # BETTER YET: The 'send_email' tool requires a 'to' address.
        # We will attempt to get the user's email from the profile.
        
        from tools.utils import get_gmail_service
        service = get_gmail_service()
        profile = service.users().getProfile(userId='me').execute()
        user_email = profile['emailAddress']
        
        send_email(to=user_email, subject=subject, message_text=email_body)
        print("✅ Scheduled task executed and email sent.")

    except Exception as e:
        print(f"❌ Error executing scheduled task: {e}")
