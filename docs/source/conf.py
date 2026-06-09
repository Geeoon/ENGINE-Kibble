# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

project = 'Kibble'
copyright = '2026, Giannah Donahoe, Rohan Sabhaya, Geeoon Chung, Elliot Norman, Anya Guyton'
author = 'Giannah Donahoe, Rohan Sabhaya, Geeoon Chung, Elliot Norman, Anya Guyton'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
]
autosummary_generate = True

autodoc_mock_imports = [
    "pymongo",
    "bson",
    "smtplib",
    "ssl",
    "email",
]

autosummary_generate = True

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
