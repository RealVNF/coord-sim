import yaml
import copy
import os


def get_config(config_file):
    """
    Parse simulator config params in specified yaml file and return as Python dict
    """
    with open(config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


def write_config(file_name, config):
    with open(f'configurations/{file_name}.yaml', 'w') as outfile:
        yaml.dump(config, outfile)


def main():
    base_config_file = 'base_config.yaml'
    base_config = get_config(os.path.abspath(base_config_file))
    os.makedirs('configurations/', exist_ok=True)

    ingress_percentage = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]

    # Scenario 1: low link cap
    config = copy.deepcopy(base_config)
    config['node_cap_values'] = [50]
    config['node_cap_weights'] = [1]
    config['link_cap_values'] = [10]
    config['link_cap_weights'] = [1]
    for ing in ingress_percentage:
        config['node_ingress_probability'] = ing
        write_config(f'llc_{ing}',config)

    # Scenario 1: low node cap
    config = copy.deepcopy(base_config)
    config['node_cap_values'] = [10]
    config['node_cap_weights'] = [1]
    config['link_cap_values'] = [50]
    config['link_cap_weights'] = [1]
    for ing in ingress_percentage:
        config['node_ingress_probability'] = ing
        write_config(f'lnc_{ing}',config)

    # Scenario 1: heterogeneous caps
    config = copy.deepcopy(base_config)
    config['node_cap_values'] = [0, 10, 50]
    config['node_cap_weights'] = [0.5, 0.4, 0.1]
    config['link_cap_values'] = [50]
    config['link_cap_weights'] = [1]
    for ing in ingress_percentage:
        config['node_ingress_probability'] = ing
        write_config(f'hc_{ing}',config)


if __name__ == "__main__":
    main()