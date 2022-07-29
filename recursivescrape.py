#!/usr/bin/env python3
"""Recursively downloads files from a webpage and links within that page."""

__author__ = "Barr Israel"
__version__ = "1"

import requests
import sys
import os
import argparse
from bs4 import BeautifulSoup
from tqdm import tqdm
import pickle
import json


def __save_progress(
    pending: dict, completed_dict: dict, completed_pages: int, fileName: str
):
    """saves current progress to a file"""
    with open(fileName, "wb") as f:
        pickle.dump(pending, f)
        pickle.dump(completed_dict, f)
        pickle.dump(completed_pages, f)


def scrape(
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
    verbosity: int = 0,
):
    pending = {}
    completed = {}
    if not download_path:
        download_path = os.getcwd()
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
    # restore progress if needed
    if resume:
        try:
            with open(args.progress_file, "rb") as f:
                pending = pickle.load(f)
                completed = pickle.load(f)
                pbar.n = pickle.load(f)
                pbar.total = pbar.n + len(pending)
        except FileNotFoundError:
            if verbosity >= 1:
                print(f"{progress_file} not found, starting from scratch")
            pending[root_url] = True
    else:
        pending[root_url] = True  # append to pending
    # main loop
    try:
        while pending:
            # inspect a page
            url = next(reversed(pending.keys()))  # LIFO order
            req = requests.get(url, cookies=cookies)
            pbar.set_description(prefix_start + url)
            if args.verbose >= 2:
                tqdm.write(f"scraping {url}")
            # set folder for the url
            folder_location = os.path.join(
                download_path, url.replace("https://", "").replace("http://", "")
            )
            # create folder if it doesn't exist
            if not os.path.exists(folder_location):
                os.makedirs(folder_location)
            entries = {}
            try:
                soup = BeautifulSoup(req.text, "html.parser")
                if args.id:
                    soup = soup.find(id=args.id)
                entries = soup.find_all("a")
            except Exception as e:
                if verbosity >= 1:
                    tqdm.write(f"error in url {url}")
            # inspect all entries in the page
            for entry in tqdm(
                entries,
                desc="Entries in page:",
                unit=" Entries",
                ncols=1,
                bar_format="{desc} {n_fmt}/{total_fmt}",
                leave=False,
            ):
                if verbosity >= 2:
                    tqdm.write(f'checking {entry["href"]}')
                if entry["href"][-1] != "/":  # if entry is file and not another page
                    try:
                        filename = os.path.join(
                            folder_location, entry["href"].split("/")[-1]
                        )
                    except Exception as e:
                        tqdm.write(e)
                        filename = os.path.join(folder_location, entry["href"])
                    if overwrite or not os.path.exists(filename):  # save file
                        if verbosity >= 2:
                            tqdm.write(f"downloading {entry.text}")
                        with open(filename, "wb") as f:
                            f.write(requests.get(entry["href"]).content)
                    elif verbosity >= 1:
                        tqdm.write(f"{entry.text} already exists, skipping.")
                elif not (
                    no_recursion
                    or url.startswith(entry["href"])
                    or "/./" in entry["href"]
                    or "/../" in entry["href"]
                    or entry["href"] in completed
                ):
                    pending[entry["href"]] = True  # add to pending
                    pbar.total += 1
                    if verbosity >= 2:
                        tqdm.write(f'added {entry["href"]} to pending stack')
            # finished page
            del pending[url]
            if not dont_prevent_loops:
                completed[url] = True  # add to completed
            pbar.update(1)

            # backup management
            backupCounter += 1
            if backup_interval and backupCounter == backup_interval:
                __save_progress(pending, completed, pbar.n, progress_file)
                if args.verbose >= 1:
                    tqdm.write("Saved backup to progress.dat")
                backupCounter = 0
        # download finished
        pbar.close()
        print("Download finished")
    except KeyboardInterrupt:
        pbar.close()
        if input("Save progress? [Y/n] ").lower() == "y":
            __save_progress(pending, completed, pbar.n, progress_file)
            print("Saved progress to file progress.dat")


if __name__ == "__main__":
    # argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-u", "--url", help="URL to start from.", required=True)
    parser.add_argument("-p", "--download-path", help="Directory to download files to. Will use the current directory otherwise.")
    parser.add_argument(
        "-c",
        "--cookies",
        help="Cookie values as needed in the json format.",
        default="{}",
    )
    parser.add_argument(
        "--id",
        help="Component id that contains the files and following paths, use "
        " to check the whole page, unrecommended.",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        help="Download and overwrite existing files. If not added, files that already exist will be skipped.",
        action="store_true",
    )

    parser.add_argument(
        "-r",
        "--resume",
        help="Resume previous progress from file PROGRESS_FILE, will ignore url and no-recursion arguments if file is found.",
        action="store_true",
    )
    parser.add_argument(
        "-bi",
        "--backup-interval",
        help="Saves the current progress every BACKUP_INTERVAL pages, 0 will disable automatic backup.",
        default=0,
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
    parser.add_argument(
        "-nr",
        "--no-recursion",
        help="Only download files from the given url and do not follow links recursively",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Increase output detail. use -vv for even more detail.",
        action="count",
        default=0,
    )
    # read args and call scrape function
    args = parser.parse_args()
    cookies = json.loads(args.cookies)
    if (
        args.id
        or input(
            "You have selected no component id, are you sure you want to scan the whole page? [Y/n] "
        ).lower
        == "y"
    ):
        scrape(
            args.url,
            download_path=args.download_path,
            cookies=cookies,
            id=args.id,
            overwrite=args.overwrite,
            resume=args.resume,
            progress_file=args.progress_file,
            dont_prevent_loops=args.dont_prevent_loops,
            no_recursion=args.no_recursion,
            backup_interval=args.backup_interval,
            verbosity=args.verbose,
        )
