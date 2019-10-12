#!/bin/env python3
import sys
from pathlib import Path
import argparse
import logging
import requests
import lxml.etree
import os
from configparser import ConfigParser
from urllib.parse import urljoin

parser = argparse.ArgumentParser()
parser.add_argument('file', nargs='+')
parser.add_argument('-p', '--playlist', required=True)
parser.add_argument('-c', '--check-history', action='store_true')
parser.add_argument('-v', '--verbose', action='count', default=0)
parser.add_argument('-q', '--quiet', action='count', default=0)
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)
logger.addHandler(logging.StreamHandler(sys.stdout))

CONFIG_DIR = Path(os.getenv('XDG_CONFIG_HOME', os.getenv('HOME')+'/.config')) / Path('subsonic_utils')
CONFIG_FILE = CONFIG_DIR / Path('config.ini')
config = ConfigParser()
config.read(CONFIG_FILE)

for f in args.file:
    f = Path(f).resolve()
    logger.info(f)
    directories = str(f.relative_to(config['subsonic']['root_dir'])).split('/')
    logger.debug(directories)

    # 曲を取得する
    directory = directories.pop(0)
    logger.debug(directory)
    r = requests.get(urljoin(config['subsonic']['url'], "/rest/getMusicFolders.view"), params={"u": config['subsonic']['user'], "p": config['subsonic']['password'], "v": "1.0.0", "c": Path(__file__).name})
    logger.debug(r.text)
    folder_id = lxml.etree.fromstring(r.content).xpath(f"//ns:musicFolder[@name='{directory}']/@id", namespaces={'ns': 'http://subsonic.org/restapi'})[0]
    logger.debug(folder_id)

    logger.debug(directories[0])
    r = requests.get(urljoin(config['subsonic']['url'], "/rest/getIndexes.view"), params={"u": config['subsonic']['user'], "p": config['subsonic']['password'], "v": "1.0.0", "c": Path(__file__).name, "musicFolderId": folder_id})
    logger.debug(r.text)
    folder_id = lxml.etree.fromstring(r.content).xpath(f"//ns:artist[@name='{directories[0]}']/@id", namespaces={'ns': 'http://subsonic.org/restapi'})[0]
    logger.debug(folder_id)

    for directory in directories[1:-1]:
        logger.debug(directory)
        r = requests.get(urljoin(config['subsonic']['url'], "/rest/getMusicDirectory.view"), params={"u": config['subsonic']['user'], "p": config['subsonic']['password'], "v": "1.0.0", "c": Path(__file__).name, "id": folder_id})
        logger.debug(r.text)
        folder_id = lxml.etree.fromstring(r.content).xpath(f"//ns:child[@title='{directory}']/@id", namespaces={'ns': 'http://subsonic.org/restapi'})[0]
        logger.debug(folder_id)

    logger.debug('/'.join(directories))
    r = requests.get(urljoin(config['subsonic']['url'], "/rest/getMusicDirectory.view"), params={"u": config['subsonic']['user'], "p": config['subsonic']['password'], "v": "1.0.0", "c": Path(__file__).name, "id": folder_id})
    logger.debug(r.text)
    song_id = lxml.etree.fromstring(r.content).xpath(f"//ns:child[@path='{'/'.join(directories)}']/@id", namespaces={'ns': 'http://subsonic.org/restapi'})[0]
    logger.debug(f"song_id: {song_id}")


    # プレイリストを取得する
    r = requests.get(urljoin(config['subsonic']['url'], "/rest/getPlaylists.view"), params={"u": config['subsonic']['user'], "p": config['subsonic']['password'], "v": "1.0.0", "c": Path(__file__).name})
    logger.debug(r.text)
    playlist_id = lxml.etree.fromstring(r.content).xpath(f"//ns:playlist[@name='{args.playlist}']/@id", namespaces={'ns': 'http://subsonic.org/restapi'})[0]
    logger.debug(f"playlist_id: {playlist_id}")

    # 登録済みなら中止する
    r = requests.get(urljoin(config['subsonic']['url'], "/rest/getPlaylist.view"), params={"u": config['subsonic']['user'], "p": config['subsonic']['password'], "v": "1.0.0", "c": Path(__file__).name, "id": playlist_id})
    logger.debug(r.text)
    if lxml.etree.fromstring(r.content).xpath(f"//ns:entry[@id='{song_id}']", namespaces={'ns': 'http://subsonic.org/restapi'}):
        logger.info("Already registered.")
        continue

    # 過去に登録済みなら中止する
    history_file = CONFIG_DIR / Path(f'{Path(__file__).stem}_history_{args.playlist}')
    if args.check_history and history_file.exists():
        with history_file.open() as hf:
            if str(f) in hf.read().splitlines():
                logger.info("Already registered.")
                continue

    # 登録する
    r = requests.get(urljoin(config['subsonic']['url'], "/rest/updatePlaylist.view"), params={"u": config['subsonic']['user'], "p": config['subsonic']['password'], "v": "1.0.0", "c": Path(__file__).name, "playlistId": playlist_id, "songIdToAdd": song_id})
    logger.debug(r.text)

    # 履歴ファイルに追記する
    print(f, file=history_file.open('a'))
