import os
import os.path
import re
import subprocess

from docutils import nodes, utils
from docutils.parsers.rst import Directive, Parser, directives
from docutils.transforms import Transform

from sphinx.directives.code import LiteralInclude
from sphinx.errors import SphinxError
from sphinx.util import logging
from sphinx.util.console import darkgreen, red

logger = logging.getLogger(__name__)

Initialized = False
App = None
Reporter = None
BTestBase = None
BTestTests = None
BTestTmp = None

Tests = {}
Includes = set()

# Maps file name extensiosn to Pygments formatter.
ExtMappings = {"bro": "bro", "rst": "rest", "c": "c", "cc": "cc", "py": "python"}


def init(settings, reporter):
    global Initialized, App, Reporter, BTestBase, BTestTests, BTestTmp

    Initialized = True
    Reporter = reporter
    BTestBase = settings.env.config.btest_base
    BTestTests = settings.env.config.btest_tests
    BTestTmp = settings.env.config.btest_tmp

    if not BTestBase:
        raise SphinxError("error: btest_base not set in config")

    if not BTestTests:
        raise SphinxError("error: btest_tests not set in config")

    if not os.path.exists(BTestBase):
        raise SphinxError(f"error: btest_base directory '{BTestBase}' does not exists")

    joined = os.path.join(BTestBase, BTestTests)

    if not os.path.exists(joined):
        raise SphinxError(f"error: btest_tests directory '{joined}' does not exists")

    if not BTestTmp:
        BTestTmp = os.path.join(App.outdir, ".tmp/rst_output")

    BTestTmp = os.path.abspath(BTestTmp)

    if not os.path.exists(BTestTmp):
        os.makedirs(BTestTmp)


def parsePartial(rawtext, settings):
    parser = Parser()
    document = utils.new_document("<partial node>")
    document.settings = settings
    parser.parse(rawtext, document)
    return document.children


class Test:
    def __init__(self):
        self.has_run = False

    def run(self):
        if self.has_run:
            return

        logger.info(f"running test {darkgreen(self.path)} ...")

        self.rst_output = os.path.join(BTestTmp, f"{self.tag}")
        os.environ["BTEST_RST_OUTPUT"] = self.rst_output

        self.cleanTmps()

        try:
            subprocess.check_call(f"btest -S {self.path}", shell=True)
        except (OSError, subprocess.CalledProcessError) as e:
            # Equivalent to Directive.error(); we don't have an
            # directive object here and can't pass it in because
            # it doesn't pickle.
            logger.warning(red(f"BTest error: {e}"))

    def cleanTmps(self):
        subprocess.call(f"rm {self.rst_output}#* 2>/dev/null", shell=True)


class BTestTransform(Transform):
    default_priority = 800

    def apply(self):
        pending = self.startnode
        (test, part) = pending.details

        os.chdir(BTestBase)

        if test.tag not in BTestTransform._run:
            test.run()
            BTestTransform._run.add(test.tag)

        try:
            rawtext = open(f"{test.rst_output}#{part}").read()
        except OSError:
            rawtext = ""

        settings = self.document.settings
        content = parsePartial(rawtext, settings)
        pending.replace_self(content)

    _run = set()


class BTest(Directive):
    required_arguments = 1
    final_argument_whitespace = True
    has_content = True

    def error(self, msg):
        self.state.document.settings.env.note_reread()
        msg = red(msg)
        msg = self.state.document.reporter.error(str(msg), line=self.lineno)
        return [msg]

    def message(self, msg):
        Reporter.info(msg)

    def run(self):
        if not Initialized:
            # FIXME: Better way to handle one-time initialization?
            init(self.state.document.settings, self.state.document.reporter)

        os.chdir(BTestBase)

        self.assert_has_content()
        document = self.state_machine.document

        tag = self.arguments[0]

        if tag not in Tests:
            test = Test()
            test.tag = tag
            test.path = os.path.join(BTestTests, tag + ".btest")
            test.parts = 0
            Tests[tag] = test

        test = Tests[tag]
        test.parts += 1
        part = test.parts

        # Save the test.

        if part == 1:
            file = test.path
        else:
            file = f"{test.path}#{part}"

        out = open(file, "w")
        for line in self.content:
            out.write(f"{line}\n")

        out.close()

        details = (test, part)
        pending = nodes.pending(BTestTransform, details, rawsource=self.block_text)
        document.note_pending(pending)

        return [pending]


class BTestInclude(LiteralInclude):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def error(self, msg):
        self.state.document.settings.env.note_reread()
        msg = red(msg)
        msg = self.state.document.reporter.error(str(msg), line=self.lineno)
        return [msg]

    def message(self, msg):
        Reporter.info(msg)

    def run(self):
        if not Initialized:
            # FIXME: Better way to handle one-time initialization?
            init(self.state.document.settings, self.state.document.reporter)

        document = self.state.document
        if not document.settings.file_insertion_enabled:
            return [
                document.reporter.warning("File insertion disabled", line=self.lineno)
            ]
        env = document.settings.env

        expanded_arg = os.path.expandvars(self.arguments[0])
        sphinx_src_relation = os.path.relpath(expanded_arg, env.srcdir)
        self.arguments[0] = os.path.join(os.sep, sphinx_src_relation)

        (root, ext) = os.path.splitext(self.arguments[0])

        if ext.startswith("."):
            ext = ext[1:]

        if ext in ExtMappings:
            self.options["language"] = ExtMappings[ext]
        else:
            # Note that we always need to set a language, otherwise the
            # linenos/emphasis don't seem to work.
            self.options["language"] = "none"

        self.options["linenos"] = True
        self.options["prepend"] = f"{os.path.basename(self.arguments[0])}\n"
        self.options["emphasize-lines"] = "1,1"
        self.options["style"] = "X"

        retnode = super().run()

        os.chdir(BTestBase)

        tag = os.path.normpath(self.arguments[0])
        tag = os.path.relpath(tag, BTestBase)
        tag = re.sub("[^a-zA-Z0-9-]", "_", tag)
        tag = re.sub("__+", "_", tag)

        if tag.startswith("_"):
            tag = tag[1:]

        test_path = "include-" + tag + ".btest"

        if BTestTests:
            test_path = os.path.join(BTestTests, test_path)

        test_path = os.path.abspath(test_path)

        i = 1
        (base, ext) = os.path.splitext(test_path)
        while test_path in Includes:
            i += 1

            test_path = f"{base}@{i}"
            if ext:
                test_path += ext

        Includes.add(test_path)

        out = open(test_path, "w")
        out.write("# @TEST-EXEC: cat %INPUT >output && btest-diff output\n\n")

        for i in retnode:
            out.write(i.rawsource)
        out.close()

        for node in retnode:
            node["classes"] += ["btest-include"]

        return retnode


directives.register_directive("btest", BTest)
directives.register_directive("btest-include", BTestInclude)


def setup(app):
    global App
    App = app

    app.add_config_value("btest_base", None, "env")
    app.add_config_value("btest_tests", None, "env")
    app.add_config_value("btest_tmp", None, "env")
