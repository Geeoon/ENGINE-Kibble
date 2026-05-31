import os
import sys

sys.path.insert(0, os.path.abspath('../../src'))
sys.path.insert(0, os.path.abspath('../../edge_node'))

project = 'ENGINE Kibble'
author = 'Elliot Norman'
release = '1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_autodoc_typehints',
]

autodoc_mock_imports = [
    'pymongo',
    'grpc',
    'psutil',
    'google',
    'protocol_pb2',
    'smtplib',
    'scapy',
    'flask',
    'waitress',
]

autoclass_content = 'both'

html_theme = 'furo'
