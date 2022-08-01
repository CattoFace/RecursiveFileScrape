#1/bin/bash

python -m venv venv
source ./venv/bin/activate
pip install -r buildReqs.txt
pip install -r ../requirements.txt
python -m nuitka ../recursivescrape.py --onefile --linux-onefile-icon=python.xpm --follow-stdlib -o recursivescrapeLinux64 --assume-yes-for-downloads
deactivate
