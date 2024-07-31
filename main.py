import time
from whatsapp import WhatsappDriver
from ai_llm import LanguageModel
from dotenv import load_dotenv
from utils import is_prompt_message

# load langchain and openai env vars
load_dotenv(".env")

# initialize
target_chat = "JJBA"
last_msg = ""
start_message = "Yinlin AI is now online!"
print(start_message)

driver = WhatsappDriver()
driver.start_webdriver_and_login()
driver.open_chat_window(target_chat)
driver.send_message(start_message)

language_model = LanguageModel()

while True:
    try:
        latest_msg, img_url, contact = driver.get_latest_message_and_contact()
        if latest_msg and latest_msg != last_msg:
            print(f"New message received from {contact}: {latest_msg}")
            if img_url:
                print(f"With img: {img_url}")
                img_base64 = driver.get_image_base64(img_url)
            else:
                img_base64 = ""
            if is_prompt_message(latest_msg):
                # check contact who sent message, check or make msg history,
                # get prompt and generate response
                ai_message = language_model.get_llm_response(
                    text=f"{contact} said: {latest_msg}",
                    session_id=contact,
                    img_base64=img_base64
                )
                driver.send_message(message=ai_message)
        last_msg = latest_msg
    except Exception as e:
        print("An error occurred: ", e)
    time.sleep(1)
