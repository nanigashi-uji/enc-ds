PYTHON     ?= python3
PIP        ?= pip3
NPM        ?= npm

TMPDIR     ?= /tmp
TMPWORKDIR ?= $(TMPDIR)/enc_ds_test
MMDC       ?= $(TMPWORKDIR)/bin/mmdc
TESTPREFIX ?= $(TMPWORKDIR)/var/run/top

.PHONY: clean_test_env clean_graphs python_module_test test_env test0 test1 clean_test_out

all: README.rst sdist bdist_wheel

README.rst: README.md
	pandoc --from markdown --to rst $^ -o $@

clean: 
	rm -rf src/enc_ds.egg-info dist/* build/* *~ test/*~ src/enc_ds/*~ src/enc_ds/__pycache__ src/enc_ds/share/data/*~

distclean: clean clean_test_env clean_test_out 
	rm -rf enc_ds.egg-info dist build README.rst

sdist: README.rst
	$(PYTHON) setup.py $@

bdist_wheel: README.rst
	$(PYTHON) setup.py $@

test_upload: sdist bdist_wheel
	twine upload --verbose --repository pypitest dist/*

upload: sdist bdist_wheel
	twine upload --verbose dist/*

graphs: src/enc_ds/share/data/cipher_diagram_0.png src/enc_ds/share/data/cipher_diagram_1.png

clean_graphs:
	rm -f src/enc_ds/share/data/cipher_diagram_0.png src/enc_ds/share/data/cipher_diagram_1.png

%.png: %.mmd $(MMDC)
	$(MMDC) -w 1024 -H 768 -i $< -o $@

test_env: $(TMPWORKDIR) $(TMPWORKDIR)/bin/mmdc python_module_test

$(TMPWORKDIR):
	@echo $(TMPWORKDIR)
	mkdir -p $(TMPWORKDIR)/{bin,lib/python/site-package,lib/node}

$(TMPWORKDIR)/bin/mmdc: $(TMPWORKDIR)
	(cd $(TMPWORKDIR)/lib/node && \
      $(NPM) install @mermaid-js/mermaid-cli && \
      cd $(TMPWORKDIR)/bin && \
      ln -s $(TMPWORKDIR)/lib/node/node_modules/.bin/mmdc )

python_module_test:
	$(PIP) install -t $(TMPWORKDIR)/lib/python/site-package \
      paramiko pkgstruct sshkeyring argparse_extd pyyaml

clean_test_env: 
	@echo rm -rf $(TMPWORKDIR)
	if [ -d $(TMPWORKDIR) ]; then { echo rm -rf $(TMPWORKDIR) ; rm -rf $(TMPWORKDIR) ; } fi

TEST0_OUT = $(TESTPREFIX)/var/run/enc-ds/data/testdata.yaml \
            $(TESTPREFIX)/var/run/enc-ds/data/testdata.json \
            $(TESTPREFIX)/var/run/enc-ds/data/testdata.ini \
            $(TESTPREFIX)/var/run/enc-ds/data/testdata.toml

TEST1_OUT = $(TESTPREFIX)/var/run/enc-ds/config/TestEncipherdDataStorage.config.toml \
            $(TESTPREFIX)/var/run/enc-ds/config/TestEncipherdDataStorage.config.ini \
            $(TESTPREFIX)/var/run/enc-ds/config/TestEncipherdDataStorage.config.json \
            $(TESTPREFIX)/var/run/enc-ds/config/TestEncipherdDataStorage.config.yaml 

$(TEST0_OUT): ./test/enc_ds_test0.sh
	$<

$(TEST1_OUT): ./test/enc_ds_test1.sh
	$<

test0: $(TEST0_OUT)

test1: $(TEST1_OUT)

clean_test_out:
	rm -f $(TEST0_OUT) $(TEST1_OUT)
