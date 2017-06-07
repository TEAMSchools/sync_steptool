#!/bin/usr/python3.6

from steptool_config import CONFIG
import os
import requests
import re
from io import StringIO
import pandas as pd
from gcloud import storage
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

## global variables
STEP_USERNAME = CONFIG['step_username']
STEP_PASSWORD = CONFIG['step_password']
DISTRICT_NAME_FULL = CONFIG['district_name_full']
SAVE_PATH = CONFIG['save_path']
GCLOUD_CREDENTIALS = CONFIG['gcloud_credentials']
GCLOUD_PROJECT_NAME = CONFIG['gcloud_project_name']
GCS_BUCKET_NAME = CONFIG['gcs_bucket_name']

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
            try:
                element = driver.find_element_by_id('id_username')
            except:
                element = driver.find_element_by_id('id_username')
            finally:
                element.send_keys(STEP_USERNAME)

            try:
                element = driver.find_element_by_id('id_password')
            except:
                element = driver.find_element_by_id('id_password')
            finally:
                element.send_keys(STEP_PASSWORD)

            element.send_keys(Keys.ENTER)

            ## navigate to Data Exports
            print('Navigating to Data Exports...')
            WebDriverWait(driver, 10).until(
                EC.title_is('STEP: My Home Page')
            )
            try:
                element = driver.find_element_by_link_text('Data Exports')
            except:
                element = driver.find_element_by_link_text('Data Exports')
            finally:
                element.click()

            ## navigate to export page
            print('Navigating to STEP Level Assessment export...')
            WebDriverWait(driver, 10).until(
                EC.title_is('{} Schools Exports'.format(DISTRICT_NAME_FULL))
            )
            try:
                element = driver.find_element_by_link_text('STEP Level Assessment Data')
            except:
                element = driver.find_element_by_link_text('STEP Level Assessment Data')
            finally:
                element.click()

            ## navigate to report download page and export cookies to pass to requests session
            print('Exporting session data...')
            WebDriverWait(driver, 10).until(
                EC.title_is('Export Step Level Assessment Data')
            )
            current_url = driver.current_url
            export_url = current_url.replace('step_level.html','step_all.csv')
            all_cookies = driver.get_cookies()

        finally:
            driver.quit()
            print('Quitting webdriver...')

    return all_cookies, export_url

def upload_to_gcs(save_dir, filename, credentials=GCLOUD_CREDENTIALS, project_name=GCLOUD_PROJECT_NAME, bucket_name=GCS_BUCKET_NAME):
    """
    upload file to a Google Cloud Storage blob
        - filepath
        - credentials
        - project
        - bucket_name
    """
    gcs_client = storage.Client(project_name, credentials)
    gcs_bucket = gcs_client.get_bucket(bucket_name)

    gcs_path = 'steptool/{}'.format(filename)
    gcs_blob = gcs_bucket.blob(gcs_path)
    print('\tUploading to Google Cloud Storage... {}'.format(gcs_blob))

    filepath = '{0}/{1}'.format(save_dir, filename)
    gcs_blob.upload_from_filename(filepath)

def main():
    if not os.path.isdir(SAVE_PATH):
        os.mkdir(SAVE_PATH)

    ## scrape data from STEP Tool website
    all_cookies, export_url = scrape_steptool()
    session_cookies = {}
    for s_cookie in all_cookies:
        session_cookies[s_cookie['name']] = s_cookie['value']

    ## switch over to requests to export the data files
    print('Downloading...')
    with requests.Session() as s:
        r = s.get(export_url, cookies=session_cookies)

    ## parse save file variables
    r_contentdisposition = r.headers['Content-Disposition']
    pattern = 'attachment; filename=(all_steps_\d{4}-\d{4}.csv)'
    m = re.search(pattern, r_contentdisposition)
    filename = m.group(1)
    savepath = '{0}/{1}'.format(SAVE_PATH, filename)

    ## read the csv into a pandas dataframe and save
    data = StringIO(r.text)
    df = pd.read_csv(data, low_memory=False)
    df.to_csv(savepath, index=False)

    ## push to GCS
    upload_to_gcs(SAVE_PATH, filename)

if __name__ == '__main__':
    main()