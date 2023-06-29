from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import configparser


class DataObject:
    def __init__(self, name, begin, end):
        self.name = name
        self.begin = begin
        self.end = end


def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini')

    email = config.get('Credentials', 'email')
    password = config.get('Credentials', 'password')
    page_name = config.get('Page', 'name')

    return email, password, page_name


def log_in(email, password):
    driver = webdriver.Firefox()
    driver.get("http://hebe.astro.amu.edu.pl/p_login.php")
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
    driver.find_element(
        By.ID, "sites"
    ).click()
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div/div/div[2]/table/tbody/tr[4]/td[1]/a/i"
    ).click()
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div/div/div[2]/table/tbody/tr[1]/td[1]/a/i"
    ).click()
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div/div/div[3]/button"
    ).click()

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
            name = cells[1].find('span', id='name')
            if name:
                name_text = name.text

                begin_time = cells[7].text
                end_time = cells[8].text

                data_object = DataObject(name_text, begin_time, end_time)
                data_objects.append(data_object)

    return data_objects


def close_website(driver):
    driver.quit()


def main():
    email, password, page_name = read_config()
    driver = log_in(email, password)
    data_objects = get_info(driver)
    close_website(driver)

    for obj in data_objects:
        print("Name:", obj.name)
        print("Begin:", obj.begin)
        print("End:", obj.end)


if __name__ == "__main__":
    main()
