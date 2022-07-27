import requests
import sys
import os
import argparse
from bs4 import BeautifulSoup
from tqdm import tqdm
import pickle
import json

# argparse
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    "-c",
    "--cookies",
    help="Cookie values as needed in the json format.",
    default="{}",
)
parser.add_argument("-u", "--url", help="URL to start from.", required=True)
parser.add_argument(
    "-o",
    "--overwrite",
    help="Download and overwrite existing files. If not added, files that already exist will be skipped.",
    action="store_true",
)
parser.add_argument(
    "-v", "--verbose", help="Increase output detail", action="store_true"
)
parser.add_argument(
    "-vv",
    "--veryverbose",
    help="Further increases output detail, overrides --verbose.",
    action="store_true",
)
parser.add_argument(
    "-r",
    "--resume",
    help="Resume previous progress from file PROGRESS_FILE, will ignore url argument if file is found.",
    action="store_true",
)
parser.add_argument(
    "--id",
    help="Component id that contains the files and following paths, on empty searches the whole page, unrecommended to leave empty.",
    default="",
)
parser.add_argument(
    "-bi",
    "--backup-interval",
    help="Saves the current progress every BACKUP_INTERVAL pages, 0 will disable automatic backup.",
    default=500,
    type=int,
)
parser.add_argument(
    "-f",
    "--progress-file",
    help="The file to save and load progress with.",
    default="progress.dat",
)
parser.add_argument(
    "-l",
    "--dont-prevent-loops",
    help="Save memory by not remembering past pages but increase the chance of checking pages multiple times, do not add if there are any loops in the directory. Changing this flag between resumed runs results in undefined behaviour.",
    action="store_true",
)


def save_progress(pending, completed_dict, completed_pages, fileName):
    """saves current progress to a file"""
    with open(fileName, "wb") as f:
        pickle.dump(pending, f)
        pickle.dump(completed_dict, f)
        pickle.dump(pbar.n, f)


if __name__ == "__main__":
    # setup
    args = parser.parse_args()
    pending = {}
    completed = {}
    dirname, src_filename = os.path.split(os.getcwd())
    print(src_filename)
    print("Total pages count will increase as more pages are found")
    url = ""
    prefix_start = "Pages, current page: "
    backupCounter = 0
    pbar = tqdm(
        total=1,
        desc=prefix_start,
        unit=" Pages",
        ncols=1,
        bar_format="{desc} {n_fmt}/{total_fmt}",
    )
    cookies = json.loads(args.cookies)

    # restore progress if needed
    if args.resume:
        try:
            with open(args.progress_file, "rb") as f:
                pending = pickle.load(f)
                completed = pickle.load(f)
                pbar.n = pickle.load(f)
                pbar.total = pbar.n + len(pending)
        except FileNotFoundError:
            print(f"{args.progress_file} not found, starting from scratch")
            pending[args.url] = True
    else:
        pending[args.url] = True  # append to pending

    # main loop
    try:
        while pending:
            # inspect a page
            url, _ = pending.popitem()  # pop entry, ignore value as it is irrelevant
            req = requests.get(url, cookies=cookies)
            pbar.set_description(prefix_start + url)
            if args.veryverbose:
                tqdm.write(f"scraping {url}")
            # create a folder for the url
            folder_location = url.replace("https://", "").replace("http://", "")
            # If there is no such folder, the script will create one automatically
            if not os.path.exists(folder_location):
                os.makedirs(folder_location)
            entries = {}
            try:
                soup = BeautifulSoup(req.text, "html.parser")
                if args.id:
                    soup = soup.find(id=args.id)
                entries = soup.find_all("a")
            except Exception as e:
                if args.verbose or args.veryverbose:
                    tqdm.write(f"error in url {url}")
            # inspect all entries in the page
            for entry in tqdm(
                entries, desc="Entries in page:", unit=" Entries", ncols=0, leave=False
            ):
                if args.veryverbose:
                    tqdm.write(f'checking {entry["href"]}')
                if entry["href"][-1] != "/":  # if entry is file and not another page
                    try:
                        filename = os.path.join(
                            folder_location, entry["href"].split("/")[-1]
                        )
                    except Exception as e:
                        tqdm.write(e)
                        filename = os.path.join(folder_location, entry["href"])
                    if args.overwrite or not os.path.exists(filename):  # save file
                        if args.verbose or args.veryverbose:
                            tqdm.write(f"downloading {entry.text}")
                        with open(filename, "wb") as f:
                            f.write(requests.get(entry["href"]).content)
                    elif args.verbose or args.veryverbose:
                        tqdm.write(f"{entry.text} already exists, skipping.")
                elif not (
                    url.startswith(entry["href"])
                    or "/./" in entry["href"]
                    or "/../" in entry["href"]
                    or entry["href"] in completed
                ):  # to prevent loops
                    pending[entry["href"]] = True  # add to pending
                    pbar.total += 1
                    if args.veryverbose:
                        tqdm.write(f'added {entry["href"]} to pending stack')
            if not args.dont_prevent_loops:
                completed[url] = True  # add to completed
            pbar.update(1)

            # backup management
            backupCounter += 1
            if args.backup_interval and backupCounter == args.backup_interval:
                save_progress(pending, completed, pbar.n, args.progress_file)
                if args.verbose or args.veryverbose:
                    tqdm.write("Saved backup to progress.dat")
                backupCounter = 0
        pbar.close()
        print("Download finished")
    except KeyboardInterrupt:
        pbar.close()
        if url:
            pending[url] = True  # redo last url incase it was partially done
        save_progress(pending, completed, pbar.n, args.progress_file)
        print("Saved progress to file progress.dat")
