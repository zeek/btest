# 
# BTest's output handlers presenting results to the user
#

class OutputHandler:
    def __init__(self):
        """Base class for reporting progress and results to user. We derive
        several classes from this one, with the one being used depending on
        which output the users wants.

        A handler's method are called from test TestMgr and may be called
        interleaved from different tests. However, the TestMgr locks before
        each call so that it's guaranteed that two calls don't run
        concurrently.
        """
        self._buffered_output = []

    def output(self, test, msg, nl=True, file=None):
        """Output one line of output to user. In non-threaded mode, this will
        be printed out directly to stderr. In threaded-mode, this will be
        buffered until the test has finished; then all output is printed as a
        block.

        This should only be called from other members of this class, or
        derived classes, not from tests.
        """
        if not Options.threads:
            output(msg, nl, file)
            return

        else:
			try:
				self._buffered_output[test.name] += [(msg, nl, file)]
			except KeyError:
				self._buffered_output[test.name] = [(msg, nl, file)]

    def replayOutput(self, test):
        """Prints out all output buffered in threaded mode by output()."""
        if not test.name in self._buffered_output:
            return
        
        for (msg, nl, file) in self._buffered_output:
            output(msg, nl, file)
            
        self._buffered_output[test.name] = []

    # Methods to override.
    def testStart(self, test):
        """Called just before a test begins."""
        pass

    def testCommand(self, test, cmdline):
        """Called just before a command line is exected for a trace."""
        pass

    def testSucceeded(self, test):
        """Called when a test was successful."""
        pass

    def testFailed(self, test):
        """Called when a test failed."""
        pass

    def testSkipped(self, test):
        """Called when a test is skipped because its dependencies aren't met."""
        pass

class OutputForwarder(OutputHandler):
	"""Forwards output to several other handlers.

        handlers: List of output handlers to forward to.
    """
    def __init__(self, handlers):
        self._handlers = handlers
        
    def testStart(self, test):
        """Called just before a test begins."""
        for h in self._handlers:
            h.testStart(test)

    def testCommand(self, test, cmdline):
        """Called just before a command line is exected for a trace."""
		for h in self._handlers:
			h.testCommand(test, cmdline)

    def testSucceeded(self, test):
        """Called when a test was successful."""
		for h in self._handlers:
			h.testSucceeded(test)

    def testFailed(self, test):
        """Called when a test failed."""
		for h in self._handlers:
			h.testFailed(test)

    def testSkipped(self, test):
		for h in self._handlers:
			h.testSkipped(test)


class Standard(OutputHandler):
    def testStart(self, test):
        self.output(test, "%s ..." % name, nl=False)

    def testCommand(self, test, cmdline):
        pass

    def testSucceeded(self, test):
        self.output(test, "ok")

    def testFailed(self, test):
        pass

    def testSkipped(self, test):
        self.output(test, "not available, skipped")


class Brief(OutputHandler):
	"""Output handler for producing the brief output format."""
    def testStart(self, test):
        pass

    def testCommand(self, test, cmdline):
        pass

    def testSucceeded(self, test):
        pass

    def testFailed(self, test):
        self.output(test, "%s ... failed" % name)

    def testSkipped(self, test):
        pass

class Verbose(OutputHandler):
	"""Output handler for producing the verbose output format."""

    def testStart(self, test):
        self.output(test, "%s ..." % name)

    def testCommand(self, test, cmdline):
        self.output(test, "  > %s" % cmdline)

    def testSucceeded(self, test):
        self.output(test, "... %s ok" % name)

    def testFailed(self, test):
        self.output(test, "... %s failed" % name)

    def testSkipped(self, test):
        self.output(test, "... %s not available, skipped" % name)

class Diag(OutputHandler):
    def __init__(self, all=False, file=None):
    	"""Output handler for producing the diagnostic output format.

        all: Print diagnostics also for succeeding tests.

        file: Output into given file rather than console.
        """
        self._all = False
		self._file = file

	def showDiag(self, test):
		"""Generates diagnostics for a test."""
        for line in test.diagmsgs:
            self.output(test, "  % " + line, self._file)

        for f in (test.diag, ".stderr"):
            if not f:
                continue

            if os.path.isfile(f):
                self.output(test, "  % cat " + os.path.basename(f), self._file)
                for line in open(f):
                    self.output(test, "  " + line.strip(), self._file)
                self.output(test, "", self._file)

        if Options.wait and not file:
            self.output(test, "<Enter> ...")
            try:
                sys.stdin.readline()
            except KeyboardInterrupt:
                sys.exit(1)

    def testCommand(self, test, cmdline):
        pass

    def testSucceeded(self, test):
        if self._all:
            self.output(test, "%s ... ok" % name, self._file)
            self.showDiag()

    def testFailed(self, test):
        self.output(test, "%s ... failed" % name, True, self._file)
        self.showDiag()

    def testSkipped(self, test):
        self.output(test, "%s ... not available, skipped" % name, True, self._file)
