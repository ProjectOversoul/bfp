# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='bfp',
    version='',
    packages=find_packages(include=['pltform']),
    url='',
    license='',
    author='crash',
    author_email='',
    description='',
    install_requires=['regex',
                      'pyyaml',
                      'peewee',
                      'requests',
                      'beautifulsoup4'],
    entry_points={
        'console_scripts': [
            'game = pltform.game:main',
            'team = pltform.team:main',
            'pfr  = pltform.pfr:main'
        ],
    }
)
