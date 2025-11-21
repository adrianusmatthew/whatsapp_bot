import traceback
import time
import pprint
from whatsapp import WhatsappDriver
from ai_llm import LanguageModel
from dotenv import load_dotenv
from utils import is_prompt_message

# load env vars and initialize in general
load_dotenv(".env")
start_message = "Yinlin AI is now online!"
print(start_message)
language_model = LanguageModel()
driver = WhatsappDriver()
driver.start_webdriver_and_login()
operation_type = input("Enter chat operation type (single or multiple): ")

# initialize for single chat window
if operation_type.lower() == "single":
    target_chat = input("Enter target chat name (case sensitive): ")
    last_msg = ""
    driver.open_chat_window(target_chat)
    driver.send_message(start_message)

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
                    # check contact who sent message, check or make
                    # msg history, get prompt and generate response
                    ai_messages = language_model.get_llm_response(
                        text=f"{contact} said: {latest_msg}",
                        session_id=target_chat,
                        img_base64=img_base64
                    )
                    for ai_message in ai_messages:
                        driver.send_message(message=ai_message)
            last_msg = latest_msg
        except Exception:
            traceback.print_exc()
        time.sleep(1)

elif operation_type.lower() == "multiple":
    # initialize for multi chat windows
    last_msg_dict = {}
    pp = pprint.PrettyPrinter(indent=4)

    while True:
        try:
            # get all unread contacts
            unread_contacts = driver.get_unread_contacts()
            if unread_contacts:
                for unread_contact in unread_contacts:
                    # open chat window of contact, get latest msg
                    driver.open_chat_window(unread_contact)
                    latest_msg, img_url, contact = driver.get_latest_message_and_contact()
                    if unread_contact not in last_msg_dict:
                        # initialize latest chat for contact
                        last_msg_dict[unread_contact] = "New contact!"
                    latest_msg_from_contact = contact + " said: " + latest_msg
                    if last_msg_dict[unread_contact] != latest_msg_from_contact:
                        print(f"New message received from {contact}: {latest_msg}")
                        if img_url:
                            print(f"With img: {img_url}")
                            img_base64 = driver.get_image_base64(img_url)
                        else:
                            img_base64 = ""
                        # check if latest msg is prompt msg
                        if is_prompt_message(latest_msg):
                            ai_message = language_model.get_llm_response(
                                text=latest_msg_from_contact,
                                session_id=unread_contact,
                                img_base64=img_base64
                            )
                            driver.send_message(message=ai_message)
                        last_msg_dict[unread_contact] = latest_msg_from_contact
                    # driver.close_chat_window()
            pp.pprint(last_msg_dict)
        except Exception:
            traceback.print_exc()
        time.sleep(1)
