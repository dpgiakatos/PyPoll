# Always prefer setuptools over distutils
from setuptools import setup, find_packages

# To use a consistent encoding
from codecs import open
from os import path

# The directory containing this file
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get the dependencies from the requirements file
with open(path.join(HERE, 'requirements.txt'), encoding='utf-8') as f:
    required = f.read().splitlines()

# This call to setup() does all the work
setup(
    name="my-lib",
    version="0.0.1",
    description="Polarization library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://medium-multiply.readthedocs.io/",
    author="Dimitrios P. Giakatos",
    author_email="dgiakatos@csd.auth.gr",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent"
    ],
    packages=["poll"],
    include_package_data=True,
    install_requires=required
)
