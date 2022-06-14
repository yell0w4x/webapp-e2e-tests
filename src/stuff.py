import string
import random
from datetime import datetime, timedelta
import time
import os
import traceback
import selenium
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
from contextlib import contextmanager

from defs import DEFAULT_TIMEOUT, DOWNLOAD_DIR, DEFAULT_DELAY


def random_str(length=8):
    return ''.join(random.choice(string.hexdigits) for _ in range(length))


def get_current_day():
    dt = datetime.today()
    return dt.day


def wait_for_element_to_be_visible(driver, selector, timeout=DEFAULT_TIMEOUT):
    wait = WebDriverWait(driver, timeout)    
    return wait.until(EC.visibility_of_element_located((By.XPATH, selector)))


def wait_for_element_to_be_clickable(driver, selector, timeout=DEFAULT_TIMEOUT):
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.element_to_be_clickable((By.XPATH, selector)))


# fixme: this didn't work
# def wait_for_new_window(driver, timeout=DEFAULT_TIMEOUT):
#     wait = WebDriverWait(driver, timeout)
#     return wait.until(EC.new_window_is_opened(driver.window_handles))


@contextmanager
def wait_for_new_window(driver, timeout=DEFAULT_TIMEOUT):
    handles_before = driver.window_handles
    yield
    WebDriverWait(driver, timeout).until(lambda driver: len(handles_before) != len(driver.window_handles))


@contextmanager
def scroll_to_then_back(driver, y, x=0):
    src_x = driver.execute_script('return window.scrollX;')
    src_y = driver.execute_script('return window.scrollY;')
    print(f'window.scrollX={src_x}, window.scrollY={src_y}')

    driver.execute_script(f"window.scrollTo({x}, {y});")
    yield
    driver.execute_script(f"window.scrollTo({src_x}, {src_y});")


def hover_then_click(driver, element_or_selector, double_click=False, delay=DEFAULT_DELAY, timeout=DEFAULT_TIMEOUT):
    if isinstance(element_or_selector, str):
        element_or_selector = wait_for_element_to_be_clickable(driver, element_or_selector, timeout)

    if double_click:
        ActionChains(driver).pause(delay).move_to_element(element_or_selector).pause(delay).click().pause(delay).click().perform()
    else:
        ActionChains(driver).pause(delay).move_to_element(element_or_selector).pause(delay).click().perform()

    return element_or_selector


def hover_then_click_then_send_keys(driver, element_or_selector, keys, delay=DEFAULT_DELAY, clear_first=False):
    if isinstance(element_or_selector, str):
        element_or_selector = wait_for_element_to_be_clickable(driver, element_or_selector)

    if clear_first:
        ActionChains(driver).pause(delay).move_to_element(element_or_selector).pause(delay).click(element_or_selector).perform()
        clear_element(driver, element_or_selector)

    ActionChains(driver).pause(delay).move_to_element(element_or_selector).pause(delay).click(element_or_selector).pause(delay).send_keys_to_element(element_or_selector, keys).perform()

    return element_or_selector


def just_hover(driver, element_or_selector, delay=DEFAULT_DELAY):
    if isinstance(element_or_selector, str):
        element_or_selector = wait_for_element_to_be_visible(driver, element_or_selector)

    ActionChains(driver).pause(delay).move_to_element(element_or_selector).pause(delay).perform()

    return element_or_selector


def clear_element(driver, element_or_selector, delay=DEFAULT_DELAY):
    if isinstance(element_or_selector, str):
        element_or_selector = wait_for_element_to_be_clickable(driver, element_or_selector)

    while element_or_selector.get_property('value'):
        element_or_selector.send_keys(Keys.BACK_SPACE)

    return element_or_selector    


def clear_non_input_element(driver, element_or_selector, delay=DEFAULT_DELAY):
    if isinstance(element_or_selector, str):
        element_or_selector = wait_for_element_to_be_clickable(driver, element_or_selector)

    ActionChains(driver).pause(delay).move_to_element(element_or_selector).pause(delay).click(element_or_selector).perform()

    while element_or_selector.text:
        element_or_selector.send_keys(Keys.BACK_SPACE)

    return element_or_selector


def wait_for_file_to_be_downloaded(file_name, timeout=DEFAULT_TIMEOUT):
    full_fn = os.path.join(DOWNLOAD_DIR, file_name)
    print(f'Waiting for file to download [{full_fn}] {timeout} seconds')

    start = datetime.utcnow()
    end = start + timedelta(seconds=timeout)

    while datetime.utcnow() < end:
        exists = os.path.exists(full_fn)
        if exists:
            size = os.path.getsize(full_fn)
            print(f'File size [{size}] bytes')
            return True
        time.sleep(1)

    return False


def element_text_matches(locator, regexp):
    def _predicate(driver):
        try:
            element_text = driver.find_element(*locator).text
            match = re.search(regexp, element_text)
            return match
        except StaleElementReferenceException:
            return False
    return _predicate


def click_with_js(driver, xpath_selector):
    wait_for_element_to_be_clickable(driver, xpath_selector)
    driver.execute_script(f'document.evaluate(\'{xpath_selector}\', document).iterateNext().dispatchEvent(new Event("click"))')
