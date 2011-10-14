
all:

.PHONY: dist

dist:
	rm -rf build/*.tar.gz
	python setup.py sdist -d build
	@printf "Package: "; echo build/*.tar.gz

www: dist
	cp dist/* $(WWW)
	# cp CHANGES $(WWW)
