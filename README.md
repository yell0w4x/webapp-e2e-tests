# Docker container for web app e2e testing  

Simple yet powerful e2e tests container. Uses firefox webdriver to perform tests. 
Ready to use with google auth. Captures test video, screenshot, logs and populate them 
on failure into `./failure_logs` folder.

# Examples run

To run headless use `--headless` option. Runs in any OS that docker supports.

    ./run --sut-location https://google.com --headless -k test_google_must_search_for_a_query_string

To see the browser window within current display issue following line. 
Note this only works for Linux or possibly for another environment with Xorg support.
Also possible to run on MacOS, but with some adjustments applied.
Note in none headless mode there is no video available.

    ./run --sut-location https://google.com -k test_google_must_search_for_a_query_string

The result should look like this.
![Example result](https://raw.githubusercontent.com/yell0w4x/webapp-e2e-tests/master/example-result.png)

If your SUT is on the same machine packed in docker container use container name or it's ip address in url.

[One more](#bigbasket)<a name="bigbasket"></a>

     ./run --sut-location https://bigbasket.com -k test_big_basket_must_show_product_in_cart

# SUT location

Put your SUT (System Under Test) endpoint to `defs.py` or use `--sut-location` option. 
There is also `--api-base-url` that is wrapped with fixture `api_base_url` in case 
if you have api and would like to use it for e.g. tests setup/tear down or other purpose.

There is a `--prod` preset to easily change related options. 
See `set_default_prod_options` in `./run` script.

# Prerequisites

Docker must be installed. The easiest way to have it on Linux is `wget -qO- https://get.docker.com | bash`.
See this for more details https://docs.docker.com/engine/install/ubuntu/#install-using-the-convenience-script.

# Firefox profile

For now Firefox 91.9.0esr (64-bit) is used.
This archive `3fdkgzzo.default-esr.tar.gz` contains `~/.mozilla/firefox/3fdkgzzo.default-esr` 
firefox profile directory (in public repo it's empty, of course).
To use google auth fixture `logged_in_selenium` make gmail (google) account. Log in into this account 
under firefox with the same version on your host system. 
Then exit firefox and archive firefox account directory. Replace the archive within the repo.
You can use distinct folder name. In that case change the name in `defs.py`.
See also `firefox_profile` fixture in `conftest.py`.

# Bitbucket pipeline

Use same `./run` script to run in Bitbucket pipeline. See `bitbucket-pipelines.yml`.

# Postgres database wipe before test

Reference `db_conn`, `wipe_db` fixtures to wipe the database.
Look for `--skip-db-wipe` and `SKIP_DB_WIPE` in source files to see the details.
Database related env variables are set in `Dockerfile`.

# CLI

```
$ ./run --help
Run web application end-to-end tests.

Usage:
    ./run [OPTIONS]

Options:
    --search-for        Example argument to show how to pass args to tests from cli 
                        (default: 'please write tests').
    --headless          Do not show browser window on the current screen.
    --sut-location      System Under Test url (default: https://stage.example.com)
    --api-base-url      API base url for the selected environment
                        (default: https://api-stage.example.com/)
    --destructive       Run destructive tests also
    --google-account    Google account to use for authorization if there is (default: '').
    --skip-db-wipe      Skip database wipe.
    -n,--repeat NUM     Number of test iterations to run (default: 1)
    --collect-logs      Collect logs regardless of failure.
    --open-dev-tools    Open dev tools on browser start.
    --open-js-console   Open js console on browser start.
    --prod              Preset for prod environment. 
                        Will be converted to these options:
                            --skip-db-wipe
                            --sut-location=https://app.example.com/
                            --api-base-url=https://api.example.com/

    --pytest-help       Pytest related help
    -h|--help           Show this message and exit

All default urls are related to the default environment which is stage. 
On failure test logs and screenshot are available under 'failure_logs' folder. 
In case of '--headless' option the failed test video is also available.

NOTE:

    All extra options are passed to the pytest as is. 
    See pytest --help for more options or ./run --pytest-help.
    Useful are -s show tests stdout and -k filter by test name.
    There is also possible to pass test file name(s) as 
    positional args like 'test_search_for.py' to run only tests from this file.
    On OSX use --headless to run or provide Xorg compartibility.

EXAMPLES:

    Runs all non-destructive tests on production with default params.

        ./run --prod

    The same, but runs headless

        ./run --prod --headless

    Runs only tests from test_search_for.py.

        ./run --prod test_search_for.py --headless

    Runs headless with specified sut location

        ./run --sut-locaiton https://google.com --headless
```

# Extra

Python version 3.9 is used.

What if example test(s) fails? 
Usually it's due to some changes in example SUT's dom since last repo review.
