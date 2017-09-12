#!/bin/usr/python3.6

from steptool_config import CONFIG
from datarobot_helpers import email, gcs

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import os
import re
from io import StringIO
import requests
import pandas as pd
from retrying import retry

## global variables
STEP_USERNAME = CONFIG['step_username']
STEP_PASSWORD = CONFIG['step_password']
DISTRICT_NAME_FULL = CONFIG['district_name_full']
SAVE_PATH = CONFIG['save_path']

@retry(wait_exponential_multiplier=1000, wait_exponential_max=64000, stop_max_attempt_number=10)
def scrape_steptool():
    """
    selenium on PythonAnywhere is a bugged older version
    so every `find_element` call is wrapped in a try/except block
    """
    with Display():
        print('Starting webdriver...')
        driver = webdriver.Firefox()

        try:
            driver.get("https://www.steptool.org/account/login/?next=/home/")

            ## login
            print('Logging in...')
            ## enter username
            try:
                element = driver.find_element_by_id('id_username')
            except:
                element = driver.find_element_by_id('id_username')
            finally:
                element.send_keys(STEP_USERNAME)
            ## enter password
            try:
                element = driver.find_element_by_id('id_password')
            except:
                element = driver.find_element_by_id('id_password')
            finally:
                element.send_keys(STEP_PASSWORD)
            ## submit login form
            element.send_keys(Keys.ENTER)
            WebDriverWait(driver, 15).until(
                EC.title_is('STEP: My Home Page')
            )

            ## navigate to Data Exports
            print('Navigating to Data Exports...')
            try:
                element = driver.find_element_by_link_text('Data Exports')
            except:
                element = driver.find_element_by_link_text('Data Exports')
            finally:
                element.click()
            WebDriverWait(driver, 15).until(
                EC.title_is('Export Student Achievement Data')
            )

            ## replace session URL with export path
            current_url = driver.current_url
            export_url = current_url.replace('achievement.html','py/step_all.csv')
            all_cookies = driver.get_cookies()

            print('Quitting webdriver...')
            driver.quit()

        except Exception as e:
            print(e)
            raise e

    return all_cookies, export_url

@retry(wait_exponential_multiplier=1000, wait_exponential_max=64000, stop_max_attempt_number=10)
def get_export_file(url, cookies):
    print('Downloading...')
    with requests.Session() as s:
        r = s.get(url, cookies=cookies)

    ## parse data and variables from response
    data = StringIO(r.text)
    pattern = 'attachment; filename=(all_steps_\d{4}-\d{4}.csv)'
    m = re.search(pattern, r.headers['Content-Disposition'])
    filename = m.group(1)

    return data, filename

def main():
    if not os.path.isdir(SAVE_PATH):
        os.mkdir(SAVE_PATH)

    ## scrape data from STEP Tool website
    try:
        all_cookies, export_url = scrape_steptool()
    except Exception as e:
        raise e

    ## extract cookies for session
    print('Extracting cookies...')
    session_cookies = {}
    for s_cookie in all_cookies:
        session_cookies[s_cookie['name']] = s_cookie['value']

    ## switch over to requests to export the data files
    data, filename = get_export_file(export_url, session_cookies)
    filepath = '{0}/{1}'.format(SAVE_PATH, filename)

    ## read the csv into a pandas dataframe and save
    df = pd.read_csv(data, low_memory=False)
    df.to_csv(filepath, index=False)

    ## push to GCS
    gcs.upload_to_gcs('steptool', 'all_steps', SAVE_PATH, filename)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        email.send_email('STEP Tool sync error', e)