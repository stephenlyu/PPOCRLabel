# ex: set ts=8 noet:

all: qt5 uic test

test: testpy3

testpy2:
	python -m unittest discover tests

testpy3:
	python3 -m unittest discover tests

qt4: qt4py2

qt5: qt5py3

qt4py2:
	pyrcc4 -py2 -o libs/resources.py resources.qrc

qt4py3:
	pyrcc4 -py3 -o libs/resources.py resources.qrc

qt5py3:
	pyrcc5 -o libs/resources.py resources.qrc

UI_DIR=libs/ui
UI_FILES := $(wildcard $(UI_DIR)/*.ui)
PY_FILES = $(patsubst $(UI_DIR)/%.ui, $(UI_DIR)/%.py, $(UI_FILES))

$(UI_DIR)/%.py: $(UI_DIR)/%.ui
	pyuic5 $< -o $@

uic: $(PY_FILES)

clean:
	rm -rf ~/.labelImgSettings.pkl *.pyc dist labelImg.egg-info __pycache__ build libs/ui/*.py

pip_upload:
	python3 setup.py upload

long_description:
	restview --long-description

.PHONY: all
