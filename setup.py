import os

from setuptools import find_packages, setup

from rest_framework_display_filter import (
    __author__, __author_email__, __license__, __version__)

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="djangorestframework-display-filter",
    version=__version__,
    long_description=long_description,
    url="https://github.com/wakita181009/django-rest-framework-display-filter",
    license=__license__,
    author=__author__,
    author_email=__author_email__,
    packages=find_packages(exclude=["tests"]),
    zip_safe=False,
    install_requires=[
        "djangorestframework",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ]
)
