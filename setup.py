# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='bfp',
    version='',
    packages=find_packages(include=['pltform']),
    url='',
    license_file='LICENSE.txt',
    author='crash',
    author_email='',
    description='Basic Football Platform - framework for hosting algorithms and running pools',
    python_requires='>=3.10',
    install_requires=['regex',
                      'pyyaml',
                      'peewee',
                      'requests',
                      'beautifulsoup4',
                      'lxml'],
    entry_points={
        'console_scripts': [
            'game     = pltform.game:main',
            'team     = pltform.team:main',
            'pfr      = pltform.pfr:main',
            'fte      = pltform.fte:main',
            'swami    = pltform.swami:main',
            'pool     = pltform.pool:main',
            'db_admin = pltform.db_admin:main'
        ],
    }
)
