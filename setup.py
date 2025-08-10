from setuptools import setup, find_packages

setup(
    name='coffee_roaster',
    version='0.0.1',
    description='Coffee Roasting Management App',
    author='sime',
    author_email='simeneshkebede@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['frappe'],
)
