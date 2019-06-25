import yaml


def get_config(config_file):
    """
    Reads yaml config file and returns it as Python dict
    :param config_file: Path to yaml config file
    :return: Python dict containing the parameter names and values
    """

    with open(config_file) as f:
        return yaml.load(f, Loader=yaml.FullLoader)
