from setuptools import find_packages, setup

setup(
    name='userservice',
    version='1.0.4',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'pyodbc',
        'google-auth',
        'requests',
    ],
)