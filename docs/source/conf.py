import sys
from pathlib import Path

sys.path.insert(0, str(Path("../../src/pymadng/").resolve()))
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "PyMAD-NG"
copyright = "2025, Joshua Gray, Laurent Deniau"
author = "Joshua Gray, Laurent Deniau"
import pymadng

release = pymadng.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Add napoleon to the extensions list
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "myst_parser"]

templates_path = ["_templates"]
exclude_patterns = []

# Number figures
numfig = True
numfig_secnum_depth = 2

# Napolean options
napoleon_include_init_with_doc = True
napoleon_use_admonition_for_references = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
