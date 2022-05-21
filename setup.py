from setuptools import setup, find_packages
requirements = [
    'scipy==1.5.4',
    'simpy>=4',
    'networkx==2.4',
    'geopy',
    'pyyaml>=5.1',
    'numpy>=1.16.5,<=1.19.5',
    'common-utils',
    'scikit-learn',
    'pandas==1.1.5',
    'tensorflow==2.5.3',
    'keras==2.2.5',
    'matplotlib',
]

test_requirements = [
    'flake8',
    'nose2'
]

setup(
    name='coord-sim',
    version='2.1.1',
    description='Simulate flow-level, inter-node network coordination including scaling and placement of services and '
                'scheduling/balancing traffic between them.',
    url='https://github.com/RealVNF/coord-sim',
    author='Stefan Schneider',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=requirements,
    tests_require=test_requirements,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'coord-sim=coordsim.main:main',
            'animation=animations.animations:main',
            'lstm-predict=coordsim.traffic_predictor.lstm_predictor:main'
        ],
    },
)
