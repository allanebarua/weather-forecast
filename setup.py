"""Package setup."""
from setuptools import find_packages, setup

name = 'weather_forecast'
version = '1.0.0'

setup(
    name=name,
    version=version,
    packages=find_packages(exclude=['tests', 'tests.*']),
    description="Weather forecast system",
    long_description=open('README.md').read(),
    url="",
    author="Allan Barua",
    author_email="allanebarua@gmail.com",
    license="Proprietary",
    classifiers=[
        'Programming Language :: Python :: 3 :: Only',
    ],
    install_requires=[],
    scripts=[],
    include_package_data=True
)
