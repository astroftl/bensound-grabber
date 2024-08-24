import os
import re
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs
from urllib.parse import urlparse

import mutagen
import mutagen.id3
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

TAG_TYPES = {
    'Tags': 'tags',
    'Mood': 'mood',
    'Genre': 'genre',
    'Energy Level': 'energy',
    'Theme': 'theme',
    'Instrument': 'instrument',
    'Complexity/Density': 'complexity',
    'Building': 'building',
}


def apply_tags(meta, song_file):
    print(f'Applying tags to {song_file}')
    file = mutagen.File(song_file)
    try:
        file.add_tags()
    except mutagen.MutagenError:
        pass
    tags = file.tags

    tags.add(mutagen.id3.TIT2(text=meta['title']))
    tags.add(mutagen.id3.TPE1(text=meta['artist']))

    if 'genre' in meta:
        tags.add(mutagen.id3.TCON(text=meta['genre']))

    if 'tags' in meta:
        tags.add(mutagen.id3.TXXX(desc='Tags', text=meta['tags']))
    if 'mood' in meta:
        tags.add(mutagen.id3.TXXX(desc='Mood', text=meta['mood']))
    if 'energy' in meta:
        tags.add(mutagen.id3.TXXX(desc='Energy', text=meta['energy']))
    if 'theme' in meta:
        tags.add(mutagen.id3.TXXX(desc='Theme', text=meta['theme']))
    if 'instrument' in meta:
        tags.add(mutagen.id3.TXXX(desc='Instrument', text=meta['instrument']))
    if 'complexity' in meta:
        tags.add(mutagen.id3.TXXX(desc='Complexity', text=meta['complexity']))
    if 'building' in meta:
        tags.add(mutagen.id3.TXXX(desc='Building', text=meta['building']))

    # print(file)
    file.save()


class BensoundGrabber:
    def __init__(self, bensound_session, output_directory, bensound_url):
        self.output_directory = Path(output_directory)
        self.bensound_url = bensound_url

        self.licenses_path = self.output_directory / 'Licenses'
        self.sources_path = self.output_directory / 'Sources'
        self.tracks_path = self.output_directory / 'Tracks'
        if not self.licenses_path.exists():
            self.licenses_path.mkdir()
        if not self.sources_path.exists():
            self.sources_path.mkdir()
        if not self.tracks_path.exists():
            self.tracks_path.mkdir()

        self.session = requests.Session()
        self.cookies = {'PHPSESSID': bensound_session}
        response = self.session.get(bensound_url, cookies=self.cookies)
        self.soup = BeautifulSoup(response.text, 'html.parser')

        self.product_id = self.get_product_id()

    def grab(self):
        time.sleep(1)
        self.get_license_file(self.product_id)

        time.sleep(1)
        source_filename = self.get_source_file(self.product_id)

        tracks = self.extract_tracks(source_filename)

        meta = self.fetch_metadata()
        for track in tracks:
            apply_tags(meta, track)

    def get_product_id(self):
        music_download = self.soup.find(id='music-download')
        download_link = music_download['data-download-link']
        parsed_url = urlparse(download_link)
        product_id = parse_qs(parsed_url.query)['product_id'][0]
        print(f'Bensound product_id: {product_id}')
        return product_id

    def get_license_file(self, product_id):
        print('Grabbing license...')
        response = self.session.get(
            'https://www.bensound.com/index.php?route=licensee/certificate&product_id=' + product_id,
            cookies=self.cookies
        )
        d = response.headers['content-disposition'].encode("latin1").decode("utf-8")
        filename = re.findall(u'filename=\"(.+)\"', d)[0]
        with open(self.licenses_path / filename, 'wb') as f:
            f.write(response.content)
            print(f'Saved as: {f.name}')

    def get_source_file(self, product_id):
        print('Grabbing source archive...')
        response = self.session.get(
            'https://www.bensound.com/index.php?route=account/download/downloadTrackSubscription&product_id=' + product_id,
            cookies=self.cookies
        )
        d = response.headers['content-disposition'].encode("latin1").decode("utf-8")
        filename = re.findall(u'filename=\"(.+)\"', d)[0]
        with open(self.sources_path / filename, 'wb') as f:
            f.write(response.content)
            print(f'Saved as: {f.name}')
        return filename

    def extract_tracks(self, source_filename):
        extracted_tracks = []
        with zipfile.ZipFile(self.sources_path / source_filename, 'r', metadata_encoding='utf-8') as archive:
            infolist = archive.infolist()
            wavs_info = filter(find_wavs, infolist)
            for info in wavs_info:
                print(f'Extracting {info.filename}...')
                with archive.open(info) as archive_wav:
                    out_filename = info.filename.split('/')[-1]
                    with open(self.tracks_path / out_filename, 'wb') as f:
                        f.write(archive_wav.read())
                        print(f'Saved as: {f.name}')
                        extracted_tracks.append(f.name)
        return extracted_tracks

    def fetch_metadata(self):
        print(f'Fetching metadata from: {self.bensound_url}')

        meta = {'url': self.bensound_url}

        song_block = self.soup.find(id='song')
        tags_block = self.soup.find(id='tag-container')

        meta['title'] = song_block.find('h1').text.strip()
        meta['artist'] = song_block.find('a').text.strip()

        for block in tags_block.find_all(class_='tags'):
            tag_type = block.find('h3').text.strip()
            tags = []
            for tag in block.find_all(class_='tag'):
                tags.append(tag.text.strip())
            meta[TAG_TYPES[tag_type]] = tags

        # print(meta)

        return meta


def find_wavs(zipinfo):
    if zipinfo.is_dir():
        return False
    if zipinfo.filename.startswith('__'):
        return False
    if zipinfo.filename.endswith('.wav'):
        return True
    return False


def main():
    if len(sys.argv) != 2:
        print('Usage: main.py [bensound_url]')
        return

    load_dotenv()

    bensound_session = os.getenv('BENSOUND_SESSION')
    if bensound_session is None:
        print('Please provide your PHPSESSID as BENSOUND_SESSION in .env or your environment variables')
        return

    output_directory = os.getenv('BENSOUND_LOCATION')
    if output_directory is None:
        output_directory = ''

    bensound_url = sys.argv[1]

    grabber = BensoundGrabber(bensound_session, output_directory, bensound_url)
    grabber.grab()


if __name__ == '__main__':
    main()
