from setuptools import setup, find_packages

requirements = [
    'simpy',
    'networkx',
    'gym',
    'geopy',
    'pyyaml'
]

test_requirements = [
    'flake8',
    'pytest'
]

setup(
    name='coord-sim',
    version='0.9',
    description='Simulate flow-level, inter-node network coordination including scaling and placement of services and '
                'scheduling/balancing traffic between them.',
    url='https://github.com/CN-UPB/coordination-simulation',
    author='Stefan Schneider',
    author_email='stefan.schneider@upb.de',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=requirements + test_requirements,
    test_requirements=test_requirements,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'coord-sim=coordsim.main:main',
        ],
    },
)
