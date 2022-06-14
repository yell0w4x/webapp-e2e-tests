import base64
import contextlib
import os
import pathlib
import pytest
import re
import shutil
import subprocess
import shlex
import time
import binascii
import psycopg
from image_hex import image
from datetime import datetime
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from defs import DEFAULT_SUT_LOCAITON, DEFAULT_TIMEOUT, DEFAULT_API_BASE_URL, FIREFOX_PROFILE
from stuff import hover_then_click, wait_for_element_to_be_visible, get_current_day, random_str, \
    hover_then_click_then_send_keys, wait_for_element_to_be_clickable, scroll_to_then_back, \
    clear_element, click_with_js

LOG_DIR = '/tmp/logs'
FAILURE_DIR = '/tmp/failure_logs'
USER_DATA_DIR = '/chrome-user-data-dir'
VIDEO_PATH = "/tmp/screen.mkv"
CPUSTAT_PATH = "/tmp/cpustat.log"
FIREFOX_LOG_FN = 'firefox.log'
FIREFOX_SRC_LOG_FN = f"/tmp/{FIREFOX_LOG_FN}"
FIREFOX_DEST_LOG_FN = f'{FIREFOX_SRC_LOG_FN}.moz_log'
FULL_HTTP_LOG_FN = '/tmp/full-http.log'
HTTP_LOG_FN = '/tmp/http.log'


# pylint: disable=maybe-no-member

def pytest_addoption(parser):
    parser.addoption('--search-for', action='store', default='please write tests', 
        help='Example argument to show how to pass args to tests from cli (default: \'please write tests\')')
    parser.addoption('--destructive', action='store_true', help='Run the tests marked @destructive)')
    parser.addoption('--sut-location', action='store', default=DEFAULT_SUT_LOCAITON, help=f'Sut location (default: {DEFAULT_SUT_LOCAITON} is RC)')
    parser.addoption('--api-base-url', action='store', default=DEFAULT_API_BASE_URL, help=f'Environment api base url (default: {DEFAULT_API_BASE_URL} is RC)')
    parser.addoption('--google-account', action='store', default='', 
        help='Google account to use for authorization if there is (default: \'\')')
    parser.addoption('--record-screen', action='store_true', default=False, help='Record screen for every running test')
    parser.addoption('--skip-db-wipe', action='store_true', default=False, help='Don\'t wipe database on RC')
    parser.addoption('--collect-logs', action='store_true', help='Collect passed test logs')
    parser.addoption('--open-dev-tools', action='store_true', help='Opens dev tools on browser start')
    parser.addoption('--open-js-console', action='store_true', help='Opens js console on browser start')


def pytest_runtest_setup(item):
    if 'nondestructive' in item.keywords:
        return
    elif 'destructive' in item.keywords:
        if not item.config.getoption('--destructive'):
            pytest.skip('need --destructive option to run this test')
    else:
        raise RuntimeError('Each test should be marked either as destructive or as nondestructive')


def pytest_generate_tests(metafunc):
    def prepare(s):
        return s.replace("'", '').replace('"', '').lower().strip()

    # HINT:
    #
    # Another way to pass search_for argument to a test
    # if 'search_for' in metafunc.fixturenames:
    #     search_for = prepare(metafunc.config.getoption('--search-for'))
    #     print(f'--search-for {search_for}')
    #     metafunc.parametrize('search_for', [search_for]

    # Consider this. If we had --args-list in cli passed as comma separted list 
    # we would be able to pass this list to the pytest.mark.parametrize to 
    # generate test for each value
    # if 'args_list' in metafunc.fixturenames:
    #     values = metafunc.config.getoption('--arg-list')
    #     print(f'--arg-list {values}')
    #     values = [prepare(f) for f in values.split(',')]
    #     metafunc.parametrize('arg_list', values)
    #     )


def pytest_sessionstart(session):
    pass


def get_option(request, name):
    option = request.config.getoption(name)
    print(name, option)
    return option


# By default use fixture wrapper for the args as it's most simple and convenient
@pytest.fixture(scope='session')
def search_for(request):
    return get_option(request, '--search-for')


@pytest.fixture(scope='module')
def sut_location(request):
    return get_option(request, '--sut-location')


@pytest.fixture(scope='module')
def api_base_url(request):
    return get_option(request, '--api-base-url')


@pytest.fixture(scope='session')
def google_account(request):
    return get_option(request, '--google-account')


