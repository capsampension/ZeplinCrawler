from config.config import ConfigurationParser
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import os
import json

class Crawler(object):
    def __init__(self,
                 config_file):
        self.config_file = config_file
        self.cparser = ConfigurationParser(config_file=self.config_file)
        self.configuration = self.cparser.get_configuration()
        self.ZEPLIN_HTTP_ADDRESS = self.configuration['ZEPLIN']['address']
        self.ZEPLIN_USERNAME = self.configuration['ZEPLIN']['zeplin_username']
        self.ZEPLIN_PASSWORD = self.configuration['ZEPLIN']['zeplin_password']
        self.DATA_DIRECTORY = self.configuration['ZEPLIN']['data_directory']
        self.CHROME_DRIVER_LOCATION = self.configuration['ZEPLIN']['chrome_driver']
        self.DELAY = 10
        if not os.path.isdir(self.DATA_DIRECTORY):
            raise ValueError("%s is not a directory. Aborting...")
        self.driver = None

    def next_screen(self):
        header_title = self.driver.find_element_by_class_name("headerTitle")
        button_right = header_title.find_element_by_id('arrowRight')
        return button_right

    def screen_name(self):
        headertitle = self.driver.find_element_by_class_name("headerTitle")
        headercontainer = headertitle.find_element_by_class_name("headerContainer")
        header = headercontainer.find_element_by_id('header')
        return header.get_attribute('title')

    def step(self):
        try:
            WebDriverWait(self.driver, self.DELAY).until(EC.presence_of_element_located((By.CLASS_NAME, 'supportButton')))
            # Should also get the name of the screen
            screen_name = self.screen_name()
            print("Loaded %s" % screen_name)
        except TimeoutException:
            raise TimeoutException('Loading page took too much time')

        screencontent = self.driver.find_element_by_xpath('//div[@class="screenContent"]')
        versions_sidebar = screencontent.find_element_by_class_name("versionsSidebar")
        versions = versions_sidebar.find_element_by_class_name("versions")
        version_elements = versions.find_elements_by_xpath("//*[contains(@class, 'version')]")

        firstElemName = 'versionHeader'
        firstElemFound = False

        lastElemName = 'version initialCommit'
        lastElemFound = False

        res = []
        for elem in version_elements:
            if firstElemFound and not lastElemFound:
                res.append(elem)
            if elem.get_attribute('class') == firstElemName:
                res.append(elem)
                firstElemFound = True
            if elem.get_attribute('class') == lastElemName:
                res.append(elem)
                lastElemFound = True
                break

        # Is now a long list with all the intermediate nodes added as well. Loop over it and filter out un-important
        # stuff
        version_dict = dict()
        version_changes = 0
        version_date = None
        version_names = ['version yellow']
        for elem in res:
            classname = elem.get_attribute('class')
            if classname == firstElemName:
                # Begin a new element. Store the last and counter
                if version_date is not None:
                    version_dict[version_date] = version_changes
                version_changes = 0
                version_date = elem.find_element_by_class_name('versionHeaderText').text
            elif version_names in classname:
                version_changes += 1
        # Flush results to disk
        with open(os.path.join(self.DATA_DIRECTORY, screen_name+".json"), 'w', encoding='utf-8') as writer:
            writer.write(json.dumps(version_dict))

        # Check that there is a right-pointing arrow and click on it. If not, we have reached the end
        next_screen = self.next_screen()
        has_next_screen = next_screen.get_property('disabled')
        if has_next_screen():
            next_screen.send_keys(Keys.RETURN)
            self.step()

    def get_first_screen(self):
        try:
            WebDriverWait(self.driver, self.DELAY).until(EC.presence_of_element_located((By.CLASS_NAME, 'supportButton')))
            print("Loaded projects overview page!")
        except TimeoutException:
            raise TimeoutException('Loading projects overview page took too much time')
        # Select the WebApp project (data-index = "0")
        active_projects = self.driver.find_element_by_id('activeProjects')
        webapp_project = active_projects.find_element_by_xpath('//div[@data-index="0"]')
        webapp_project_link = webapp_project.find_element_by_class_name('projectLink')
        webapp_project_link.send_keys(Keys.RETURN)

        try:
            WebDriverWait(self.driver, self.DELAY).until(EC.presence_of_element_located((By.CLASS_NAME, 'supportButton')))
            print("Loaded WebApp overview page!")
        except TimeoutException:
            raise TimeoutException('Loading WebApp overview page took too much time')

        # Find all the headlines
        overview_content = self.driver.find_element_by_class_name('overviewContent')
        project_overview = overview_content.find_element_by_class_name('projectOverview')
        sections = project_overview.find_element_by_id('sections')
        headlines = sections.find_elements_by_xpath("//div[contains(@class, 'section ')]")

        # First entry
        headline = headlines[0]

        screen_grid = headline.find_element_by_class_name('screenGrid')
        first_screen_in_group = screen_grid.find_element_by_xpath('//div[@data-index="0"]')
        first_screen_link = first_screen_in_group.find_element_by_class_name('screenLink')
        first_screen_link.send_keys(Keys.RETURN)
        #self.step()


    def login(self):
        print('Logging in to Zeplin...')
        self.driver = webdriver.Chrome(self.CHROME_DRIVER_LOCATION)
        self.driver.get(self.ZEPLIN_HTTP_ADDRESS)

        try:
            WebDriverWait(self.driver, self.DELAY).until(EC.presence_of_element_located((By.ID, 'loginForm')))
            print("Loaded is ready!")
        except TimeoutException:
            raise TimeoutException('Loading Zeplin main page took too much time')

        loginform = self.driver.find_element_by_id('loginForm')
        username_field = loginform.find_element_by_id('handle')
        username_field.clear()
        username_field.send_keys(self.ZEPLIN_USERNAME)
        password_field = loginform.find_element_by_id('password')
        password_field.clear()
        password_field.send_keys(self.ZEPLIN_PASSWORD)
        password_field.send_keys(Keys.RETURN)


if __name__ == "__main__":
    zeplin_crawler = Crawler(config_file="C:\\Users\\CAP\\PycharmProjects\\Zeplin\\config.cfg")
    zeplin_crawler.login()
    zeplin_crawler.get_first_screen()





