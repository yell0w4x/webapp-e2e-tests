import pytest
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from stuff import hover_then_click_then_send_keys
from defs import DEFAULT_TIMEOUT


@pytest.mark.nondestructive
def test_google_must_search_for_a_query_string(not_logged_in_selenium, search_for):
    driver = not_logged_in_selenium
    hover_then_click_then_send_keys(driver, '//input[@type="text"]', search_for + Keys.ENTER)
    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
    wait.until(lambda x: driver.title.startswith(search_for))
