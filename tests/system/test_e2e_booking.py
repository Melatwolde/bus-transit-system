import threading
import time
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from src.app import app
from tests.system.pages.booking_page import BookingPage
from tests.system.pages.ticket_page import TicketPage
import uvicorn


@pytest.fixture(scope="session", autouse=True)
def start_server():
  server = uvicorn.Server(
      uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="error")
  )
  t = threading.Thread(target=server.run, daemon=True)
  t.start()
  time.sleep(1.5)
  yield


@pytest.fixture
def browser():
  import os
  opts = Options()
  if os.path.exists("/usr/bin/google-chrome"):
    opts.binary_location = "/usr/bin/google-chrome"
  opts.add_argument("--headless=new")
  opts.add_argument("--no-sandbox")
  opts.add_argument("--disable-dev-shm-usage")
  try:
    path = ChromeDriverManager().install()
    if os.path.basename(path) != "chromedriver":
      path = os.path.join(os.path.dirname(path), "chromedriver")
    driver = webdriver.Chrome(service=Service(path), options=opts)
  except Exception:
    driver = webdriver.Chrome(options=opts)
  driver.implicitly_wait(4)
  yield driver
  driver.quit()


def test_full_user_booking_journey(browser):
  browser.get("http://127.0.0.1:8001")
  booking = BookingPage(browser)
  ticket = TicketPage(browser)

  # 1. Fill details and book
  booking.book("Melat", 25, is_peak=True, is_frequent=True)

  # 2. Check ticket page
  assert "ISSUED" in ticket.get_status_text()
  assert "22.5 ETB" in ticket.get_fare_text()

  # 3. Complete payment
  ticket.pay()
  assert "PAID" in ticket.get_status_text()
  assert len(ticket.get_qr_text()) == 16

  # 4. Conductor scan
  ticket.scan()
  assert "VALIDATED" in ticket.get_status_text()