VERSION=`cat VERSION`

.PHONY: all
all:

.PHONY: dist
dist:
	rm -rf build/*.tar.gz
	python setup.py sdist -d build
	@printf "Package: "; echo build/*.tar.gz

.PHONY:
upload: twine-check dist
	twine upload -u bro build/btest-$(VERSION).tar.gz

.PHONY: test
test:
	@(cd testing && make)

.PHONY: twine-check
twine-check:
	@type twine > /dev/null 2>&1 || \
		{ \
		echo "Uploading to PyPi requires 'twine' and it's not found in PATH."; \
		echo "Install it and/or make sure it is in PATH."; \
		echo "E.g. you could use the following command to install it:"; \
		echo "\tpip install twine"; \
		echo ; \
		exit 1; \
		}
