import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="py-irtools",
    version="1.0.6",
    author="Inbar Rose",
    author_email="inbar.rose1@gmail.com",
    description="A package with useful tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/InbarRose/irtools",
    packages=setuptools.find_packages(),
    install_requires=[
        'psutil',
        'junit-xml>=1.8',
        'pytz',
        'requests'
    ],
    classifiers=(
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