@pytest.fixture(scope='session')
def skip_db_wipe(request):
    return get_option(request, '--skip-db-wipe')


@pytest.fixture(scope='module')
def collect_logs(request):
    return get_option(request, '--collect-logs')


@pytest.fixture(scope='module')
def open_dev_tools(request):
    return get_option(request, '--open-dev-tools')


@pytest.fixture(scope='module')
def open_js_console(request):
    return get_option(request, '--open-js-console')


@pytest.fixture
def firefox_profile():
    home_dir = os.environ['HOME']
    # HINT: 
    # 
    # Put real firefox profile here with already logged in user into google if you want to test and use 
    # google auth (logged_in_selenium fixture).
    profile = webdriver.FirefoxProfile(os.path.join(home_dir, FIREFOX_PROFILE))
    profile.set_preference("dom.webdriver.enabled", False)
    profile.set_preference('useAutomationExtension', False)
    profile.set_preference('devtools.selfxss.count', 100)
    profile.set_preference("browser.download.folderList", 2)
    profile.set_preference("browser.download.manager.showWhenStarting", False)
    profile.set_preference("browser.helperApps.alwaysAsk.force", False)
    profile.set_preference("browser.download.dir", "/home/chrome/Downloads")
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
    profile.set_preference("network.proxy.type", 1)
    profile.set_preference("network.proxy.socks", "127.0.0.1")
    profile.set_preference("network.proxy.socks_port", 1080)
    profile.update_preferences()

    return profile


@pytest.fixture
def firefox_options(firefox_options, open_dev_tools, open_js_console):
    firefox_options.log.level = "trace"
    firefox_options.add_argument('--MOZ_LOG=timestamp,nsHttp:1,cache2:1,nsHostResolver:1,cookie:1')
    firefox_options.add_argument(f'--MOZ_LOG_FILE={FIREFOX_SRC_LOG_FN}')

    if open_dev_tools:
        firefox_options.add_argument('--devtools')

    if open_js_console:
        firefox_options.add_argument('--jsconsole')

    return firefox_options


@pytest.fixture
def proxy():
    # fixme stdout redirection prevents proxy from exiting
    # with _background_process(f'bash -c "/home/chrome/proxy/mitmdump --showhost --mode socks5 --listen-port 1080 -w {FULL_HTTP_LOG_FN} &> {HTTP_LOG_FN}"'):
    with _background_process(f'bash -c "/home/chrome/proxy/mitmdump --showhost --mode socks5 --listen-port 1080 -w {FULL_HTTP_LOG_FN}"'):
        yield


@pytest.fixture
def logged_in_selenium(proxy, selenium, firefox_options, sut_location, google_account):
    selenium.set_window_size(1920, 1080)
    selenium.set_window_position(0, 0)
    selenium.maximize_window()
    selenium.get(sut_location)
    size = selenium.get_window_size()
    print(f"\033[34mWindow size: width = {size['width']}px, height = {size['height']}px\033[0m")

    wait = WebDriverWait(selenium, DEFAULT_TIMEOUT)
    hover_then_click(selenium, '//i[contains(text(), "account_circle")]')
    hover_then_click(selenium, '//div[@class="q-field__inner relative-position col self-stretch"][1]')
    wait_for_element_to_be_clickable(selenium, f'//div[@data-identifier="{google_account}"]//img')
    hover_then_click(selenium, f'//div[@data-identifier="{google_account}"]', double_click=True, delay=1)

    # HINT:
    # 
    # Put here your page conditions to wait for after authorization
    # to be sure the login completed
    # wait_for_element_to_be_visible(selenium, '//div[contains(@class, "q-img__content")]/ancestor::div[contains(@class, "cursor-pointer")]', timeout=300)

    yield selenium
    selenium.quit()


@pytest.fixture
def not_logged_in_selenium(proxy, selenium, firefox_options, sut_location):
    selenium.set_window_size(1920, 1080)
    selenium.set_window_position(0, 0)
    selenium.maximize_window()
    selenium.get(sut_location)
    size = selenium.get_window_size()
    print(f"\033[34mWindow size: width = {size['width']}px, height = {size['height']}px\033[0m")
    yield selenium
    selenium.quit()


@pytest.fixture
def wait(logged_in_selenium):
    return WebDriverWait(logged_in_selenium, DEFAULT_TIMEOUT)


@pytest.fixture
def wait_nl(not_logged_in_selenium):
    return WebDriverWait(not_logged_in_selenium, DEFAULT_TIMEOUT)


