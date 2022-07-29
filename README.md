# Recursive File Scraper

A Python script that recursively downloads files from a webpage and links within that page using a console or by importing the script.
Single page downloading and page component filter and other configurations are available.

## Setup

**Source:**

Python 3 is required to run the script.

Clone the repository, enter the directory and run the following line to install the script's dependencies:
```bash
pip install -r requirements.txt
```

**Binary:**

If a binary has been precompiled for your platform, it will be available in the releases section and no further steps are required.

Binaries are generated using Nuitka.

## Usage
**Command:**
Run the relevant file with any additional flags:
```bash
recursivescrape[.py/.exe/Linux64] [flags]
```
```bash
python ./recursivescrape.py [flags]
```

The available flags are:

|Flag|Description|Default|
|---|---|---|
|-h, --help|Show the help page of the program and all available flags||
|-u, --url|URL to start from. **REQUIRED**||
|-p, --download-path|Directory to download files to. Will use the current directory by default.||
|-c, --cookies| Cookie values as needed in the json format. Example: '{"session":"12kmjyu72yberuykd57"}'|"{}"|
|--id|Component id that contains the files and following paths. by default will check the whole page.||
|-o, --overwrite|Download and overwrite existing files. If not added, files that already exist will be skipped.|False|
|-r, --resume|Resume previous progress from file PROGRESS_FILE, will ignore url and no-recursion arguments if file is found.|False|
|-bi, --backup-interval|Saves the current progress every BACKUP_INTERVAL pages, 0 will disable automatic backup.|0|
|-f, --progress-file|The file to save and load progress with, relative to the download path.|progress.dat|
|-l, --dont-prevent-loops|Save memory by not remembering past pages but increase the chance of checking pages multiple times, do not add if there are any loops in the directory. Changing this flag between resumed runs results in undefined behaviour.|False|
|-nr, --no-recursion|Only download files from the given url and do not follow links recursively|False|
|-v, --verbose|Increase output detail. use -vv for even more detail.||

**Code:**
Place the script in the same folder as your file(or your python import path) and import it:
```python
import recursivescrape
```
Call the scrape function with the same flags that are available using the script, only root_url is strictly required:
```python
recursivescrape.scrape(
                root_url: str,
                download_path: str = None,
                cookies: dict = {},
                id: str = "",
                overwrite: bool = False,
                resume: bool = False,
                progress_file: str = "progress.dat",
                dont_prevent_loops: bool = True,
                no_recursion: bool = False,
                backup_interval: int = 0,
                verbosity: int = 0)
```

## To Do
- Allow method calling to download instead of standalone only. 
- Utilize async to parallel requests and speed up the process.  

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to test changes before sending a request.

## License
[MIT](https://choosealicense.com/licenses/mit/)
