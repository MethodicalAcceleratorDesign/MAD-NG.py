import sphinx_rtd_theme, os, sys
sys.path.insert(0, os.path.abspath("../../src/"))
sys.path.insert(0, os.path.abspath("../../"))
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'PyMAD-NG'
copyright = '2022, Joshua Gray, Laurent Deniau'
author = 'Joshua Gray, Laurent Deniau'
release = '0.2.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Add napoleon to the extensions list
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon'
    ]

templates_path = ['_templates']
exclude_patterns = []


#Napolean options
napoleon_include_init_with_doc = True
napoleon_use_admonition_for_references = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]


##Code from https://github.com/readthedocs/readthedocs.org/issues/1139, for autogenerating w/ read the docs
def run_apidoc(_):
	from sphinx.ext.apidoc import main
	import os
	import sys
	sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
	cur_dir = os.path.abspath(os.path.dirname(__file__))
	module = os.path.join(cur_dir,"../../src","pymadng")
	main(['-e', '-o', cur_dir, module, '--force'])

def setup(app):
	app.connect('builder-inited', run_apidoc)