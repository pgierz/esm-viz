#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
import os
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install


def show_messages():
    print("Install is now complete. Please be aware of the following:")
    print(
        "\nIf you used the --user flag in pip, you should adapt your PATH variable to include:"
    )
    print(os.path.join(os.environ.get("HOME"), ".local/bin"))
    print(
        "\nIf you used the --prefix flag in pip, you should adapt **both** you PATH and PYTHONPATH accordingly:"
    )
    print("PATH=${whatever_prefix_you_used}/bin:$PATH")
    print(
        "PYTHONPATH=${whatever_prefix_you-used}/lib/python-${your_python_version}/site-packages"
    )
    print("\nThank you for installing esm_viz!")


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        show_messages()
        develop.run(self)


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        # PUT YOUR POST-INSTALL SCRIPT HERE or CALL A FUNCTION
        show_messages()
        install.run(self)


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
    version="0.9.5",
    zip_safe=False,
)
