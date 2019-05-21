import configparser


class ConfigurationParser(object):
    def __init__(self, config_file=None):
        self.CONFIG_FILE = config_file
        self.CONFIG = None

    def get_configuration(self):
        config = configparser.ConfigParser()
        config.read(self.CONFIG_FILE)

        configuration = dict()

        for section in config.sections():
            items = config.items(section)
            section_dict = dict()
            for item in items:
                section_dict[item[0]] = item[1]
            configuration[section] = section_dict
        self.CONFIG = configuration

        return self.CONFIG
