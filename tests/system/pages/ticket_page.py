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

    def get_status_text(self) -> str:
        return self.driver.find_element(*self.status).text

    def get_fare_text(self) -> str:
        return self.driver.find_element(*self.fare).text

    def get_qr_text(self) -> str:
        return self.driver.find_element(*self.qr).text

    def pay(self):
        self.driver.find_element(*self.pay_btn).click()
        WebDriverWait(self.driver, 5).until(
            lambda d: "PAID" in d.find_element(*self.status).text
        )
    def scan(self):
        self.driver.find_element(*self.scan_btn).click()
        WebDriverWait(self.driver, 5).until(
            lambda d: "VALIDATED" in d.find_element(*self.status).text
        )