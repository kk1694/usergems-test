from setuptools import find_packages, setup

# Read the requirements.txt file
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="jobsfinder",
    packages=find_packages(include=["jobsfinder"]),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ugfind=jobsfinder.cli:main",  # Example: mycli=my_package.cli:main
        ],
    },
)
