from selenium.webdriver.common.by import By

class BookingPage:
    def __init__(self, driver):
        self.driver = driver
        self.name_field = (By.ID, "passenger_name")
        self.age_field = (By.ID, "passenger_age")
        self.peak_box = (By.ID, "is_peak")
        self.frequent_box = (By.ID, "is_frequent")
        self.holiday_box = (By.ID, "is_holiday")
        self.submit_button = (By.ID, "book_btn")
        self.error_text = (By.ID, "error_msg")

    def book(self, name: str, age: int, is_peak=False, is_frequent=False, is_holiday=False):
        self.driver.find_element(*self.name_field).clear()
        self.driver.find_element(*self.name_field).send_keys(name)
        self.driver.find_element(*self.age_field).clear()
        self.driver.find_element(*self.age_field).send_keys(str(age))
        if is_peak:
            self.driver.find_element(*self.peak_box).click()
        if is_frequent:
            self.driver.find_element(*self.frequent_box).click()
        if is_holiday:
            self.driver.find_element(*self.holiday_box).click()
        self.driver.find_element(*self.submit_button).click()

    def get_error(self) -> str:
        return self.driver.find_element(*self.error_text).text