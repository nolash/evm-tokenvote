doc:
	make -C doc/texinfo

python:
	make -C python

readme:
	make -C doc/texinfo readme
	pandoc -f docbook -t gfm doc/texinfo/build/docbook.xml > README.md
