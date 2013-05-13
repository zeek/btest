
import os
import os.path
import tempfile
import subprocess

from docutils import nodes, statemachine, utils
from docutils.parsers.rst import directives, Directive, DirectiveError, Parser
from docutils.transforms import TransformError, Transform
from sphinx.util.console import bold, purple, darkgreen, red, term_width_line

Initialized = False
Reporter = None
BTestBase = None
BTestTests = None

Tests = {}

def init(settings, reporter):
    global Intialized, Reporter, BTestBase, BTestTests

    Initialized = True
    Reporter = reporter
    BTestBase = settings.env.config.btest_base
    BTestTests = settings.env.config.btest_tests

    if not BTestBase:
        return self.error("error: btest_base not set in config")

    if not BTestTests:
        return self.error("error: btest_tests not set in config")

    if not os.path.exists(BTestBase):
        return self.error("error: btest_base directory '%s' does not exists" % BTestBase)

    joined = os.path.join(BTestBase, BTestTests)

    if not os.path.exists(joined):
        return self.error("error: btest_tests directory '%s' does not exists" % joined)

def parsePartial(rawtext, settings):
    parser = Parser()
    document = utils.new_document("<partial node>")
    document.settings = settings
    parser.parse(rawtext, document)
    return document.children

class Test(object):
    def __init__(self):
        self.has_run = False

    def run(self):
        if self.has_run:
            return

        Reporter.info("running test %s ..." % "X")
        self.has_run = True

        self.rst_output = tempfile.mktemp(prefix="rst-btest")
        os.environ["BTEST_RST_OUTPUT"] = self.rst_output

        try:
            subprocess.check_call("btest -qd %s" % self.path, shell=True)
        except (OSError, IOError, subprocess.CalledProcessError), e:
            # Equivalent to Directive.error(); we don't have an
            # directive object here and can't pass it in because
            # it doesn't pickle.
            return Reporter.error("btest error: %s" % e)

class BTestTransform(Transform):

    default_priority = 800

    def apply(self):
        pending = self.startnode
        test = pending.details

        os.chdir(BTestBase)
        test.run()

        try:
            rawtext = open(test.rst_output).read()
        except IOError, e:
            rawtext = "BTest input error: %s" % e

        if len(rawtext):
            settings = self.document.settings
            content = parsePartial(rawtext, settings)
            pending.replace_self(content)
        else:
            pending.parent.parent.remove(pending.parent)

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

        if not tag in Tests:
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
            file = test.path + "#%d" % part

        out = open(file, "w")
        for line in self.content:
            print >>out, line

        out.close()

        details = test
        pending = nodes.pending(BTestTransform, details, rawsource=self.block_text)
        document.note_pending(pending)

        return [pending]

directives.register_directive('btest', BTest)

def setup(app):
    app.add_config_value('btest_base', None, 'env')
    app.add_config_value('btest_tests', None, 'env')
