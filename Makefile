.PHONY: check clean

check:
	@python test/server.py

clean:
	find -name \*.pyc -delete
