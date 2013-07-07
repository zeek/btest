
all:

.PHONY: dist

dist:
	rm -rf build/*.tar.gz
	python setup.py sdist -d build
	@printf "Package: "; echo build/*.tar.gz

test:
	@(cd testing && make)
