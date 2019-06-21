# -*- coding: utf-8 -*-
#

# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinxcontrib.apidoc',
              'sphinx.ext.viewcode',
              'sphinxcontrib.rsvgconverter',
              'openstackdocstheme',
              ]

repository_name = 'openstack/python-ironic-inspector-client'
use_storyboard = True

wsme_protocols = ['restjson']

# sphinxcontrib.apidoc options
apidoc_module_dir = '../../ironic_inspector_client'
apidoc_output_dir = 'reference/api'
apidoc_excluded_paths = [
    'test/*',
    'test',
    'common/i18n*',
    'shell*']
apidoc_separate_modules = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
copyright = u'OpenStack Foundation'

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ['ironic_inspector_client']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'openstackdocs'
#html_theme_path = ["."]
#html_theme = '_theme'
#html_static_path = ['_static']

# Output file base name for HTML help builder.
htmlhelp_basename = 'python-ironic-inspector-clientdoc'

latex_use_xindy = False

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    (
        'index',
        'doc-python-ironic-inspector-client.tex',
        u'Python Ironic Inspector Client Documentation',
        u'OpenStack Foundation',
        'manual'
    ),
]
