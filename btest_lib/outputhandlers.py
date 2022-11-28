import atexit
import json
import multiprocessing
import os
import socket
import sys
import time
import xml
import xml.dom.minidom

from datetime import datetime


class OutputHandler:
    def __init__(self, options):
        """Base class for reporting progress and results to user. We derive
        several classes from this one, with the one being used depending on
        which output the users wants.

        A handler's method are called from test TestMgr and may be called
        interleaved from different tests. However, the TestMgr locks before
        each call so that it's guaranteed that two calls don't run
        concurrently.

        options: An optparser with the global options.
        """
        self._buffered_output = {}
        self._options = options

    def prepare(self, mgr):
        """The TestManager calls this with itself as an argument just before
        it starts running tests."""
        pass

    def options(self):
        """Returns the current optparser instance."""
        return self._options

    def threadPrefix(self):
        """With multiple threads, returns a string with the thread's name in
        a form suitable to prefix output with. With a single thread, returns
        the empty string."""
        if self.options().threads > 1:
            return "[%s]" % multiprocessing.current_process().name
        else:
            return ""

    @staticmethod
    def _output(msg, nl=True, file=None):
        if not file:
            file = sys.stderr

        if nl:
            print(msg, file=file)
        else:
            if msg:
                print(msg, end=" ", file=file)

    def output(self, test, msg, nl=True, file=None):
        """Output one line of output to user. Unless we're just using a single
        thread, this will be buffered until the test has finished;
        then all output is printed as a block.

        This should only be called from other members of this class, or
        derived classes, not from tests.
        """
        if self.options().threads < 2:
            self._output(msg, nl, file)
            return

        try:
            self._buffered_output[test.name] += [(msg, nl, file)]
        except KeyError:
            self._buffered_output[test.name] = [(msg, nl, file)]

    def replayOutput(self, test):
        """Prints out all output buffered in threaded mode by output()."""
        if test.name not in self._buffered_output:
            return

        for (msg, nl, file) in self._buffered_output[test.name]:
            self._output(msg, nl, file)

        self._buffered_output[test.name] = []

    # Methods to override.
    def testStart(self, test):
        """Called just before a test begins."""

    def testCommand(self, test, cmdline):
        """Called just before a command line is executed for a trace."""

    def testProgress(self, test, msg):
        """Called when a test signals having made progress."""

    def testSucceeded(self, test, msg):
        """Called when a test was successful."""

    def testFailed(self, test, msg):
        """Called when a test failed."""

    def testSkipped(self, test, msg):
        """Called when a test is skipped because its dependencies aren't met."""

    def testFinished(self, test, msg):
        """
        Called just after a test has finished being processed, independent of
        success or failure. Not called for skipped tests.
        """

    def testUnstable(self, test, msg):
        """Called when a test failed initially but succeeded in a retry."""

    def finished(self):
        """Called when all tests have been executed."""


class Forwarder(OutputHandler):
    """
    Forwards output to several other handlers.

    options: An optparser with the global options.

    handlers: List of output handlers to forward to.
    """
    def __init__(self, options, handlers):
        OutputHandler.__init__(self, options)
        self._handlers = handlers

    def prepare(self, mgr):
        """Called just before test manager starts running tests."""
        for h in self._handlers:
            h.prepare(mgr)

    def testStart(self, test):
        """Called just before a test begins."""
        for h in self._handlers:
            h.testStart(test)

    def testCommand(self, test, cmdline):
        """Called just before a command line is executed for a trace."""
        for h in self._handlers:
            h.testCommand(test, cmdline)

    def testProgress(self, test, msg):
        """Called when a test signals having made progress."""
        for h in self._handlers:
            h.testProgress(test, msg)

    def testSucceeded(self, test, msg):
        """Called when a test was successful."""
        for h in self._handlers:
            h.testSucceeded(test, msg)

    def testFailed(self, test, msg):
        """Called when a test failed."""
        for h in self._handlers:
            h.testFailed(test, msg)

    def testSkipped(self, test, msg):
        for h in self._handlers:
            h.testSkipped(test, msg)

    def testFinished(self, test, msg):
        for h in self._handlers:
            h.testFinished(test, msg)

    def testUnstable(self, test, msg):
        """Called when a test failed initially but succeeded in a retry."""
        for h in self._handlers:
            h.testUnstable(test, msg)

    def replayOutput(self, test):
        for h in self._handlers:
            h.replayOutput(test)

    def finished(self):
        for h in self._handlers:
            h.finished()


