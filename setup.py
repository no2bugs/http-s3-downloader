#!/usr/bin/env python3

from setuptools import setup


setup(
    name='downloader',
    version='1.0',
    description="Downloads a file or space/comma separated list of files from URL/s. Supports \"http://\", \"https://\" and \"s3://\"",
    url='https://github.com/code4ops/http-s3-downloader',
    python_requires='>=3.0',
    license='Apache License 2.0',
    install_requires=[
      'requests',
      'boto3',
      'botocore',
    ],
    zip_safe=False,
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ),
)
