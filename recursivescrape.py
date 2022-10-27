#!/usr/bin/env python3
"""Recursively downloads files from a webpage and links within that page."""

__author__ = "Barr Israel"
__version__ = "2.1"

import enum
import sys
import os
import argparse
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm
import pickle
import json
from itertools import islice
import warnings
import aiofiles
import aiohttp
import asyncio

warnings.filterwarnings(
    "ignore", category=DeprecationWarning
)  # for aiohttp depracting creating a session without "with" and asyncio "there is no current event loop"


def __save_progress(
    pending: dict, completed_dict: dict, completed_pages: int, fileName: str
):
    """saves current progress to a file"""
    with open(fileName, "wb") as f:
        pickle.dump(pending, f)
        pickle.dump(completed_dict, f)
        pickle.dump(completed_pages, f)


async def __scrape_page(
    url: str,
    download_path: str,
    cookies: dict,
    id: str,
    overwrite: bool,
    progress_file: str,
    dont_prevent_loops: bool,
    no_recursion: bool,
    verbosity: int,
    pending: dict,
    completed: dict,
    session: aiohttp.ClientSession,
    pbar: tqdm,
):

    if args.verbose >= 2:
        tqdm.write(f"scraping {url}")
    # set and check file_path in order to not redownload files
    file_path = os.path.join(
        download_path, url.replace("https://", "").replace("http://", "")
    )
    if os.path.isfile(file_path) and not overwrite:
        if verbosity >= 1:
            tqdm.write(f"{file_path.split('/')[-1]} already exists, skipping")
    else:
        try:
            soup = None
            content = None
            async with session.get(url) as res:
                content = await res.read()
                soup = BeautifulSoup(content, features="lxml")
            if "text/html" in res.headers["content-type"]:  # url is webpage
                if not (
                    no_recursion and pbar.n >= 1
                ):  # if no recusion, only scrape one page
                    try:
                        if id:
                            soup = soup.find(id=id)
                        for entry in filter(
                            lambda url: not (
                                "/./" in url or "/../" in url or url in completed
                            ),
                            list(map(lambda a: a["href"], soup.find_all("a"))),
                        ):  # add all links in url to pending
                            pending[entry] = True
                            pbar.total += 1
                            if verbosity >= 2:
                                tqdm.write(f"added {entry} to pending")
                    except:
                        tqdm.write(f"Error parsing {url}")
                        return url
            else:  # url is a file
                folder_location = "/".join(file_path.split("/")[:-1])
                if not os.path.exists(
                    folder_location
                ):  # create folder if it doesn't exist
                    os.makedirs(folder_location)
                if verbosity >= 1:
                    tqdm.write(f"downloading {file_path.split('/')[-1]}")
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(content)
        except Exception as e:
            if verbosity >= 1:
                tqdm.write(f"error getting {url}, retrying:\n"+str(e))
            return None  # return None to mark no page finished
        # finished page
        if not dont_prevent_loops:
            completed[url] = True  # add to completed
    return url  # return url to tell the update loop which pages finished


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
    concurrent: int = 20,
):
    pending = {}
    completed = {}
    if not download_path:
        download_path = os.getcwd()
    print("Total pages count will increase as more pages are found")
    url = ""
    prefix_start = "Pages and files, current page: "
    backupCounter = 0
    pbar = tqdm(
        total=1,
        desc=prefix_start,
        unit=" Pages",
        ncols=1,
        bar_format="{desc} {n_fmt}/{total_fmt} [{rate_fmt}{postfix}]",
    )
    progress_path = os.path.join(download_path, progress_file)
    if resume:
        try:
            with open(progress_path, "rb") as f:
                pending = pickle.load(f)
                completed = pickle.load(f)
                pbar.n = pickle.load(f)
                pbar.total = pbar.n + len(pending)
        except FileNotFoundError:
            if verbosity >= 1:
                tqdm.write(f"{progress_file} not found, starting from scratch")
            pending[root_url] = True
    else:
        pending[root_url] = True  # append to pending
    try:
        # main loop
        loop = asyncio.get_event_loop()
        session = aiohttp.ClientSession(cookies=cookies)
        while pending:
            tasks = []
            # inspect a page
            for url in islice(reversed(pending.keys()), concurrent):
                # create url task and add to tasks
                pbar.set_description(
                    prefix_start + (".." + url[-80:] if len(url) >= 82 else url)
                )
                task = __scrape_page(
                    url,
                    download_path,
                    cookies,
                    id,
                    overwrite,
                    progress_file,
                    dont_prevent_loops,
                    no_recursion,
                    verbosity,
                    pending,
                    completed,
                    session,
                    pbar,
                )
                tasks.append(task)
            for url in loop.run_until_complete(
                asyncio.gather(*tasks)
            ):  # update finished tasks
                if url:  # on success
                    del pending[url]
                    backupCounter += 1
                    pbar.update(1)
            # backup management
            if backup_interval and backupCounter >= backup_interval:
                __save_progress(pending, completed, pbar.n, progress_path)
                if args.verbose >= 1:
                    tqdm.write("Saved backup to progress.dat")
                backupCounter = 0

        # download finished
        asyncio.run(session.close())
        pbar.close()
        print("Download finished")

    except KeyboardInterrupt:  # catching outside the function because KeyboardIntrrupt is not handled correctly inside tasks
        pbar.close()
        if input("Save progress? [Y/n] ").lower() != "n":
            __save_progress(pending, completed, pbar.n, progress_path)
            print("Saved progress to file progress.dat")


if __name__ == "__main__":
    # argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-u", "--url", help="URL to start from.", required=True)
    parser.add_argument(
        "-p",
        "--download-path",
        help="Directory to download files to. Will use the current directory by default.",
    )
    parser.add_argument(
        "-c",
        "--cookies",
        help='Cookie values as needed in the json format. Example: \'{"session":"12kmjyu72yberuykd57"}\'',
        default="{}",
    )
    parser.add_argument(
        "--id",
        help="Component id that contains the files and following paths. by default will check the whole page.",
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
        help="The file to save and load progress with, relative to the download path.",
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
    parser.add_argument(
        "--concurrent",
        help="How many pages to download concurrently at most",
        type=int,
        default=20,
    )
    # read args and call scrape function
    args = parser.parse_args()
    cookies = json.loads(args.cookies)
    if (
        args.id
        or input(
            "You have selected no component id, are you sure you want to scan the whole page? [Y/n] "
        ).lower()
        != "n"
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
            concurrent=args.concurrent,
        )
