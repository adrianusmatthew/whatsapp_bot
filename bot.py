import undetected_chromedriver as uc
import random
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def randomize_wait():
    # change wait seconds here
    return random.uniform(1, 3)


def start_webdriver_and_login():
    driver = uc.Chrome()
    driver.get('https://web.whatsapp.com')
    # Await user to login with QR code until search bar shows up
    print("Please scan the QR code to log in to WhatsApp Web.")
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-tab="3"]'))
    )
    print("Logged in successfully")

    return driver


def open_contact_window(driver, contact):
    # Search contact
    print(f"Getting contact: {contact}")
    time.sleep(randomize_wait())
    search_box = driver.find_element(
        By.CSS_SELECTOR,
        'div[contenteditable="true"]'
    )
    search_box.click()
    time.sleep(randomize_wait())
    # This should open message window immediately
    search_box.send_keys(contact)
    search_box.send_keys(Keys.ENTER)


def get_latest_message(driver):
    print("Getting latest message")
    message_bubbles = driver.find_elements(
        By.CSS_SELECTOR, 'div.message-in span.selectable-text'
    )
    if message_bubbles:
        print(f"Latest message: {message_bubbles[-1].text}")
        return message_bubbles[-1].text
    return None


def send_message(driver, message):
    print(f"Sending message: {message}")
    message_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="10"]')
        )
    )
    message_box.click()
    time.sleep(randomize_wait())
    message_box.send_keys(message)
    time.sleep(randomize_wait())
    message_box.send_keys(Keys.ENTER)
    time.sleep(randomize_wait())


# initialize
contact = "Adrian"
driver = start_webdriver_and_login()
open_contact_window(driver, contact)
last_msg = get_latest_message(driver)

while True:
    latest_msg = get_latest_message(driver)
    if latest_msg and latest_msg != last_msg:
        print(f"New message received: {latest_msg}")
        if latest_msg.lower().startswith("hey jarvis"):
            message = "Hey there, JARVIS here ready to assist!"
            send_message(driver, message)
        last_msg = latest_msg