class Standard(OutputHandler):
    def testStart(self, test):
        self.output(test, self.threadPrefix(), nl=False)
        self.output(test, "%s ..." % test.displayName(), nl=False)
        test._std_nl = False

    def testCommand(self, test, cmdline):
        pass

    def testProgress(self, test, msg):
        """Called when a test signals having made progress."""
        if not test._std_nl:
            self.output(test, "")

        self.output(test, "  - " + msg)
        test._std_nl = True

    def testSucceeded(self, test, msg):
        sys.stdout.flush()
        self.finalMsg(test, msg)

    def testFailed(self, test, msg):
        self.finalMsg(test, msg)

    def testSkipped(self, test, msg):
        self.finalMsg(test, msg)

    def finalMsg(self, test, msg):
        if test._std_nl:
            self.output(test, self.threadPrefix(), nl=False)
            self.output(test, "%s ..." % test.displayName(), nl=False)

        self.output(test, msg)

    def testUnstable(self, test, msg):
        self.finalMsg(test, msg)


class Console(OutputHandler):
    """
    Output handler that writes colorful progress report to the console.

    This handler works well in settings that can handle coloring but not
    cursor placement commands (for example because moving to the beginning of
    the line overwrites other surrounding output); it's what the
    ``--show-all`` output uses. In contrast, the *CompactConsole* handler uses
    cursor placement in addition for a more space-efficient output.
    """
    Green = "\033[32m"
    Red = "\033[31m"
    Yellow = "\033[33m"
    Gray = "\033[37m"
    DarkGray = "\033[1;30m"
    Normal = "\033[0m"

    def __init__(self, options):
        OutputHandler.__init__(self, options)
        self.show_all = True

    def testStart(self, test):
        msg = "[%3d%%] %s ..." % (test.mgr.percentage(), test.displayName())
        self._consoleOutput(test, msg, False)

    def testProgress(self, test, msg):
        """Called when a test signals having made progress."""
        msg = self.DarkGray + "(%s)" % msg + self.Normal
        self._consoleOutput(test, msg, True)

    def testSucceeded(self, test, msg):
        if test.known_failure:
            msg = self.Yellow + msg + self.Normal
        else:
            msg = self.Green + msg + self.Normal

        self._consoleOutput(test, msg, self.show_all)

    def testFailed(self, test, msg):
        if test.known_failure:
            msg = self.Yellow + msg + self.Normal
        else:
            msg = self.Red + msg + self.Normal

        self._consoleOutput(test, msg, True)

    def testUnstable(self, test, msg):
        msg = self.Yellow + msg + self.Normal
        self._consoleOutput(test, msg, True)

    def testSkipped(self, test, msg):
        msg = self.Gray + msg + self.Normal
        self._consoleOutput(test, msg, self.show_all)

    def finished(self):
        sys.stdout.flush()

    def _consoleOutput(self, test, msg, sticky):
        self._consoleWrite(test, msg, sticky)

    def _consoleWrite(self, test, msg, sticky):
        sys.stdout.write(msg.strip() + " ")

        if sticky:
            sys.stdout.write("\n")

        sys.stdout.flush()


