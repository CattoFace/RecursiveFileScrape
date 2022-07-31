python -m venv venv
venv\bin\activate.bat
pip install -r buildReqs.txt
python -m nuitka ../recursivescrape.py --onefile  --follow-stdlib -o recursivescrape.exe --assume-yes-for-downloads
