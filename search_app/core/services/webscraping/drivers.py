from selenium.webdriver.chrome.service import Service
from selenium.webdriver import Chrome, ChromeOptions
import uuid
import os
from pathlib import Path
import requests
import pandas as pd
from random import choice
from typing import Iterator
import logging

lg = logging.getLogger(__name__)

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

def get_dataframe_shuffled(df : pd.DataFrame, column : str | None = None) -> Iterator[pd.Series]:

    rows = df.sample(frac=1).iterrows()

    for row in rows :
        if column :
            yield row[1][column]
        else :
            yield row[1]

class ProxiesHandler():
    free_proxies_providers = ["https://free-proxy-list.net"]

    _retrieved_proxies      = None
    _proxies                = set()
    _used_proxies           = set()
    _not_working_proxies    = set()

    def __init__(self) -> None:
        self._mimic_header = None

    def get_proxies_elements(self):
        for proxies_provider in self.free_proxies_providers :
            resp = requests.get(proxies_provider)
            proxy_list = pd.read_html(resp.text)[0]
            proxy_list["url"]="http://" + proxy_list["IP Address"] + ":" + proxy_list["Port"].astype(str)
            self._retrieved_proxies = proxy_list[proxy_list["Https"]=="yes"]

    def build_good_proxies(self):
        test_url = "https://httpbin.org/ip"


        for proxy_row in get_dataframe_shuffled(df=self.proxies_retrived):
            proxy_url = proxy_row['url']
            try :
                proxies = {
                    'http'  : proxy_url,
                    'https' : proxy_url
                }
                resp = requests.get(url=test_url, headers=self.mimic_header, proxies=proxies, timeout=2)
                lg.info(f"proxy inscription : {proxy_url}")
                proxy_ip = f"{proxy_row['IP Address']}:{proxy_row['Port']}" if proxy_row['Port'] else proxy_row['IP Address']
                self._proxies.add(proxy_ip)
                self.proxies_retrived.drop(index=self.proxies_retrived[self.proxies_retrived['url']==proxy_url].index)
            except Exception :
                lg.info(f"proxy eviction : {proxy_url}")
                lg.info(f"mimic_header = {self.mimic_header}")
                self.proxies_retrived.drop(index=self.proxies_retrived[self.proxies_retrived['url']==proxy_url].index)
            if len(self._proxies) >= 5 :
                break



    @property
    def mimic_header(self) -> dict[str, str]:
        if not self._mimic_header :
            resp = requests.get(
                url='https://headers.scrapeops.io/v1/browser-headers',
                params={
                    'api_key': os.getenv('HEADER_API_KEY'),
                    'num_results': '1'}
                )
            self._mimic_header = resp.json()['result'][0]
        
        return self._mimic_header
    
    
    @property
    def proxies_retrived(self) -> pd.DataFrame:
        if not isinstance(self._retrieved_proxies, pd.DataFrame) :
            self.get_proxies_elements()
        
        if self._retrieved_proxies.empty:
            self.get_proxies_elements()
        
        return self._retrieved_proxies
    
    @property
    def proxies(self) -> set:
        if not self._proxies :
            self.build_good_proxies()
        return self._proxies
    
    @property
    def proxy(self) -> str:

        return self.proxies.pop()

class ScrapingDriver():
    AGENT_LIST = [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:24.0) Gecko/20100101 Firefox/24.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/91.0.4472.114 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0"
        ]
    _proxies_handler = ProxiesHandler()
    
    def __init__(self) -> None:
        pass

    def get_driver(self, url : str) -> tuple[Chrome, Path]:
        # lg.info("Creation d'un moteur de scraping.")
        service = Service(executable_path='/usr/bin/chromedriver')
        chrome_options = ChromeOptions()

        # temp_folder = Path(os.getenv("TEMP_EMPL"))
        # temp_folder.mkdir(parents=True, exist_ok=True)
        temp_folder = Path('./temp_' + str(uuid.uuid4()))
        temp_folder.mkdir(parents=True, exist_ok=True)

        prefs = {
            "download.default_directory" : str(temp_folder.absolute()),
            'download.prompt_for_download': False,
            'plugins.always_open_pdf_externally': True,
        }

        chrome_options.add_argument("--headless=new")
        # chrome_options.add_argument('--disable-blink-features')
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f'--proxy-server={self._proxies_handler.proxy}')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        chrome_options.add_experimental_option('prefs', prefs)

        

        driver = Chrome(
            options=chrome_options,
            service=service
            )
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": choice(self.AGENT_LIST)})
        driver.get(url=url)

        return driver, temp_folder