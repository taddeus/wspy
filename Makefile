.PHONY: test clean

test:
	python test.py

clean:
	rm `find -name \*.pyc`
