import os
from whatsapp import WhatsappDriver
from ai_llm import (
    create_session_id,
    get_llm_response
)
from dotenv import load_dotenv
from utils import is_prompt_message

# load langchain and openai env vars
load_dotenv(".env")

LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT")

# initialize
contact = "Adrian"
last_msg = ""
start_message = "JOJO is now online!"
print(start_message)

driver = WhatsappDriver()
driver.start_webdriver_and_login()
driver.open_contact_window(contact)
driver.send_message(start_message)

while True:
    latest_msg, contact = driver.get_latest_message_and_contact()
    if latest_msg and latest_msg != last_msg:
        print(f"New message received from {contact}: {latest_msg}")
        if is_prompt_message(latest_msg):
            # check contact who sent message, check or make msg history,
            # get prompt and generate response
            session_id = create_session_id(contact)
            ai_message = get_llm_response(latest_msg, session_id)
            driver.send_message(driver, ai_message)
        last_msg = latest_msg