class CompactConsole(Console):
    """
    Output handler that writes compact, colorful progress report to
    the console while also keeping the output compact by keeping
    output only for failing tests.

    This handler adds cursor mods and navigation to the coloring provided by
    the Console class and hence needs settings that can handle both.
    """
    CursorOff = "\033[?25l"
    CursorOn = "\033[?25h"
    EraseToEndOfLine = "\033[2K"

    def __init__(self, options):
        Console.__init__(self, options)
        self.show_all = False

        def cleanup():
            sys.stdout.write(self.CursorOn)

        atexit.register(cleanup)

    def testStart(self, test):
        test.console_last_line = None
        self._consoleOutput(test, "", False)
        sys.stdout.write(self.CursorOff)

    def testProgress(self, test, msg):
        """Called when a test signals having made progress."""
        msg = " " + self.DarkGray + "(%s)" % msg + self.Normal
        self._consoleAugment(test, msg)

    def testFinished(self, test, msg):
        test.console_last_line = None

    def finished(self):
        sys.stdout.write(self.EraseToEndOfLine)
        sys.stdout.write("\r")
        sys.stdout.write(self.CursorOn)
        sys.stdout.flush()

    def _consoleOutput(self, test, msg, sticky):
        line = "[%3d%%] %s ..." % (test.mgr.percentage(), test.displayName())

        if msg:
            line += " " + msg

        test.console_last_line = line
        self._consoleWrite(test, line, sticky)

    def _consoleAugment(self, test, msg):
        sys.stdout.write(self.EraseToEndOfLine)
        sys.stdout.write(" %s" % msg.strip())
        sys.stdout.write("\r%s" % test.console_last_line)
        sys.stdout.flush()

    def _consoleWrite(self, test, msg, sticky):
        sys.stdout.write(chr(27) + '[2K')
        sys.stdout.write("\r%s" % msg.strip())

        if sticky:
            sys.stdout.write("\n")
            test.console_last_line = None

        sys.stdout.flush()


class Brief(OutputHandler):
    """Output handler for producing the brief output format."""
    def testStart(self, test):
        pass

    def testCommand(self, test, cmdline):
        pass

    def testProgress(self, test, msg):
        """Called when a test signals having made progress."""
        pass

    def testSucceeded(self, test, msg):
        pass

    def testFailed(self, test, msg):
        self.output(test, self.threadPrefix(), nl=False)
        self.output(test, "%s ... %s" % (test.displayName(), msg))

    def testUnstable(self, test, msg):
        self.output(test, self.threadPrefix(), nl=False)
        self.output(test, "%s ... %s" % (test.displayName(), msg))

    def testSkipped(self, test, msg):
        pass


class Verbose(OutputHandler):
    """Output handler for producing the verbose output format."""
    def testStart(self, test):
        self.output(test, self.threadPrefix(), nl=False)
        self.output(test, "%s ..." % test.displayName())

    def testCommand(self, test, cmdline):
        part = ""

        if cmdline.part > 1:
            part = " [part #%d]" % cmdline.part

        self.output(test, self.threadPrefix(), nl=False)
        self.output(test, "  > %s%s" % (cmdline.cmdline, part))

    def testProgress(self, test, msg):
        """Called when a test signals having made progress."""
        self.output(test, "  - " + msg)

    def testSucceeded(self, test, msg):
        self.output(test, self.threadPrefix(), nl=False)
        self.showTestVerbose(test)
        self.output(test, "... %s %s" % (test.displayName(), msg))

    def testFailed(self, test, msg):
        self.output(test, self.threadPrefix(), nl=False)
        self.showTestVerbose(test)
        self.output(test, "... %s %s" % (test.displayName(), msg))

    def testUnstable(self, test, msg):
        self.output(test, self.threadPrefix(), nl=False)
        self.showTestVerbose(test)
        self.output(test, "... %s %s" % (test.displayName(), msg))

    def testSkipped(self, test, msg):
        self.output(test, self.threadPrefix(), nl=False)
        self.showTestVerbose(test)
        self.output(test, "... %s %s" % (test.displayName(), msg))

    def showTestVerbose(self, test):
        if not os.path.exists(test.verbose):
            return

        for line in open(test.verbose):
            self.output(test, "  > [test-verbose] %s" % line.strip())


class Diag(OutputHandler):
    def __init__(self, options, all=False, file=None):
        """Output handler for producing the diagnostic output format.

        options: An optparser with the global options.

        all: Print diagnostics also for succeeding tests.

        file: Output into given file rather than console.
        """
        OutputHandler.__init__(self, options)
        self._all = all
        self._file = file

    def showDiag(self, test):
        """Generates diagnostics for a test."""
        for line in test.diagmsgs:
            self.output(test, "  % " + line, True, self._file)

        for f in (test.diag, os.path.join(test.tmpdir, ".stderr")):
            if not f:
                continue

            if os.path.isfile(f):
                self.output(test, "  % cat " + os.path.basename(f), True, self._file)
                for line in open(f):
                    self.output(test, "  " + line.rstrip(), True, self._file)
                self.output(test, "", True, self._file)

        if self.options().wait and not self._file:
            self.output(test, "<Enter> ...")
            try:
                sys.stdin.readline()
            except KeyboardInterrupt:
                sys.exit(1)

    def testCommand(self, test, cmdline):
        pass

    def testSucceeded(self, test, msg):
        if self._all:
            if self._file:
                self.output(test, "%s ... %s" % (test.displayName(), msg), True, self._file)

            self.showDiag(test)

    def testFailed(self, test, msg):
        if self._file:
            self.output(test, "%s ... %s" % (test.displayName(), msg), True, self._file)

        if (not test.known_failure) or self._all:
            self.showDiag(test)

    def testUnstable(self, test, msg):
        if self._file:
            self.output(test, "%s ... %s" % (test.displayName(), msg), True, self._file)

    def testSkipped(self, test, msg):
        if self._file:
            self.output(test, "%s ... %s" % (test.displayName(), msg), True, self._file)


