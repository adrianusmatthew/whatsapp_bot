import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from utils import randomize_wait


class WhatsappDriver:
    def __init__(self) -> None:
        self.driver = webdriver.Chrome()

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

    def open_chat_window(self, contact):
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
        # Now to clear search box for next search
        time.sleep(randomize_wait())
        cancel_search_button = self.driver.find_element(
            By.CSS_SELECTOR,
            'button[aria-label*="Cancel search"]'
        )
        cancel_search_button.click()

    def close_chat_window(self):
        menu_button = self.driver.find_element(By.CSS_SELECTOR, 'div[role="button"][aria-disabled="false"][data-tab="6"][title="Menu"]')
        menu_button.click()
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 'div[aria-label="Close chat"]'
            ))
        )
        close_chat_button = self.driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Close chat"]')
        close_chat_button.click()

    def get_unread_contacts(self):
        unread_contacts = []
        try:
            # Locate the elements that indicate unread messages
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 'div._ahlk span[aria-label*="unread message"]'
                ))
            )
            unread_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 'div._ahlk span[aria-label*="unread message"]'
            )
            for element in unread_elements:
                # Navigate to the contact's parent element to 
                # get the contact name or other info
                contact_element = element.find_element(
                    By.XPATH, './../../../../../div/div'
                )
                contact_name = contact_element.find_element(
                    By.CSS_SELECTOR, 'span[title]'
                ).text
                unread_contacts.append(contact_name)
        except TimeoutException:
            pass

        return unread_contacts

    def get_latest_message_and_contact(self):
        message = ""
        contact = ""
        img_url = ""
        print("Getting latest message and contact")

        # get all messages and take last sent message
        messages = self.driver.find_elements(
            By.CSS_SELECTOR, 'div.message-in span.selectable-text'
        )
        if messages:
            message = messages[-1].text
            print(f"Latest message: {message}")
            sent_img = self.driver.find_elements(
                By.CSS_SELECTOR, 'div.message-in img.x15kfjtz'
            )
            if sent_img:
                sent_img = sent_img[-1]
                if sent_img.get_attribute("alt") == message:
                    img_url = sent_img.get_attribute('src')
                    print(f"With img: {img_url}")

        # get all contacts and take last contact
        contacts = self.driver.find_elements(
            By.CSS_SELECTOR, 'div.message-in div.copyable-text'
        )
        if contacts:
            contact = contacts[-1].get_attribute(
                'data-pre-plain-text'
            )
            contact = contact.split("] ")[-1].split(":")[0]
            print(f"Sent from contact: {contact}")
        return message, img_url, contact

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

    def get_image_base64(self, img_url):
        # this function opens img blob in new tab, gets the base64
        # of it, then closes tab
        self.driver.execute_script(f'window.open("{img_url}");')
        self.driver.switch_to.window(self.driver.window_handles[-1])
        time.sleep(randomize_wait())
        result = self.driver.execute_async_script("""
            var uri = arguments[0];
            var callback = arguments[1];
            var toBase64 = function(buffer) {
                for (var r, n = new Uint8Array(buffer), t = n.length, a = new Uint8Array(4 * Math.ceil(t / 3)), i = new Uint8Array(64), o = 0, c = 0; 64 > c; ++c)
                    i[c] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);
                for (c = 0; t - t % 3 > c; c += 3, o += 4)
                    r = n[c] << 16 | n[c + 1] << 8 | n[c + 2],
                    a[o] = i[r >> 18],
                    a[o + 1] = i[r >> 12 & 63],
                    a[o + 2] = i[r >> 6 & 63],
                    a[o + 3] = i[63 & r];
                return t % 3 === 1 ? (r = n[t - 1], a[o] = i[r >> 2], a[o + 1] = i[r << 4 & 63], a[o + 2] = 61, a[o + 3] = 61) : t % 3 === 2 && (r = (n[t - 2] << 8) + n[t - 1], a[o] = i[r >> 10], a[o + 1] = i[r >> 4 & 63], a[o + 2] = i[r << 2 & 63], a[o + 3] = 61),
                new TextDecoder("ascii").decode(a);
            };
            var xhr = new XMLHttpRequest();
            xhr.responseType = 'arraybuffer';
            xhr.onload = function() { callback(toBase64(xhr.response)); };
            xhr.onerror = function() { callback(xhr.status); };
            xhr.open('GET', uri);
            xhr.send();
            """, img_url)
        if isinstance(result, int):
            raise Exception("Request failed with status %s" % result)
        time.sleep(randomize_wait())
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return result
