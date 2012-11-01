
import os
import os.path
import tempfile
import subprocess

from docutils import nodes, statemachine
from docutils.parsers.rst import directives, Directive
from sphinx.util.console import bold, purple, darkgreen, red, term_width_line

try: # This has changed in more recent docutils versions.
    from docutils.error_reporting import ErrorString
except ImportError:
    from docutils.utils.error_reporting import ErrorString

App = None

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
        App.info(msg)

    def run(self):
        self.assert_has_content()

        env = self.state.document.settings.env
        btest_base = env.config.btest_base
        btest_tests = env.config.btest_tests

        tag = self.arguments[0]

        if not btest_base:
            return self.error("error: btest_base not set in config")

        if not btest_tests:
            return self.error("error: btest_tests not set in config")

        if not os.path.exists(btest_base):
            return self.error("error: btest_base directory '%s' does not exists" % btest_base)

        if not os.path.exists(os.path.join(btest_base, btest_tests)):
            return self.error("error: btest_tests directory '%s' does not exists" % os.path.join(btest_base, btest_tests))

        os.chdir(btest_base)

        tmp = tempfile.mktemp(prefix="rst-btest")
        file = os.path.join(btest_tests, tag + ".btest")

        self.message("running test %s ..." % darkgreen(file))

        # Save the test.
        out = open(file, "w")
        for line in self.content:
            print >>out, line

        out.close()

        # Run it.
        os.environ["BTEST_RST_OUTPUT"] = tmp

        try:
            subprocess.check_call("btest -qd %s" % file, shell=True)
        except (OSError, IOError, subprocess.CalledProcessError), e:
            return self.error("btest: %s" % e)

        # Read output and turn into docutils.
        rawtext = open(tmp).read()

            # From docutils/parsers/rst/directives/misc.py
        include_lines = statemachine.string2lines(rawtext, convert_whitespace=1)
        self.state_machine.insert_input(include_lines, tmp)

        return []

directives.register_directive('btest', BTest)

def setup(app):
    global App
    App = app
    app.add_config_value('btest_base', None, 'env')
    app.add_config_value('btest_tests', None, 'env')
