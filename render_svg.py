from selenium import webdriver
from selenium.webdriver.edge.options import Options
import os, time

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
driver = webdriver.Edge(options=options)

svg_path = os.path.abspath("edson_card.svg").replace("\\", "/")
driver.get("file:///" + svg_path)
time.sleep(1)
driver.set_window_size(1100, 1100)
driver.save_screenshot("edson_card_preview.png")
driver.quit()
print("ok")
