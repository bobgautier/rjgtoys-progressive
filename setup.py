#!/usr/bin/python

from setuptools import setup

from setuprjg import PyTest, readfile

setup(
    name = "rjgtoys.progressive",
    version = "0.0.1",
    author = "Bob Gautier",
    author_email = "bob@rjg-resources.com",
    description = ("Support for progressive operations"),
    long_description = readfile('README'),
    license = "GPL",
    keywords = "progressive",
    namespace_packages=['rjgtoys'],
    packages = ['rjgtoys.progressive'],
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)"
        ],
    tests_require=['pytest'],
    # The following configures testing the way I like it
    cmdclass = {'test':PyTest},
)
