from setuptools import find_packages, setup


setup(
    name="liveboxplaytv",
    version="2.0.3",
    license="GPL3",
    description="Python bindings for the Orange Livebox Play TV appliance",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Philipp Schmitt",
    author_email="philipp@schmitt.co",
    url="https://github.com/pschmitt/python-liveboxplaytv",
    packages=find_packages(),
    install_requires=[
        "fuzzywuzzy",
        "python-Levenshtein",
        "pyteleloisirs>=3.6",
        "requests",
        "wikipedia",
    ],
    entry_points={"console_scripts": ["liveboxplaytv=liveboxplaytv.cli:main"]},
)
