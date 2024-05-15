# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# import uuid
# import os
# from pathlib import Path

# def create_webdriver():
#     service = Service(executable_path='/usr/bin/chromedriver')
#     chrome_options = webdriver.ChromeOptions()


#     temp_folder = Path('/temp_' + uuid.uuid4())
#     temp_folder.mkdir(parents=True, exist_ok=True)

#     prefs = {
#         "download.default_directory" : str(temp_folder),
#         'download.prompt_for_download': False,
#         'plugins.always_open_pdf_externally': True,

#     }

#     chrome_options.add_argument("--headless=new")
#     chrome_options.add_experimental_option('prefs', prefs)

#     driver = webdriver.Chrome(
#         options=chrome_options
#         , service=service
#         )
#     driver.capabilities
#     return driver