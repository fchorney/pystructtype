from datetime import datetime

from recommonmark.parser import CommonMarkParser
from recommonmark.transform import AutoStructify

# from pystructtype import __version__


# This exists to fix a bug in recommonmark due to a missing function definition
# https://github.com/readthedocs/recommonmark/issues/177
class CustomCommonMarkParser(CommonMarkParser):
    def visit_document(self, node):
        pass


# Sphinx Base --------------------------------------------------------------------------
# Extensions
extensions = [
    # http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
    "sphinx.ext.autodoc",
    # http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
    "sphinx.ext.napoleon",
    # http://www.sphinx-doc.org/en/master/usage/extensions/todo.html
    "sphinx.ext.todo",
    # http://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html
    "sphinx.ext.viewcode",
    # https://sphinx-autoapi.readthedocs.io/en/latest/
    "autoapi.extension",
    # https://github.com/invenia/sphinxcontrib-runcmd
    "sphinxcontrib.runcmd",
]

# Set initial page name
master_doc = "index"

# Project settings
project = "PyStructType"
year = datetime.now().year
author = "Fernando Chorney"
copyright = f"{year}, {author}"

# Short version name
version = "0.1.0"

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

# Sphinx Extension Napoleon ------------------------------------------------------------

# We want to force google style docstrings, so disable numpy style
napoleon_numpy_docstring = False

# Set output style
napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False

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
    # Allow .rst files along with .md
    app.add_source_suffix(".rst", "restructuredtext")
    app.add_source_suffix(".md", "markdown")
    app.add_source_parser(CustomCommonMarkParser)

    # RecommonMark Settings ------------------------------------------------------------
    # Enable the evaluation of rst directive in .md files
    # https://recommonmark.readthedocs.io/en/latest/auto_structify.html
    app.add_config_value("recommonmark_config", {"enable_eval_rst": True}, True)
    app.add_transform(AutoStructify)
