import codecs
from os.path import abspath, dirname, join

from setuptools import find_packages, setup


TEST_DEPS = ["coverage[toml]", "pytest", "pytest-cov"]
DOCS_DEPS = [
    "recommonmark",
    "sphinx",
    "sphinx-autoapi",
    "sphinx-rtd-theme",
    "sphinxcontrib-runcmd",
]
CHECK_DEPS = [
    "black",
    "flake8",
    "flake8-bugbear",
    "flake8-quotes",
    "isort[colors]",
    "mypy",
    "pep8-naming",
]
REQUIREMENTS = ["loguru", "typing_extensions"]

EXTRAS = {
    "test": TEST_DEPS,
    "docs": DOCS_DEPS,
    "check": CHECK_DEPS,
    "dev": TEST_DEPS + DOCS_DEPS + CHECK_DEPS,
}

# Read in the version
with open(join(dirname(abspath(__file__)), "VERSION")) as version_file:
    version = version_file.read().strip()


setup(
    name="pyStructType",
    version=version,
    description="Define c structs with typing",
    long_description=codecs.open("README.md", "r", "utf-8").read(),
    long_description_content_type="text/markdown",
    author="Fernando Chorney",
    author_email="github@djsbx.com",
    url="https://github.com/fchorney/pystructtype",
    packages=find_packages(exclude=["tests"]),
    install_requires=REQUIREMENTS,
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.11",
    ],
    platforms=["any"],
    include_package_data=True,
    tests_require=TEST_DEPS,
    extras_require=EXTRAS,
)
