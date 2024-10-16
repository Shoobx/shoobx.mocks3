###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Shoobx Mock S3 Setup
"""
import os

from setuptools import find_packages, setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="shoobx.mocks3",
    version='4.2.9.dev0',
    author="Shoobx, Inc.",
    author_email="dev@shoobx.com",
    description="Shoobx Mock S3 Implementation",
    long_description=read('README.rst'),
    keywords="amazon aws s3 mock moto",
    license='Proprietary',
    url="http://shoobx.com/",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    data_files=[
        ('config', [
            'config/mocks3.cfg',
            'config/uwsgi.ini',
            ]
        ),
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Office/Business',
    ],
    python_requires=">=3.8",
    install_requires=[
        'boto3',
        'moto[server]>=3.0.0',
        'flask_cors',
        'pytz',
    ],
    extras_require=dict(
        test=[
            'coverage',
            'freezegun',
            'junitxml',
            'mock',
            'python-subunit',
            'pytz',
            'zope.testrunner'],
        dev=['ipdb', 'pdbpp'],
    ),
    entry_points={
        'console_scripts': [
            'sbx-mocks3-serve = shoobx.mocks3.run:serve',
        ]
    },
    zip_safe=False,
    test_suite='shoobx.mocks3',
)
