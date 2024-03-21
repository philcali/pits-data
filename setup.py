#!/bin/env python3

from setuptools import setup, find_packages


with open('README.md', 'r') as f:
    long_description = f.read()


setup(
    name="pinthesky",
    version="0.1.0",
    description="Simple Pi In The Sky Data Plane",
    long_description=long_description,
    long_description_context_type="text/markdown",
    author="Philip Cali",
    author_email="philip.cali@gmail.com",
    url="https://github.com/philcali/pits-data",
    license="Apache License 2.0",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent"
    ],
    install_requires=[
        "boto3"
    ],
    extra_require={
        'test': ['pytest']
    }
)
