from setuptools import setup, find_packages
requirements = [
    'simpy>=4',
    'networkx',
    'geopy',
    'pyyaml>=5.1',
    'numpy',
    'common-utils'
]

test_requirements = [
    'flake8',
    'nose2'
]

dependency_links = [
    'git+https://github.com/RealVNF/common-utils'
]

setup(
    name='coord-sim',
    version='1.0.0',
    description='Simulate flow-level, inter-node network coordination including scaling and placement of services and '
                'scheduling/balancing traffic between them.',
    url='https://github.com/RealVNF/coord-sim',
    author='Stefan Schneider',
    dependency_links=dependency_links,
    author_email='stefan.schneider@upb.de',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=requirements + test_requirements,
    tests_require=test_requirements,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'coord-sim=coordsim.main:main',
        ],
    },
)
