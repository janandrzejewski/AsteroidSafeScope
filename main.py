from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import configparser
from datetime import datetime, timedelta
import requests
import re
from tabulate import tabulate
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.gaia import Gaia
import logging

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DataObject:
    def __init__(self, id, begin, end):
        self.id = id
        self.begin = begin
        self.end = end


def read_config():
    config = configparser.ConfigParser()
    config.read("config.ini")

    email = config.get("Credentials", "email")
    password = config.get("Credentials", "password")
    page_name = config.get("Page", "name")

    return email, password, page_name


def log_in(email, password, page_name):
    driver = webdriver.Firefox()
    driver.get(page_name)
    element = driver.find_element(By.NAME, "email")
    element.send_keys(email)
    element = driver.find_element(By.NAME, "pass")
    element.send_keys(password)
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div/div[2]/form/div[4]/button"
    ).click()
    driver.find_element(
        By.XPATH, "/html/body/div[2]/div[2]/div/div[1]/ul[2]/li[3]/a/span"
    ).click()
    driver.find_element(By.ID, "sites").click()
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div/div/div[2]/table/tbody/tr[4]/td[1]/a/i"
    ).click()
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div/div/div[2]/table/tbody/tr[1]/td[1]/a/i"
    ).click()
    driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/button").click()

    return driver


def get_info(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")

    data_objects = []

    for row in rows:
        cells = row.find_all("td")

        if len(cells) >= 8:
            id = cells[1].find("span", id="id")
            if id:
                name_text = id.text

                begin_time = cells[7].text
                end_time = cells[8].text

                data_object = DataObject(name_text, begin_time, end_time)
                data_objects.append(data_object)

    return data_objects


def close_website(driver):
    driver.quit()


def collision(data, radius=10):
    collided_stars = set()
    for positon in data:
        coord = SkyCoord(ra=positon[2], dec=positon[3], unit=(u.hourangle, u.deg))
        j = Gaia.cone_search_async(coord, radius * u.arcsec)
        result = j.get_results()

        if len(result) > 0:
            for star in result:
                star_id = star["source_id"]
                if star_id not in collided_stars:
                    collided_stars.add(star_id)

    table = []
    for star_id in collided_stars:
        table.append([star_id])
    if table:
        print("Znalezione gwiazdy to:")
        return tabulate(table, headers=["Star ID"], tablefmt="grid")
    else:
        return "Nie znaleziono zadnych gwiazd w kolizji"


def print_data(data, object):
    match = re.search(r"\$\$SOE.*?\$\$EOE", data.text, re.DOTALL)
    if match:
        fragment = match.group()
        lines = fragment.strip().split("\n")

        table_data = []

        for line in lines:
            line = line.strip()
            parts = line.split()

            if len(parts) >= 8:
                date_time = parts[0] + " " + parts[1]
                ra = parts[2] + " " + parts[3] + " " + parts[4]
                dec = parts[5] + " " + parts[6] + " " + parts[7]

                table_data.append([object.id, date_time, ra, dec])

        headers = ["Object ID", "Date-Time", "RA", "Dec"]

        if table_data:
            table = tabulate(table_data, headers=headers, tablefmt="grid")
            print(table)
            print(collision(table_data, 5))

            return table_data
        else:
            logging.info("No data to display.")
            return []


def get_position(data_objects):
    for object in data_objects:
        url = "https://ssd.jpl.nasa.gov/api/horizons.api"
        start_time = datetime.today().strftime("%Y-%m-%d") + " " + object.begin
        if object.begin > object.end:
            stop_time = (
                (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
                + " "
                + object.end
            )
        else:
            stop_time = datetime.today().strftime("%Y-%m-%d") + " " + object.end
        url += "?format=text&COMMAND='{}'&OBJ_DATA=NO&EPHEM_TYPE=OBSERVER".format(
            object.id
        )
        url += "&START_TIME='{}'&STOP_TIME='{}'&STEP_SIZE='1h'&QUANTITIES='1'".format(
            start_time, stop_time
        )
        response = requests.get(url)
        print_data(response, object)


def main():
    email, password, page_name = read_config()
    driver = log_in(email, password, page_name)
    data_objects = get_info(driver)
    close_website(driver)
    get_position(data_objects)


if __name__ == "__main__":
    main()