@pytest.fixture
def clear_downloads_dir():
    yield
    os.system('rm -rf /home/chrome/Downloads/*')


# @pytest.fixture
# def capabilities(capabilities):
#     capabilities['acceptSslCerts'] = True
#     capabilities['acceptInsecureCerts'] = True
#     return capabilities


@pytest.fixture(autouse=True)
def logs_capture(request, collect_logs):
    yield
    if not collect_logs:
        return 

    print('logs_capture')
    test_name = request.function.__name__
    if os.path.exists(VIDEO_PATH):
        shutil.copy(VIDEO_PATH, make_artifact_filename(test_name, 'screen.mkv', folder=LOG_DIR))

    if os.path.exists(CPUSTAT_PATH):
        shutil.copy(CPUSTAT_PATH, make_artifact_filename(test_name, 'cpustat.log', folder=LOG_DIR))

    if os.path.exists(FIREFOX_DEST_LOG_FN):
        shutil.copy(FIREFOX_DEST_LOG_FN, make_artifact_filename(test_name, FIREFOX_LOG_FN, folder=LOG_DIR))

    if os.path.exists(FULL_HTTP_LOG_FN):
        subprocess.run(shlex.split(f'bash -c \'python read_proxy_flow.py {FULL_HTTP_LOG_FN} > {make_artifact_filename(test_name, "full-http.log", folder=LOG_DIR)}\''))

    if os.path.exists(HTTP_LOG_FN):
        shutil.copy(HTTP_LOG_FN, make_artifact_filename(test_name, 'http.log', folder=LOG_DIR))


def make_artifact_filename(name, suffix, folder=FAILURE_DIR):
    now = datetime.now()
    dt_string = now.strftime('%Y%m%dT%H%M%S-')
    return os.path.join(folder, f'{dt_string}{get_valid_filename(name)}.{suffix}')


def write_file(name, content, suffix, attrs):
    filename = make_artifact_filename(name, suffix)
    with open(filename, attrs) as f:
        f.write(content)


def pytest_selenium_capture_debug(item, report, extra):
    fixture_request = getattr(item, '_request', None)
    pathlib.Path(FAILURE_DIR).mkdir(parents=True, exist_ok=True)

    driver_log_written = False # at the moment the are two driver logs, second is empty, it looks like a bug
    for log_type in extra:
        if log_type['name'] == 'Driver Log' and not driver_log_written:
            driver_log_written = True
            content = log_type['content']
            write_file(item.name, content, 'driver.log', 'w')
        elif log_type['name'] == 'Browser Log':
            content = log_type['content']
            write_file(item.name, content, 'browser.log', 'w')
        elif log_type['name'] == 'Screenshot':
            content = base64.b64decode(log_type['content'].encode('utf-8'))
            write_file(item.name, content, 'screenshot.png', 'wb')

    if fixture_request.config.getoption('--record-screen'):
        assert os.path.exists(VIDEO_PATH)
        shutil.move(VIDEO_PATH, make_artifact_filename(item.name, 'screen.mkv'))

    assert os.path.exists(CPUSTAT_PATH)
    shutil.move(CPUSTAT_PATH, make_artifact_filename(item.name, 'cpustat.log'))

    assert os.path.exists(FIREFOX_DEST_LOG_FN)
    shutil.move(FIREFOX_DEST_LOG_FN, make_artifact_filename(item.name, FIREFOX_LOG_FN))

    assert os.path.exists(FULL_HTTP_LOG_FN)
    subprocess.run(shlex.split(f'bash -c \'python read_proxy_flow.py {FULL_HTTP_LOG_FN} > {make_artifact_filename(item.name, "full-http.log")}\''))
    os.remove(FULL_HTTP_LOG_FN)

    # assert os.path.exists(HTTP_LOG_FN)
    # shutil.move(HTTP_LOG_FN, make_artifact_filename(item.name, 'http.log'))


def pytest_runtest_logfinish(nodeid, location):
    test_name = location[2]


# def pytest_runtest_teardown(item, nextitem):
#     print('pytest_runtest_teardown', item, nextitem)


def get_valid_filename(s):
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '_', s)


@pytest.helpers.register
def wait_element_to_be_visible_and_enabled(selenium, timeout_in_seconds, locator, allow_stale=True):
    while True:
        try:
            WebDriverWait(selenium, timeout_in_seconds).until(EC.element_to_be_clickable(locator))
            return
        except StaleElementReferenceException:
            if not allow_stale:
                raise


