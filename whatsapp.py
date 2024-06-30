import undetected_chromedriver as uc
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from utils import randomize_wait


class WhatsappDriver:
    def __init__(self) -> None:
        self.driver = uc.Chrome()

    def start_webdriver_and_login(self):
        self.driver.get('https://web.whatsapp.com')
        # Await user to login with QR code until search bar shows up
        print("Please scan the QR code to log in to WhatsApp Web.")
        WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 'div[data-tab="3"]'
            ))
        )
        print("Logged in successfully")

    def open_contact_window(self, contact):
        # Search contact
        print(f"Getting contact: {contact}")
        time.sleep(randomize_wait())
        search_box = self.driver.find_element(
            By.CSS_SELECTOR,
            'div[contenteditable="true"]'
        )
        search_box.click()
        time.sleep(randomize_wait())
        # This should open message window immediately
        search_box.send_keys(contact)
        search_box.send_keys(Keys.ENTER)

    def get_latest_message_and_contact(self):
        message = ""
        contact = ""
        print("Getting latest message and contact")

        # get all messages and take last sent message
        messages = self.driver.find_elements(
            By.CSS_SELECTOR, 'div.message-in span.selectable-text'
        )
        if messages:
            message = messages[-1].text
            print(f"Latest message: {message}")

        # get all contacts and take last contact
        contacts = self.driver.find_elements(
            By.CSS_SELECTOR, 'div.message-in div.copyable-text'
        )
        if contacts:
            contact = contacts[-1].get_attribute(
                'data-pre-plain-text'
            ).split("] ")[-1]
            print(f"Sent from contact: {contact}")
        return message, contact

    def send_message(self, message):
        print(f"Sending message: {message}")
        message_box = WebDriverWait(self.driver, 10).until(
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
