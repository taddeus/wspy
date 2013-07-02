.PHONY: check clean

check:
	@python test.py

clean:
	find -name \*.pyc -delete
