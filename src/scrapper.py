import os
import time
from datetime import date
import requests

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By


def download_netto_offer(save_dir="data"):
    """
    Download Netto's weekly offer image and save it in 'save_dir'
    named netto_YYYY-MM-DD.jpg
    """
    # Ensure directory exists
    os.makedirs(save_dir, exist_ok=True)

    # Build filename
    today = date.today().isoformat()
    filename = f"netto_{today}.jpg"
    filepath = os.path.join(save_dir, filename)

    # Selenium setup
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    url = "https://netto.dk/netto-avisen/"
    driver.get(url)
    time.sleep(3)  # allow JS to load

    # Try finding the main image
    img = driver.find_element(
        By.CSS_SELECTOR,
        "img.swiper-lazy, img[src*='avis'], img[srcset]"
    )
    img_url = img.get_attribute("src")

    # Download image
    data = requests.get(img_url).content
    with open(filepath, "wb") as f:
        f.write(data)

    driver.quit()
    return filepath

if __name__ == '__main__':
    print("Starting function")
    download_netto_offer()