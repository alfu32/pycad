from setuptools import setup, find_packages

setup(
    name='pycad',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'PySide6',  # Add all your dependencies here
        'ezdxf',
    ],
    entry_points={
        'console_scripts': [
            'pycad=pycad.main:main',  # Adjust to your main entry point
        ],
    },
)
