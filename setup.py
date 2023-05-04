import os

from setuptools import setup, find_packages

# read the contents of the README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

requirements = [
    'simpy>=4',
    'networkx==2.4',
    'geopy',
    'numpy>=1.16.5,<=1.19.5',
    'pandas==1.1.5',
    'matplotlib',
]
# extra requirements for the lstm_predictor (usually not needed)
lstm_extra_requirements = [
    "scikit-learn",
    'keras==2.2.5',
]
test_requirements = [
    'flake8',
    'nose2'
]

setup(
    name='coord-sim',
    version='2.2.0',
    description='Simulate flow-level, inter-node network coordination including scaling and placement of services and '
                'scheduling/balancing traffic between them.',
    url='https://github.com/RealVNF/coord-sim',
    author='Stefan Schneider',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    python_requires=">=3.6.0",
    install_requires=requirements,
    extras_require={"lstm": lstm_extra_requirements},
    tests_require=test_requirements,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'coord-sim=coordsim.main:main',
            'animation=animations.animations:main',
            'lstm-predict=coordsim.traffic_predictor.lstm_predictor:main'
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    license="MIT",
)
