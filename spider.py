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
        self.DATA_DIRECTORY = self.configuration['ZEPLIN']['group_directory']
        self.SCREEN_DIRECTORY = self.configuration['ZEPLIN']['screen_directory']
        self.CHROME_DRIVER_LOCATION = self.configuration['ZEPLIN']['chrome_driver']
        self.ZEPLIN_PROJECT_PATH = 'https://app.zeplin.io/project/5c3da066182f8e339c8d00a9/screen/'
        self.DELAY = 10
        if not os.path.isdir(self.DATA_DIRECTORY):
            raise ValueError("%s is not a directory. Aborting...")
        self.driver = None

    def screen_name(self):
        """
        Gets the title of a screen.
        :return: The title of a screen.
        """
        headertitle = self.driver.find_element_by_class_name("headerTitle")
        headercontainer = headertitle.find_element_by_class_name("headerContainer")
        header = headercontainer.find_element_by_id('header')
        return header.get_attribute('title')

    def step(self, screen_name):
        """
        For a given Zeplin screen, the method open the version side-bar, scrapes the content (with filtering)
        and stores the scraped content in a JSON file named according to the @screen_name and prefixed with the group
        the screen belongs to.
        :param screen_name: The names of the screen prefixed by the group it belong to.
        :return: Nothing.
        """
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

        # Flush results to disk
        with open(os.path.join(self.SCREEN_DIRECTORY, screen_name+".json"), 'w', encoding='utf-8') as writer:
            writer.write(json.dumps(version_list))

    def write_groups_and_screens_to_disk(self):
        """
        For a given project, finds all the groups (screens under a common headline) and scrapes the relative URLs
        for the screens that belong to each group. The screens' url, its group name and some other metadata is written
        to a delimited file for subsequent processing.
        :return: Nothing
        """
        try:
            WebDriverWait(self.driver, 3 * self.DELAY).until(
                EC.presence_of_element_located((By.CLASS_NAME,'projectOverview'))
            )
            print("Loaded all screen")
        except TimeoutException:
            raise TimeoutException('Loading all screens took too much time')

        self.driver.implicitly_wait(self.DELAY * 3)
        project_overview = self.driver.find_element_by_class_name("projectOverview")
        sections = project_overview.find_element_by_id("sections")
        # We need to group name
        groups = sections.find_elements_by_xpath('//div[starts-with(@class, "section")]')
        print('Found %d groups' % len(groups))

        grp_ctr = 0
        for i, group in enumerate(groups):
            if group.get_attribute('data-index') is not None:

                group_name_elem = group.find_element_by_class_name("sectionNameForm")

                # The find_elements_by_class_name (notice plural) is required as Selenium can't find the text otherwise
                group_name = group_name_elem.find_elements_by_class_name('mirror')
                group_name = group_name[0].get_attribute('textContent')
                group_name = group_name.replace(u'\xa0', u' ')
                group_name = group_name.replace(u' ', u'_')
                group_name = group_name.replace(u'/', u'_')

                # Get the screens for the particular group
                screens = group.find_elements_by_class_name("screen")
                # textContent was also needed
                out_file_name = '%s.txt' % group_name
                with open(os.path.join(self.DATA_DIRECTORY, out_file_name), 'w', encoding='utf-8') as writer:
                    for screen in screens:
                        screen_relative_url = screen.get_attribute('data-id')
                        screen_absolute_url = self.ZEPLIN_PROJECT_PATH + screen_relative_url
                        writer.write('%d#%s#%d#%s\n' % (grp_ctr, group_name, len(screens), screen_absolute_url))
                grp_ctr += 1
                print('Finished %d out of %d' % (i, len(groups)))

    def projectoverview(self):
        """
        Following successful login, this method selects the first project available and accesses it.
        The behaviour is undefined if no projects exist.
        :return: Nothing
        """
        try:
            WebDriverWait(self.driver, self.DELAY).until(
                EC.presence_of_element_located((By.XPATH, '//div[@data-index="0"]'))
            )
            print("Loaded projects overview page!")
        except TimeoutException:
            raise TimeoutException('Loading projects overview page took too much time')
        # Select the WebApp project (data-index = "0")
        active_projects = self.driver.find_element_by_id('activeProjects')
        webapp_project = active_projects.find_element_by_xpath('//div[@data-index="0"]')
        webapp_project_link = webapp_project.find_element_by_class_name('projectLink')
        webapp_project_link.send_keys(Keys.RETURN)

    def login(self):
        """
        Logs into Zeplin.
        :return: Nothing
        """
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

    def download_screen_history(self, urls):
        """
        Scrapes the versioning of screens in Zeplin, each defined by an absolute URL found in urls.
        :param urls: A list of urls on the form <group>;#;<absolute_url>.
        :return: Nothing.
        """
        try:
            WebDriverWait(self.driver, self.DELAY).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'section ')]")))
            print("Loaded WebApp overview page!")
        except TimeoutException:
            raise TimeoutException('Loading WebApp overview page took too much time')

        for i, url in enumerate(urls):
            group, url = url.split(';#;')
            self.driver.get(url)
            try:
                WebDriverWait(self.driver, self.DELAY * 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'widgets')))
                screen_name = self.screen_name()
                screen_name = screen_name.replace(u'\xa0', u' ')
                screen_name = screen_name.replace(u' ', u'_')
                screen_name = screen_name.replace(u'/', u'')
            except TimeoutException:
                raise TimeoutException('Loading screen took too much time')
            self.step(screen_name=group+'_-_'+screen_name)

            if (i+1) % 25 == 0:
                print('Completed URL! (%d out of %d)' % (i, len(urls)))