class SphinxOutput(OutputHandler):
    def __init__(self, options, all=False, file=None):
        """Output handler for producing output when running from
        Sphinx. The main point here is that we save all diagnostic output to
        $BTEST_RST_OUTPUT.

        options: An optparser with the global options.
        """
        OutputHandler.__init__(self, options)

        self._output = None

        try:
            self._rst_output = os.environ["BTEST_RST_OUTPUT"]
        except KeyError:
            print("warning: environment variable BTEST_RST_OUTPUT not set, will not produce output",
                  file=sys.stderr)
            self._rst_output = None

    def testStart(self, test):
        self._output = None

    def testCommand(self, test, cmdline):
        if not self._rst_output:
            return

        self._output = "%s#%s" % (self._rst_output, cmdline.part)
        self._part = cmdline.part

    def testSucceeded(self, test, msg):
        pass

    def testFailed(self, test, msg):
        if not self._output:
            return

        out = open(self._output, "a")

        print("\n.. code-block:: none ", file=out)
        print("\n  ERROR executing test '%s' (part %s)\n" % (test.displayName(), self._part),
              file=out)

        for line in test.diagmsgs:
            print("  % " + line, file=out)

        test.diagmsgs = []

        for f in (test.diag, os.path.join(test.tmpdir, ".stderr")):
            if not f:
                continue

            if os.path.isfile(f):
                print("  % cat " + os.path.basename(f), file=out)
                for line in open(f):
                    print("   %s" % line.strip(), file=out)
                print(file=out)

    def testUnstable(self, test, msg):
        pass

    def testSkipped(self, test, msg):
        pass


