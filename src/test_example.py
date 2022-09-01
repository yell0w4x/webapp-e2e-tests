import pytest
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from stuff import hover_then_click_then_send_keys, wait_for_element_to_be_clickable, \
    just_hover, wait_for_element_to_be_visible
from defs import DEFAULT_TIMEOUT


@pytest.mark.nondestructive
def test_google_must_search_for_a_query_string(not_logged_in_selenium, search_for):
    driver = not_logged_in_selenium
    hover_then_click_then_send_keys(driver, '//input[@type="text"]', search_for + Keys.ENTER)
    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
    wait.until(lambda x: driver.title.startswith(search_for))


@pytest.fixture
def product_in_basket(not_logged_in_selenium):
    def empty_cart_element_void(driver):
        try:
            driver.find_element(
                By.XPATH, '//ul[contains(@class, "cart-dropdown")]//p//span[text()="Your basket is empty. Start shopping now!"]')
            return False
        except BaseException as e:
            return True

    driver = not_logged_in_selenium
    just_hover(driver, '//div[contains(@class, "dropdown checkout-section")]')
    wait_for_element_to_be_visible(driver, 
        '//ul[contains(@class, "cart-dropdown")]//p//span[text()="Your basket is empty. Start shopping now!"]')
    just_hover(driver, '//input[@id="input"]')

    wait_for_element_to_be_clickable(driver, '(//div[contains(@class, "owl-item")]//button[@qa="add"])[1]').click()
    just_hover(driver, '//div[contains(@class, "dropdown checkout-section")]')
    WebDriverWait(driver, DEFAULT_TIMEOUT).until(empty_cart_element_void)


@pytest.mark.nondestructive
def test_big_basket_must_show_product_in_cart(product_in_basket):
    pass
