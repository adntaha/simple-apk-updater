import io
import sys
import json
import hashlib
import requests

from tqdm import tqdm
from github import Github
from pathlib import Path

git = Github(user_agent="ApkUpdaterByBotato/1.0")
apks = {}

if ('-v' in sys.argv) or ('--verbose' in sys.argv):
    verbose = True
else:
    verbose = False


def log(*msg):
    if verbose:
        print(*msg)


def load_apks():
    global apks
    with Path(__file__).parent.joinpath("apks.json").open("r") as f:
        apks = json.loads(f.read())


def fetch(name, url):
    res = requests.get(url, stream=True)
    name = Path(name)
    if name.exists():
        with name.open("rb") as cur_content:
            if check_if_version_same(cur_content, res.content):
                print(f"[!] {name} is already up to date")
                return (False, res)
    return (True, res)


def fetch_github(name, apk_fetch):
    GH_USER, GH_REPO = apk_fetch.replace('github:', '').split('/')
    assets = (
        git.get_user(GH_USER)
        .get_repo(GH_REPO)
        .get_latest_release()
        .get_assets()
    )
    for asset in assets:
        if '.apk' in asset.name:
            browser_download_url = asset.browser_download_url
            break
    res = fetch(name, browser_download_url)
    return res[1] if res[0] else False


def fetch_http(name, apk_fetch):
    res = fetch(name, apk_fetch)
    return res[1] if res[0] else False


def check_hash(file):
    """
    Credits to https://www.quickprogrammingtips.com/python/how-to-calculate-sha256-hash-of-a-file-in-python.html
    """
    sha256_hash = hashlib.sha256()
    if not isinstance(file, io.BufferedReader):
        file = io.BytesIO(file)
    with file as f:
        # Read and update hash string value in chunks of 4K
        for byte_chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_chunk)
    return sha256_hash.hexdigest()


def check_if_version_same(first_data, second_data):
    curr_apk = check_hash(first_data)
    log(f"Current hash: {curr_apk}")
    dwnld_apk = check_hash(second_data)
    log(f"Download hash: {dwnld_apk}")
    if curr_apk != dwnld_apk:
        print("[!] APK hashes mismatch, updating apk...")
        return False
    return True


def main():
    for apk_name, apk_fetch in apks.items():
        if apk_fetch.startswith("github:"):
            res = fetch_github(apk_name, apk_fetch)
        elif apk_fetch.startswith(("http://", "https://")):
            res = fetch_http(apk_name, apk_fetch)
        else:
            raise Exception(f"Invalid fetch type for {apk_name}")

        if res:
            with open(apk_name, "wb") as f:
                for chunk in tqdm(
                    res.iter_content(chunk_size=4096),
                    ascii=True,
                    desc=f"Updating {apk_name}",
                ):
                    if not chunk:
                        continue
                    f.write(chunk)
        else:
            continue


if __name__ == "__main__":
    load_apks()
    main()
