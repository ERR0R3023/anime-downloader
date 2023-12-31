import os
import re
from urllib.parse import urljoin, urlparse
from string import Template

import subprocess

import utils
import outputs
import config


gogoanime_url = 'https://gogoanime.dk/'
new_page_url = urljoin(gogoanime_url, "new-season.html")

# ajax_t = Template('https://gogoplay.fi/encrypt-ajax.php?id=${id}')
episode_t = Template("${anime}-episode-${ep}")
anime_t = Template("category/${anime}")
resume_t = Template("Range: bytes=${size}-")
search_t = Template(gogoanime_url + "//search.html?keyword=${name}")
search_page_t = Template(
    gogoanime_url + "//search.html?keyword=${name}&page=${page}")

script_path = os.path.join(config.project_dir, 'sources/url-to-videos.sh')


def get_anime_url(anime_name):
    return urljoin(
        gogoanime_url,
        anime_t.substitute(anime=anime_name.lower().replace(' ', '-')))


def get_episode_url(anime_name, episode):
    return urljoin(
        gogoanime_url,
        episode_t.substitute(
            anime=anime_name.lower().replace(' ', '-'),
            ep=episode))


def process_anime_name(name):
    name = name.lower().replace(' ', '-')
    name = re.sub(r'\(|\)|:', '', name)
    return name


def get_episode_stream_url(url):
    soup = utils.get_soup(url)
    if not soup:
        outputs.error_info("The video doesn't exist.")
        raise SystemExit
    iframe = soup.find('iframe')
    if not iframe:
        outputs.error_info("The video doesn't exist.")
        raise SystemExit
    link = iframe['src']
    if not link.startswith('http'):
        link = 'https:' + link
    return link


def select_quality(urls):
    req_quality = f'{config.video_quality}p'
    for url in urls:
        if req_quality in url:
            break
    return url


def get_direct_video_url(gogo_url):
    url = get_episode_stream_url(gogo_url)

    # got this from ani-cli program since mine broke.
    process = subprocess.Popen(f'bash {script_path} {url}',
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    out, err = process.communicate()
    vids = out.decode().strip().split('\n')

    link = select_quality(vids)
    _, ext = os.path.splitext(urlparse(link).path)
    if ext == '.m3u8':
        link = utils.get_m3u8_stream(link)
    return link, ext


def get_episodes_range(anime_url):
    soup = utils.get_soup(anime_url)
    if not soup:
        return []
    rngs_obj = soup.find_all('a', ep_end=True, ep_start=True)
    total_rng = []
    for r in rngs_obj:
        rng = r.text
        rngs = rng.split('-')
        if rngs[0] == '0' and len(rngs) == 2:
            rngs[0] = '1'
        total_rng.append('-'.join(rngs))
    text = ','.join(total_rng)
    parsed_rng = utils.compress_range(utils.extract_range(text))
    return parsed_rng


def get_page(url=gogoanime_url):
    soup = utils.get_soup(url)
    div = soup.find('div', {'class': 'last_episodes'})
    eps = []
    for li in div.find_all('li'):
        try:
            link = li.find('a')['href']
            eps.append(parse_url(link))
        except SystemExit:
            continue
    return eps


def home_page():
    return get_page()


def new_page():
    return get_page(new_page_url)


def parse_url(url):
    whole_name = url.split('/')[-1]
    match = re.match(r'(.+)-episode-([0-9]+)', whole_name)
    if match:
        anime_name = match.group(1)
        episode = match.group(2)
    elif "category" in url:
        anime_name = whole_name
        episode = None
    else:
        outputs.error_info("URL couldn't be parsed.")
        raise SystemExit
    return anime_name, episode


def verify_anime_exists(anime_name, verbose=False):
    if utils.read_log(anime_name) is not None:
        if verbose:
            outputs.normal_info(anime_name, 'LOG', reverse=True)
        return True
    elif anime_name in utils.read_cache(complete=True):
        if verbose:
            outputs.normal_info(anime_name, 'CACHE', reverse=True)
        return True
    elif utils.get_anime_path(anime_name, check=True)[0]:
        if verbose:
            outputs.normal_info(anime_name, 'LOCAL', reverse=True)
        return True
    elif utils.get_soup(get_anime_url(anime_name)) is not None:
        if verbose:
            outputs.normal_info(anime_name, 'SITE', reverse=True)
        return True
    else:
        return False


def search_anime(keywords):
    url = search_t.substitute(name=keywords)
    soup = utils.get_soup(url)
    plist = soup.find("ul", {"class": "pagination-list"})
    utils.clear_cache()

    def search_results(s):
        all_res = s.find("ul", {"class": "items"})
        for list_item in all_res.find_all("li"):
            an = list_item.p.a["href"].split("/")[-1]
            utils.write_cache(an, append=True)
            outputs.normal_info(an, end="  \t")
            outputs.normal_info(list_item.p.a.text)

    search_results(soup)
    if plist:
        for list_item in plist.find_all("li", {"class": None}):
            url = search_page_t.substitute(name=keywords,
                                           page=list_item.a.text)
            soup = utils.get_soup(url)
            search_results(soup)
