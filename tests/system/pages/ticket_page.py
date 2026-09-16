from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TicketPage:
    def __init__(self, driver):
        self.driver = driver
        self.status = (By.ID, "ticket_status")
        self.fare = (By.ID, "fare_display")
        self.qr = (By.ID, "qr_code_display")
        self.pay_btn = (By.ID, "pay_btn")
        self.scan_btn = (By.ID, "scan_btn")

    def _wait_for_element(self, locator, timeout: int = 10):
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )

    def get_status_text(self) -> str:
        element = self._wait_for_element(self.status)
        return element.text

    def get_fare_text(self) -> str:
        element = self._wait_for_element(self.fare)
        return element.text

    def get_qr_text(self) -> str:
        element = self._wait_for_element(self.qr)
        return element.text

    def pay(self):
        btn = self._wait_for_element(self.pay_btn)
        btn.click()
        WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element(self.status, "PAID")
        )

    def scan(self):
        btn = self._wait_for_element(self.scan_btn)
        btn.click()
        WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element(self.status, "VALIDATED")
        )