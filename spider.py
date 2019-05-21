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

    def step(self, val=0):
        screen_name = str(val)
        try:
            #WebDriverWait(self.driver, self.DELAY).until(EC.presence_of_element_located((By.CLASS_NAME, 'supportButton')))
            WebDriverWait(self.driver, self.DELAY*3).until(EC.presence_of_element_located((By.CLASS_NAME, 'widgets')))
            # Should also get the name of the screen
            #screen_name = self.screen_name()
            #print("Loaded %s" % screen_name)
        except TimeoutException:
            raise TimeoutException('Loading page took too much time')

        screencontent = self.driver.find_element_by_xpath('//div[@class="screenContent"]')
        # Now we must open the version sidebar
        screenviewcontainer = screencontent.find_element_by_class_name("screenViewContainer")
        screenview_widgets = screenviewcontainer.find_element_by_class_name("widgets")
        toggle_version_button = screenview_widgets.find_element_by_xpath('//button[contains(@class, "versionsToggleWidget")]')
        toggle_version_button.send_keys(Keys.RETURN)

        # Wait a "fixed" amount
        try:
            WebDriverWait(self.driver, self.DELAY*3).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'versionHeader')))
            # Should also get the name of the screen
        except TimeoutException:
            raise TimeoutException('Loading page took too much time')

        self.driver.implicitly_wait(self.DELAY*3)
        #screencontent = self.driver.find_element_by_xpath('//div[@class="screenContent"]')
        versions_sidebar = screencontent.find_element_by_class_name("versionsSidebar")
        versions = versions_sidebar.find_element_by_class_name("versions")
        version_elements = versions.find_elements_by_class_name("versionHeader")

        self.driver.implicitly_wait(self.DELAY*3)
        version_list = []
        for elem in version_elements:
            version_date = elem.find_element_by_class_name('versionHeaderText').text
            version_list.append(version_date)
            print('Found version_date %s' % version_date)

        # Flush results to disk

        with open(os.path.join(self.DATA_DIRECTORY, screen_name+".json"), 'w', encoding='utf-8') as writer:
            writer.write(json.dumps(version_list))

        # Check that there is a right-pointing arrow and click on it. If not, we have reached the end
        next_screen = self.next_screen()
        has_next_screen = not next_screen.get_property('disabled')
        if has_next_screen and val < 3:
            print('Found next screen!')
            next_screen.send_keys(Keys.RETURN)
            self.driver.implicitly_wait(self.DELAY * 3)
            print('All screenContent should now be visible')
            self.step(val=val + 1)

    def step_new(self, screen_name):
        screencontent = self.driver.find_element_by_xpath('//div[@class="screenContent"]')
        # Now we must open the version sidebar
        screenviewcontainer = screencontent.find_element_by_class_name("screenViewContainer")
        screenview_widgets = screenviewcontainer.find_element_by_class_name("widgets")
        toggle_version_button = screenview_widgets.find_element_by_xpath('//button[contains(@class, "versionsToggleWidget")]')
        toggle_version_button.send_keys(Keys.RETURN)

        # Wait a "fixed" amount
        try:
            WebDriverWait(self.driver, self.DELAY).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'versionHeader')))
            # Should also get the name of the screen
        except TimeoutException:
            raise TimeoutException('Loading page took too much time')

        versions_sidebar = screencontent.find_element_by_class_name("versionsSidebar")
        versions = versions_sidebar.find_element_by_class_name("versions")
        version_elements = versions.find_elements_by_class_name("versionHeader")

        self.driver.implicitly_wait(self.DELAY)
        version_list = []
        for elem in version_elements:
            version_date = elem.find_element_by_class_name('versionHeaderText').text
            version_list.append(version_date)
            print('Found version_date %s' % version_date)

        # Flush results to disk
        with open(os.path.join(self.DATA_DIRECTORY, screen_name+".json"), 'w', encoding='utf-8') as writer:
            writer.write(json.dumps(version_list))


    def get_first_screen(self):
        try:
            WebDriverWait(self.driver, self.DELAY).until(EC.presence_of_element_located((By.XPATH, '//div[@data-index="0"]')))
            print("Loaded projects overview page!")
        except TimeoutException:
            raise TimeoutException('Loading projects overview page took too much time')
        # Select the WebApp project (data-index = "0")
        active_projects = self.driver.find_element_by_id('activeProjects')
        webapp_project = active_projects.find_element_by_xpath('//div[@data-index="0"]')
        webapp_project_link = webapp_project.find_element_by_class_name('projectLink')
        webapp_project_link.send_keys(Keys.RETURN)

        try:
            WebDriverWait(self.driver, self.DELAY).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'section ')]")))
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
        self.step()

    def get_screen_list(self):
        try:
            WebDriverWait(self.driver, 3 * self.DELAY).until(EC.presence_of_element_located((By.CLASS_NAME, 'projectOverview')))
            print("Loaded all screen")
        except TimeoutException:
            raise TimeoutException('Loading all screens took too much time')

        self.driver.implicitly_wait(self.DELAY * 3)
        project_overview = self.driver.find_element_by_class_name("projectOverview")
        sections = project_overview.find_element_by_id("sections")
        screens = sections.find_elements_by_class_name("screen")
        print('Found %d screens' % len(screens))
        relative_urls = []
        for i, screen in enumerate(screens):
            url = screen.get_attribute('data-id')
            relative_urls.append(url)
            if (i+1) % 50 == 0:
                print('Completed %1.2f%%' % (((i+1)/len(screens)) * 100))
        print('Completed 100%%')
        path = 'https://app.zeplin.io/project/5c3da066182f8e339c8d00a9/screen/'
        relative_urls = [path + u for u in relative_urls]
        with open(os.path.join(self.DATA_DIRECTORY, 'out.txt'), 'w', encoding='utf-8') as writer:
            for u in relative_urls:
                writer.write(u+'\n')

    def projectoverview(self):
        try:
            WebDriverWait(self.driver, self.DELAY).until(EC.presence_of_element_located((By.XPATH, '//div[@data-index="0"]')))
            print("Loaded projects overview page!")
        except TimeoutException:
            raise TimeoutException('Loading projects overview page took too much time')
        # Select the WebApp project (data-index = "0")
        active_projects = self.driver.find_element_by_id('activeProjects')
        webapp_project = active_projects.find_element_by_xpath('//div[@data-index="0"]')
        webapp_project_link = webapp_project.find_element_by_class_name('projectLink')
        webapp_project_link.send_keys(Keys.RETURN)

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

        try:
            WebDriverWait(self.driver, self.DELAY).until(EC.presence_of_element_located((By.XPATH, '//div[@data-index="0"]')))
            print("Loaded projects overview page!")
        except TimeoutException:
            raise TimeoutException('Loading projects overview page took too much time')

    def download_screen_history(self):
        urls = ['https://app.zeplin.io/project/5c3da066182f8e339c8d00a9/screen/5c6d62110cb0f599dfd379c1',
               'https://app.zeplin.io/project/5c3da066182f8e339c8d00a9/screen/5c6a8ca8dd0ba39a1b1843dd']

        self.driver.implicitly_wait(self.DELAY)
        for i, url in enumerate(urls):
            self.driver.get(url)
            try:
                WebDriverWait(self.driver, self.DELAY * 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'widgets')))
                # Should also get the name of the screen
                screen_name = self.screen_name()
                screen_name = screen_name.replace(" ", "_")
                print("Loaded %s" % screen_name)
            except TimeoutException:
                raise TimeoutException('Loading page took too much time')
            self.step_new(screen_name=screen_name)
            print('Completed URL: %d out of %d' % (i, len(urls)))


if __name__ == "__main__":
    #zeplin_crawler = Crawler(config_file="C:\\Users\\CAP\\PycharmProjects\\Zeplin\\config.cfg")
    zeplin_crawler = Crawler(config_file="/home/casper/github/ZeplinCrawler/config.cfg")
    zeplin_crawler.login()

    #zeplin_crawler.projectoverview()
    #zeplin_crawler.get_screen_list()
    zeplin_crawler.download_screen_history()




