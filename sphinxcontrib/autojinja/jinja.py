"""
    sphinxcontrib.autojinja
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2012 by Jaka Hudoklin
    :license: BSD, see LICENSE for details.

"""

import re
import os
import sys
from docutils import nodes
from docutils.statemachine import ViewList

try:
    from docutils.parsers.rst import Directive
except ImportError:
    from sphinx.util.compat import Directive

from sphinx.util.nodes import nested_parse_with_titles

from sphinx.ext.napoleon import Config
from sphinx.ext.napoleon.docstring import GoogleDocstring

from sphinxcontrib import jinjadomain

PY3 = sys.version_info[0] > 2
if PY3:
    basestring = str


def jinja_directive(path, content):
    if isinstance(content, basestring):
        content = content.splitlines()
    yield ""
    yield ".. jinja:template:: {path}".format(**locals())
    yield ""
    for line in content:
        yield "   " + line
    yield ""


def parse_jinja_comment(path):
    """
    Parses jinja comment

    :param path: Path to jinja template
    :type path: str

    :returns: Jinja comment docstring
    :rtype: str
    """

    f = open(path, "r")
    contents = f.read()
    # res = re.match(
    #     r"\{\{\#-?(.+?)-?\#\}\}", contents, flags=re.MULTILINE | re.DOTALL
    # )

    res = re.compile(r"\{\{\#-?(.+?)-?\#\}\}[\r\n]+([^\r\n]+)", flags=re.MULTILINE | re.DOTALL)
    ret = res.findall(contents)
    if ret:
        return ret

    return None


class AutojinjaDirective(Directive):

    has_content = True
    required_arguments = 1
    option_spec = {}

    @property
    def endpoints(self):
        try:
            endpoints = re.split(r"\s*,\s*", self.options["endpoints"])
        except KeyError:
            # means 'endpoints' option was missing
            return None
        return frozenset(endpoints)

    @property
    def undoc_endpoints(self):
        try:
            endpoints = re.split(r"\s*,\s*", self.options["undoc-endpoints"])
        except KeyError:
            return frozenset()
        return frozenset(endpoints)

    def make_rst(self):
        env = self.state.document.settings.env
        path = self.arguments[0]
        parsed = parse_jinja_comment(
            os.path.join(env.config["jinja_template_path"], path)
        )

        if parsed:
            config = Config(napoleon_use_param=True, napoleon_use_rtype=True)
            for comment, macro_function in parsed:
                if macro_function.startswith("{{%- macro ") or macro_function.startswith("{{% macro "):
                    macro_function_signature = macro_function.replace("{{% macro ","").replace("{{%- macro ","").replace(" -%}}","").replace(" %}}","")
                    macro_function_name = macro_function_signature.split("(")[0]

                    docstring = GoogleDocstring(comment, config).lines()
                    docstring.append(macro_function_signature)
                    if docstring is not None and env.config["jinja_template_path"]:
                        for line in jinja_directive(macro_function_name, docstring):
                            yield line

        yield ""

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, "<autojinja>")
        nested_parse_with_titles(self.state, result, node)
        # result.pprint()
        return node.children


def setup(app):
    if not app.registry.has_domain("jinja"):
        jinjadomain.setup(app)
    app.add_directive("autojinja", AutojinjaDirective)
    app.add_config_value("jinja_template_path", "", None)
