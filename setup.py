from setuptools import setup, find_packages
requirements = [
    'simpy>=4',
    'networkx==2.4',
    'geopy',
    'pyyaml>=5.1',
    'numpy>=1.16.5,<1.19',
    'scipy<1.6'
    'common-utils',
    'cython',   # otherwise sklearn fails
    'sklearn',
    'pandas==1.0.0',
    'tensorflow==1.14.0',
    'keras==2.2.5',
    'matplotlib',
]

test_requirements = [
    'flake8',
    'nose2'
]

setup(
    name='coord-sim',
    version='2.0.0',
    description='Simulate flow-level, inter-node network coordination including scaling and placement of services and '
                'scheduling/balancing traffic between them.',
    url='https://github.com/RealVNF/coord-sim',
    author='Stefan Schneider',
    author_email='stefan.schneider@upb.de',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=requirements + test_requirements,
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
