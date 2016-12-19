# Default values for user options
PYTHON := python2.7
SETUPTOOLS_VERSION := 18.1
SHOOBX_APP_BRANCH := master
PARENT_DIR := $(realpath $(PWD)/..)

.PHONY: default
default: all

.PHONY: help
help:
	@echo "= Development ="
	@echo "make                -- build everything that needs building"
	@echo "make test           -- run tests in level 1"
	@echo "make test-all       -- run all tests"
	@echo "make coverage       -- compute test coverage with coverage.py"
	@echo "make clean          -- Remove runtime generated files."
	@echo "make real-clean     -- Remove all files not in Git."
	@echo "make docs           -- Generate documentation."
	@echo
	@echo "= Deployment ="
	@echo "make run            -- run the server in foreground mode"
	@echo "make run-uwsgi      -- run the app using uwsgi"
	@echo
	@echo "= Jenkins ="
	@echo "make test-jenkins"
	@echo "make test-jenkins-with-coverage"
	@echo "make diff-cover"

.PHONY: clean
clean:
	rm -rf bin/ include/ lib/ local/ share/ pip-selfcheck.json

.PHONY: real-clean
real-clean:
	git clean -dfx
	rm -rf \
	    src/cipher.session src/duo-client-python src/duo-python \
	    src/img2pdf src/migrant src/pjpersist src/z3c.insist src/zodb \
	    src/zope.i18n src/zope.wfmc

.virtualenv: setup.py requirements.txt src/shoobx.app src/zodb
	rm -rf bin/ include/ lib/ local/ share/ pip-selfcheck.json
	virtualenv -p $(PYTHON) .
	bin/pip install --upgrade pip
	bin/pip install --upgrade setuptools==$(SETUPTOOLS_VERSION)
	bin/pip install setuptools==$(SETUPTOOLS_VERSION) # for debian stable
	bin/pip install -r ./requirements.txt
	touch .virtualenv

src/shoobx.app:
        # Optimization to either use an existing checkout or to use a shallow
        # one, since shoobx.app takes a long time to clone.
	if [ -d $(PARENT_DIR)/shoobx.app ]; \
	then \
	    ln -s $(PARENT_DIR)/shoobx.app src/shoobx.app; \
	else \
	    git clone \
	        --depth 1 --branch $(SHOOBX_APP_BRANCH) \
                git@git.shoobx.com:shoobx/shoobx.app.git \
	        src/shoobx.app; \
	fi;
        # Write the version file, so that pip get a proper version for
        # shoobx.app.
	cd src/shoobx.app && \
	  git describe --always | sed -e 's/-/+/' | sed -e 's/-/./g' > version

src/zodb:
	git clone \
	    --depth 1 --branch master \
	    https://github.com/Shoobx/ZODB.git \
	    src/zodb;

bin/test:
	printf "#!/bin/bash\n$(PWD)/bin/zope-testrunner --test-path $(PWD)/src \$$@\n" > bin/test
	chmod 755 bin/test

all: .virtualenv docs bin/test

.PHONY: test
test: bin/test
	bin/test -vpc1

.PHONY: test-all
test-all: bin/test
	bin/test -vpc1 --all

.PHONY: test-jenkins
test-jenkins: .virtualenv bin/test
	mkdir -p parts/test/testreports/
	rm -rf parts/test/testreports/*.xml
	bin/test --all --subunit \
	  | bin/python scripts/subunit2junit.py parts/test/testreports/all.xml \
	  | bin/python scripts/subunit2pyunit.py -vvv

.PHONY: test-jenkins-with-coverage
test-jenkins-with-coverage: .virtualenv
	mkdir -p testreports/
	rm -rf testreports/*.xml
	-bin/coverage run \
             $(PWD)/bin/zope-testrunner --test-path $(PWD)/src --all --subunit \
	   | bin/python scripts/subunit2junit.py testreports/all.xml \
	   | bin/python scripts/subunit2pyunit.py -vvv
	bin/coverage xml --include '*/shoobx/mocks3/*'  --omit='*/test*'
	bin/coverage html --include '*/shoobx/mocks3/*' --omit='*/test*'

.PHONY: diff-cover
diff-cover: .virtualenv
	bin/coverage-test -c
	bin/coverage xml --include '*/shoobx/app/*' --omit='*/test*'
	bin/diff-cover coverage.xml --html-report report.html

.PHONY: coverage
coverage: .virtualenv
	rm .coverage
	-bin/coverage run $(PWD)/bin/zope-testrunner --test-path $(PWD)/src --all
	bin/coverage xml --include '*/shoobx/mocks3/*'  --omit='*/test*'
	bin/coverage html --include '*/shoobx/mocks3/*' --omit='*/test*'

.PHONY: run
run:
	bin/sbx-mocks3-serve -c config/mocks3.cfg

.PHONY: run-uwsgi
run-uwsgi: .virtualenv
	uwsgi ./config/uwsgi.ini --need-app
