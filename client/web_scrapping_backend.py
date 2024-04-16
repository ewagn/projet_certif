from selenium import webdriver
from typing import Optional

async def create_webdriver():
    chrome_options = webdriver.ChromeOptions()

    prefs = {
        "download.default_directory" : "/Users/etiennewagner/Documents/Reconversion/Licence IA/2eme_annee/projet_certif/client/temp",
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