def load_groups_from_disk(data_directory):
    """
    Reads URLs from a collection of files.
    :param data_directory: The absolute path of the directory containing the files.
    :return: A list of read URLs
    """
    groups = os.listdir(data_directory)
    print('Found %d groups/headlines' % len(groups))
    result_list = []
    for group in groups:
        with open(os.path.join(data_directory, group), 'r', encoding='utf-8') as reader:
            content = reader.readlines()
        content = [x.strip().split('#') for x in content]
        result_list = [entry[1] + ';#;' + entry[3] for entry in content]

    print('Processed all groups. Total screens: %d' % len(result_list))
    return result_list

def filter_url_list_by_screen(screens, screen):
    """
    As the driver can crash, this method takes a list of url and retains only those after a specific point defined by
    a specific relative URL. For example, if the list of screens is ['a','b','c','d','e'] and the point given is 'c',
    the filtered list will be ['c','d','e']
    :param screens: A list of URLs. The output from load_groups_from_disk
    :param screen: The relative URL for a screen. Will be something like '5cb04e0481a36d6b22456747'
    :return: A filtered list of URLs.
    """

    screen = 'screen/' + screen
    screen_found = False
    res = []
    for s in screens:
        if screen in s:
            screen_found = True
            res.append(s)
        elif screen_found:
            res.append(s)
    print('Filtered list contains to %d URLs' % len(res))
    return res

if __name__ == "__main__":
    zeplin_crawler = Crawler(config_file="C:\\Users\\CAP\\PycharmProjects\\Zeplin\\config.cfg")
    #zeplin_crawler = Crawler(config_file="/home/casper/github/ZeplinCrawler/config.cfg")
    zeplin_crawler.login()

    zeplin_crawler.projectoverview()
    #zeplin_crawler.write_groups_and_screens_to_disk()
    urls = load_groups_from_disk(data_directory=zeplin_crawler.DATA_DIRECTORY)
    urls = filter_url_list_by_screen(urls, screen='screen/5cab215a16f8996023e6b276')
    zeplin_crawler.download_screen_history(urls=urls)




