__author__ = 'nevor'
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def act(driver):
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@id='galleryList']/descendant::img")))
