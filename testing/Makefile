
all:
	@../btest -j -d -f diag.log
	@if [ -d .tmp ] && [ "$$(ls -A .tmp)" ]; then \
	    echo "ERROR: Left-over files in .tmp"; \
	    ls -lA .tmp; \
	    exit 1; \
	fi

cleanup:
	@rm -f diag.log
	@rm -f .btest.failed.dat
	@rm -rf .tmp
