from selenium import webdriver
import os
from pathlib import Path

def create_webdriver():
    chrome_options = webdriver.ChromeOptions()

    temp_folder = Path(os.getenv("TEMP_EMPL"))
    temp_folder.mkdir(parents=True, exist_ok=True)

    prefs = {
        "download.default_directory" : str(temp_folder),
        'download.prompt_for_download': False,
        'plugins.always_open_pdf_externally': True,

    }

    chrome_options.add_argument("--headless=new")
    chrome_options.add_experimental_option('prefs', prefs)

    driver = webdriver.Chrome(
        options=chrome_options
        )
    return driver