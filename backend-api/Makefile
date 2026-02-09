.PHONY: test compile quality

test:
	python3 -m unittest discover -s tests -p 'test_*.py'

compile:
	python3 -m compileall app tests scripts

quality: test compile
