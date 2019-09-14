#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

# TODO: Shouldn't this somehow be linked to the requirements.txt file?
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup_requirements = []

test_requirements = []

setup(
    author="Paul Gierz",
    author_email="pgierz@awi.de",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="esm-viz allows you to monitor and visualize ongoing simulations",
    entry_points={
        "console_scripts": [
            "esm_viz=esm_viz.cli:main",
            "esm_viz_deploy=esm_viz.scripts.deploy:deploy",
            "esm_viz_combine=esm_viz.scripts.combine:combine",
        ]
    },
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="esm_viz",
    name="esm_viz",
    packages=find_packages(),
    package_dir={"esm_viz": "esm_viz"},
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/pgierz/esm_viz",
    version="0.9.4",
    zip_safe=False,
)
