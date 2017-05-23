# Default values for user options
PYTHON := python2.7
SETUPTOOLS_VERSION := 18.1
PARENT_DIR := $(realpath $(PWD)/..)

.PHONY: default
default: all

.PHONY: help
help:
	@echo "= Development ="
	@echo "make                -- build everything that needs building"
	@echo "make test           -- run all tests"
	@echo "make coverage       -- compute test coverage with coverage.py"
	@echo "make clean          -- Remove runtime generated files."
	@echo "make real-clean     -- Remove all files not in Git."
	@echo
	@echo "= Deployment ="
	@echo "make run            -- run the server in foreground mode"
	@echo "make run-uwsgi      -- run the app using uwsgi"

.PHONY: clean
clean:
	rm -rf ve/ pip-selfcheck.json

.PHONY: real-clean
real-clean:
	git clean -dfx
	rm -rf \
	    src/cipher.session src/duo-client-python src/duo-python \
	    src/img2pdf src/migrant src/pjpersist src/z3c.insist src/zodb \
	    src/zope.i18n src/zope.wfmc

ve: setup.py requirements.txt
	rm -rf ve/
	virtualenv -p $(PYTHON) ve
	ve/bin/pip install --upgrade pip
	ve/bin/pip install --upgrade setuptools==$(SETUPTOOLS_VERSION)
	ve/bin/pip install setuptools==$(SETUPTOOLS_VERSION) # for debian stable
	ve/bin/pip install -r ./requirements.txt

ve/bin/test:
	printf "#!/bin/bash\n$(PWD)/ve/bin/zope-testrunner --test-path $(PWD)/src \$$@\n" > ve/bin/test
	chmod 755 ve/bin/test

all: ve ve/bin/test

.PHONY: test
test: ve/bin/test
	ve/bin/test -vpc1 --all

.PHONY: coverage
coverage: ve
	rm -rf .coverage
	ve/bin/coverage run $(PWD)/ve/bin/zope-testrunner --test-path $(PWD)/src --all
	ve/bin/coverage xml --include '*/shoobx/mocks3/*'  --omit='*/test*'
	ve/bin/coverage html --include '*/shoobx/mocks3/*' --omit='*/test*'
	ve/bin/coverage report -m --include '*/shoobx/mocks3/*' --omit='*/test*'

.PHONY: run
run: ve
	ve/bin/sbx-mocks3-serve -c config/mocks3.cfg

.PHONY: run-uwsgi
run-uwsgi: ve
	uwsgi ./config/uwsgi.ini --need-app