class XMLReport(OutputHandler):

    RESULT_PASS = "pass"
    RESULT_FAIL = "failure"
    RESULT_SKIP = "skipped"
    RESULT_UNSTABLE = "unstable"

    def __init__(self, options, xmlfile):
        """Output handler for producing an XML report of test results.

        options: An optparser with the global options.

        file: Output into given file
        """
        OutputHandler.__init__(self, options)
        self._file = xmlfile
        self._start = time.time()
        self._timestamp = datetime.now().isoformat()

    def prepare(self, mgr):
        self._results = mgr.list([])

    def testStart(self, test):
        pass

    def testCommand(self, test, cmdline):
        pass

    def makeTestCaseElement(self, doc, testsuite, name, duration):
        parts = name.split('.')
        if len(parts) > 1:
            classname = ".".join(parts[:-1])
            name = parts[-1]
        else:
            classname = parts[0]
            name = parts[0]

        e = doc.createElement("testcase")
        e.setAttribute("classname", classname)
        e.setAttribute("name", name)
        e.setAttribute("time", str(duration))
        testsuite.appendChild(e)

        return e

    def getContext(self, test, context_file):
        context = ""
        for line in test.diagmsgs:
            context += "  % " + line + "\n"

        for f in (test.diag, os.path.join(test.tmpdir, context_file)):
            if not f:
                continue

            if os.path.isfile(f):
                context += "  % cat " + os.path.basename(f) + "\n"
                for line in open(f):
                    context += "  " + line.strip() + "\n"

        return context

    def addTestResult(self, test, status):
        context = ""

        if status != self.RESULT_PASS:
            context = self.getContext(test, ".stderr")

        res = {
            "name": test.displayName(),
            "status": status,
            "context": context,
            "duration": time.time() - test.start,
        }

        self._results.append(res)

    def testSucceeded(self, test, msg):
        self.addTestResult(test, self.RESULT_PASS)

    def testFailed(self, test, msg):
        self.addTestResult(test, self.RESULT_FAIL)

    def testUnstable(self, test, msg):
        self.addTestResult(test, self.RESULT_UNSTABLE)

    def testSkipped(self, test, msg):
        self.addTestResult(test, self.RESULT_SKIP)

    def finished(self):
        num_tests = 0
        num_failures = 0
        doc = xml.dom.minidom.Document()
        testsuite = doc.createElement("testsuite")
        doc.appendChild(testsuite)

        for res in self._results:
            test_case = self.makeTestCaseElement(doc, testsuite, res["name"], res["duration"])

            if res["status"] != self.RESULT_PASS:
                e = doc.createElement(res["status"])
                e.setAttribute("type", res["status"])
                text_node = doc.createTextNode(res["context"])
                e.appendChild(text_node)
                test_case.appendChild(e)

                if res["status"] == self.RESULT_FAIL:
                    num_failures += 1

            num_tests += 1

        # These attributes are set in sorted order so that resulting XML output
        # is stable across Python versions.  Before Python 3.8, attributes
        # appear in sorted order.  After Python 3.8, attributes appear in
        # order specified by the user.  Would be best to use an XML canonifier
        # method here and Python 3.8+ does provide one, except earlier versions
        # would need to rely on a third-party lib to do the same. References:
        #   https://bugs.python.org/issue34160
        #   https://mail.python.org/pipermail/python-dev/2019-March/156709.html
        testsuite.setAttribute("errors", str(0))
        testsuite.setAttribute("failures", str(num_failures))
        testsuite.setAttribute("hostname", socket.gethostname())
        testsuite.setAttribute("tests", str(num_tests))
        testsuite.setAttribute("time", str(time.time() - self._start))
        testsuite.setAttribute("timestamp", self._timestamp)

        print(doc.toprettyxml(indent="    "), file=self._file)
        self._file.close()


class ChromeTracing(OutputHandler):
    """Output in Chrome tracing format.

    Output files can be loaded into Chrome browser under about:tracing, or
    converted to standalone HTML files with `trace2html`.
    """
    def __init__(self, options, tracefile):
        OutputHandler.__init__(self, options)
        self._file = tracefile

    def prepare(self, mgr):
        self._results = mgr.list([])

    def testFinished(self, test, _):
        self._results.append({
            "name": test.name,
            "ts": test.start * 1e6,
            "tid": multiprocessing.current_process().pid,
            "pid": 1,
            "ph": "X",
            "cat": "test",
            "dur": (time.time() - test.start) * 1e6,
        })

    def finished(self):
        print(json.dumps(list(self._results)), file=self._file)
        self._file.close()


def create_output_handler(options):

    output_handlers = []

    if options.verbose:
        output_handlers += [Verbose(options, )]

    elif options.brief:
        output_handlers += [Brief(options, )]

    else:
        if sys.stdout.isatty():
            if options.show_all:
                output_handlers += [Console(options, )]
            else:
                output_handlers += [CompactConsole(options, )]
        else:
            output_handlers += [Standard(options, )]

    if options.diagall:
        output_handlers += [Diag(options, True, None)]

    elif options.diag:
        output_handlers += [Diag(options, False, None)]

    if options.diagfile:
        try:
            diagfile = open(options.diagfile, "w", 1)
            output_handlers += [Diag(options, options.diagall, diagfile)]

        except IOError as e:
            print("cannot open %s: %s" % (options.diagfile, e), file=sys.stderr)

    if options.sphinx:
        output_handlers += [SphinxOutput(options)]

    if options.xmlfile:
        try:
            xmlfile = open(options.xmlfile, "w", 1)
            output_handlers += [XMLReport(options, xmlfile)]

        except IOError as e:
            print("cannot open %s: %s" % (options.xmlfile, e), file=sys.stderr)

    if options.tracefile:
        try:
            tracefile = open(options.tracefile, "w", 1)
            output_handlers += [ChromeTracing(options, tracefile)]

        except IOError as e:
            print("cannot open %s: %s" % (options.tracefile, e), file=sys.stderr)

    return Forwarder(options, output_handlers)
