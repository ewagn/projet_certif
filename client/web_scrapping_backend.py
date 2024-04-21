from selenium import webdriver
from typing import Optional
import os
from aiopath import AsyncPath

async def create_webdriver():
    chrome_options = webdriver.ChromeOptions()

    temp_folder = AsyncPath(os.getenv("TEMP_EMPL"))
    await temp_folder.mkdir(parents=True, exist_ok=True)

    prefs = {
        "download.default_directory" : str(temp_folder),
        'download.prompt_for_download': False,
        'plugins.always_open_pdf_externally': True,
        # "plugins.plugins_disabled" : "Chrome PDF Viewer",
    }

    # else :
    #     return webdriver.Chrome()

    chrome_options.add_argument("--headless=new")
    # chrome_options.add_argument('--no-sandbox')
    chrome_options.add_experimental_option('prefs', prefs)

    driver = webdriver.Chrome(
        options=chrome_options
        )
    return driver