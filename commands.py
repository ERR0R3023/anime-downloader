#!/usr/bin/env python
import os
import re
import sys

import subprocess
import time
import html2text

import config
import gogoanime
import utils


def anime_log(args):
    print('Watched:\tAnime Name:')
    logs = utils.read_log().items()
    if len(args) == 1:
        logs = filter(lambda kv: re.match(args[0], kv[0]), logs)
    for k, v in logs:
        print(f'{v}\t\t{k}')


def play_anime(args):
    name, episodes = read_args(args)
    for e in episodes:
        url = gogoanime.get_episode_url(name, e)
        gogoanime.stream_from_url(url, name, e)


def update_log(args):
    anime_name, episodes = read_args(args)
    utils.write_log(anime_name, utils.compress_range(episodes))


def continue_play(args):
    name, episodes = read_args(args)
    watched = utils.read_log().get(name)
    print(f'Watched: {watched}')
    if not watched:
        last = 0
    else:
        last = int(watched.split('-')[-1])
    play_anime(
        [name,
         utils.compress_range(filter(lambda e: e > last, episodes))])


def download_anime(args):
    name, episodes = read_args(args)
    for e in episodes:
        url = gogoanime.get_episode_url(name, e)
        gogoanime.download_from_url(url, name, e)


def check_anime(args):
    name, episodes = read_args(args)
    unavail_eps = []
    for e in episodes:
        url = gogoanime.get_episode_url(name, e)
        print('Testing:', url)
        durl, ext = gogoanime.get_direct_video_url(url)
        if not durl:
            raise SystemExit('Url for the file not found')
        if not os.path.exists(
                os.path.join(config.anime_dir, f'./{name}/ep{e:02d}.{ext}')):
            unavail_eps.append(e)
    if len(unavail_eps) == 0:
        print('All episodes in given range are locally available')
    else:
        print(f'Missing episodes: {utils.compress_range(unavail_eps)}')


def read_args(args, episodes=True):
    if len(args) == 0:
        name = utils.read_cache()
    elif args[0].isnumeric():
        name = utils.read_cache(int(args[0]))
        print(name)
    elif '/' in args[0]:
        name = args[0].strip('/').split('/')[-1]
    else:
        name = gogoanime.process_anime_name(args[0])
        if not os.path.exists(os.path.join(
                config.anime_dir, f'./{name}')) and not utils.get_soup(
                    gogoanime.get_anime_url(name)):
            print(
                f'Anime with name doesn\'t exist: {" ".join(name.split("-"))}')
            raise SystemExit

    if not name:
        print('Numbers choice invalid, or invalid context.')
        raise SystemExit
    os.makedirs(os.path.join(config.anime_dir, f'./{name}'), exist_ok=True)

    if not episodes:
        return name
    if len(args) <= 1:
        print('Episodes range not given defaulting to all')
        available_rng = gogoanime.get_episodes_range(
            gogoanime.get_anime_url(name))
        print(f'Available episodes: {available_rng}')
        episodes = utils.extract_range(available_rng)
    elif len(args) == 2:
        episodes = utils.extract_range(args[1])
    else:
        print('Too many arguments.\n')
        print(__doc__)
        raise SystemExit
    return name, episodes


def list_episodes(args):
    name, episodes = read_args(args)
    if len(sys.argv) == 4:
        eps = set(episodes)
        avl_eps = set(
            utils.extract_range(
                gogoanime.get_episodes_range(gogoanime.get_anime_url(name))))
        res = eps.intersection(avl_eps)
        result = utils.compress_range(res)
        print(f'Available episodes: {result}')
    print(f'Watched episodes: {utils.read_log(name)}')
    utils.write_cache(name)


def search_anime(args):
    name = " ".join(args)
    url = config.search_t.substitute(name=name)
    soup = utils.get_soup(url)
    plist = soup.find('ul', {'class': 'pagination-list'})
    utils.clear_cache()

    def search_results(s):
        all_res = s.find('ul', {'class': 'items'})
        for list_item in all_res.find_all('li'):
            an = list_item.p.a['href'].split('/')[-1]
            utils.write_cache(an, append=True)
            print(an, end='  \t')
            print(list_item.p.a.text)

    search_results(soup)
    if plist:
        for list_item in plist.find_all('li', {'class': None}):
            url = config.search_page_t.substitute(name=name,
                                                  page=list_item.a.text)
            soup = utils.get_soup(url)
            search_results(soup)


def anime_info(args):
    name = read_args(args, episodes=False)
    soup = utils.get_soup(gogoanime.get_anime_url(name))
    info = soup.find('div', {'class': 'anime_info_body'})
    h = html2text.HTML2Text()
    h.ignore_links = True
    for t in info.find_all('p', {'class': 'type'}):
        print(h.handle(t.decode_contents()), end="")


def download_from_url(gogo_url, anime_name=None, episode=None):
    if not anime_name or not episode:
        anime_name, episode = gogoanime.parse_gogo_url(gogo_url)
    print('Downloading:', gogo_url)
    durl, ext = gogoanime.get_direct_video_url(gogo_url)
    if not durl:
        raise SystemExit('Url for the file not found')
    if ext == 'm3u8':
        print("m3u8 file found")
        m3u8_url = utils.get_m3u8_stream(durl)
        utils.download_m3u8(
            m3u8_url,
            os.path.join(config.anime_dir,
                         f'./{anime_name}/ep{episode:02d}.{ext}'))
    else:
        utils.download_file(
            durl,
            os.path.join(config.anime_dir,
                         f'./{anime_name}/ep{episode:02d}.{ext}'))


def stream_from_url(url, anime_name=None, episode=None):
    if not anime_name or not episode:
        anime_name, episode = gogoanime.parse_gogo_url(url)
    print('Getting Streaming Link:', url)
    durl, ext = gogoanime.get_direct_video_url(url)
    if not durl:
        raise SystemExit('Url for the file not found')
    if ext == 'm3u8':
        print("m3u8 file found")
        durl = utils.get_m3u8_stream(durl)
    print(f'Stream link: {durl}')
    if input('Start mpv?<Y/n>:') == 'n':
        raise SystemExit
    t1 = time.time()
    subprocess.call(" ".join(config.ext_player_command + [durl]), shell=True)
    if (time.time() - t1) > (
            5 * 60
    ):  # 5 minutes watchtime at least, otherwise consider it unwatched
        utils.write_log(anime_name, episode)
        utils.write_cache(anime_name)