@pytest.helpers.register
def click_element(selenium, timeout_in_seconds, locator, allow_stale=True):
    while True:
        try:
            WebDriverWait(selenium, timeout_in_seconds).until(EC.element_to_be_clickable(locator)).click()
            return
        except StaleElementReferenceException:
            if not allow_stale:
                raise


@pytest.helpers.register
def wait_element_to_be_visible_and_enabled_by_xpath(selenium, xpath, timeout=DEFAULT_TIMEOUT):
    pytest.helpers.wait_element_to_be_visible_and_enabled(selenium, timeout, (By.XPATH, xpath))


@pytest.helpers.register
def click_by_xpath(selenium, xpath):
    pytest.helpers.click_element(selenium, DEFAULT_TIMEOUT, (By.XPATH, xpath))


@pytest.fixture(autouse=True, scope="function")
def ffmpeg(request):
    _ensure_file_absent(VIDEO_PATH)
    if request.config.getoption('--record-screen'):
        print('Recoding screen...')
        cmd = 'ffmpeg -loglevel fatal -r 10 -f x11grab -draw_mouse 0 -s 1920x1080 -i :99 -c:v libvpx -quality realtime -cpu-used 0 ' \
            + '-b:v 384k -qmin 10 -qmax 42 -maxrate 384k -bufsize 1000k -an ' \
            + '-vf drawtext="fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf: text=%{localtime}: fontcolor=white: fontsize=24: box=1: boxcolor=black@0.5: boxborderw=5: x=(w-text_w): y=0" ' \
            + VIDEO_PATH
        with _background_process(cmd):
            yield
    else:
        yield


@pytest.fixture(autouse=True, scope="function")
def mpstat():
    _ensure_file_absent(CPUSTAT_PATH)
    with _background_process(f'bash -c "mpstat 1 > {CPUSTAT_PATH}"'):
        yield


def _ensure_file_absent(path):
    if os.path.exists(path):
        os.remove(path)


@contextlib.contextmanager
def _background_process(cmd, stdin=None, stdout=None, stderr=None):
    proc = subprocess.Popen(shlex.split(cmd), stdin=stdin, stdout=stdout, stderr=stderr)
    yield proc
    proc.terminate()
    proc.wait(timeout=30)


@pytest.fixture
def somefile():
    filename = os.path.join(os.environ['HOME'], 'example.jpeg')
    file_content = binascii.unhexlify(image)
    with open(filename, 'wb') as f:
        f.write(file_content)
        yield filename
    os.remove(filename)


DB_HOST = os.environ['DB_SQL_HOST']
DB_USERNAME = os.environ['DB_SQL_USERNAME']
DB_PASSWORD = os.environ['DB_SQL_PASSWORD']
DB_NAME = os.environ['DB_SQL_DATABASE']
BACKEND_API_DIR = os.environ['BACKEND_API_DIR']


@pytest.fixture(scope='session')
def db_name():
    assert DB_NAME != ''
    return DB_NAME


@pytest.fixture(scope='session')
def db_conn(db_name, skip_db_wipe):
    if skip_db_wipe:
        print('No db wipe')
        yield
        return

    print(f'Setup db connection, using database {db_name}')
    with psycopg.connect(f'user={DB_USERNAME} password={DB_PASSWORD} host={DB_HOST} dbname={db_name}') as conn:
        with conn.cursor() as cur:
            cur.execute("select tablename from pg_tables where schemaname = 'public' order by tablename ;")
            rows = cur.fetchall()
            for row in rows:
                print(f"Dropping table: {row[0]}")   
                cur.execute(f"drop table {row[0]} cascade")
        conn.commit()
        
    with psycopg.connect(f'user={DB_USERNAME} password={DB_PASSWORD} host={DB_HOST} dbname={db_name}') as test_conn:
        yield test_conn
    print('Teardown db connection')


# @pytest.fixture(autouse=True, scope='session')
@pytest.fixture
def wipe_db(db_conn, skip_db_wipe):
    if skip_db_wipe:
        return 

    proc = subprocess.run(['npm', 'run', 'migration:run'], cwd=BACKEND_API_DIR)
    print(proc.stdout, proc.stderr, proc.returncode)
    assert proc.returncode == 0
    proc = subprocess.run(['npm', 'run', 'migration:seed:run'], cwd=BACKEND_API_DIR)
    print(proc.stdout, proc.stderr, proc.returncode)
    assert proc.returncode == 0
