import tomllib
from datetime import datetime

# Sphinx Base --------------------------------------------------------------------------
# Extensions
extensions = [
    # http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
    "sphinx.ext.autodoc",
    # http://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html
    "sphinx.ext.viewcode",
    # https://sphinx-autoapi.readthedocs.io/en/latest/
    "autoapi.extension",
    "sphinx.ext.autodoc.typehints",
]

# Set initial page name
master_doc = "index"

# Project settings
project = "pystructtype"
year = datetime.now().year
author = "Fernando Chorney"
project_copyright = f"{year}, {author}"

# Read in pyproject.toml to grab version
with open("../pyproject.toml", "rb") as f:
    project_data = tomllib.load(f)

# Short version name
version = project_data["project"]["version"]

# Long version name
release = version

# HTML Settings
html_theme = "sphinx_rtd_theme"
html_last_updated_fmt = "%b %d, %Y"
html_short_title = f"{project}-{version}"

# Pygments Style Settings
pygments_style = "monokai"

# Sphinx Extension Autodoc -------------------------------------------------------------

# Order members by source order
autodoc_member_order = "bysource"

# Always show members, and member-inheritance by default
autodoc_default_options = {"members": True, "show-inheritance": True}

# Sphinx Extension AutoAPI -------------------------------------------------------------
autoapi_type = "python"
autoapi_dirs = ["../src/pystructtype/"]
autoapi_template_dir = "./autoapi_templates"
autoapi_root = "autoapi"
autoapi_add_toctree_entry = False
autoapi_keep_files = False

# Exclude the autoapi templates in the doc building
exclude_patterns = ["autoapi_templates"]


# Add any Sphinx plugin settings here that don't have global variables exposed.
def setup(app):
    # App Settings ---------------------------------------------------------------------
    # Set source filetype(s)
    # Allow .rst files
    app.add_source_suffix(".rst", "restructuredtext")
