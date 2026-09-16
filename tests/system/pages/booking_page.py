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
        name_el = self.driver.find_element(*self.name_field)
        name_el.clear()
        name_el.send_keys(name)

        age_el = self.driver.find_element(*self.age_field)
        age_el.clear()
        age_el.send_keys(str(age))

        if is_peak:
            peak_el = self.driver.find_element(*self.peak_box)
            if not peak_el.is_selected():
                peak_el.click()
        if is_frequent:
            freq_el = self.driver.find_element(*self.frequent_box)
            if not freq_el.is_selected():
                freq_el.click()
        if is_holiday:
            hol_el = self.driver.find_element(*self.holiday_box)
            if not hol_el.is_selected():
                hol_el.click()

        btn = self.driver.find_element(*self.submit_button)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        btn.click()

    def get_error(self) -> str:
        return self.driver.find_element(*self.error_text).text