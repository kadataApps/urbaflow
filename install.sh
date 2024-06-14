#!/usr/bin/env bash

# for OS X, use python3 (otherwise, python2x is used)
# python3 -m venv virtual-env-kadata
 
# python -m venv virtual-env-kadata
# for Alwaysdata, use virtualenv directly
virtualenv venv-kadata

# activate venv
. venv-kadata/bin/activate

# install dependencies
pip install -r requirements.txt

# install certificates (see Readme) (only needed on OS X)
# sudo /Applications/Python\ 3.6/Install\ Certificates.command
deactivate