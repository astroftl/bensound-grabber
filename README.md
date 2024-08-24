# Bensound Grabber
A simple Python script to grab the license file and song archive from Bensound, then extract any `.wav` files. These files then get additional metadata attached as custom IDv3 tags, as scraped from the Bensound song info page.

The license file will be placed in `Licenses/`, the source archive will be placed in `Sources/`, and the extracted songs will be placed in `Tracks/`

Create a venv and install the requirements listed in `requirements.txt`.

This script requires that the `BENSOUND_SESSION` environment variable be set, or loaded from a `.env` file. This variable must be your Bensound `PHPSESSID` cookie, which can be found by inspecting your cookies or requests in a browser while logged in to Bensound. 

By default, the 3 directories where files are output are created in the current directory. This can be overwritten by an optional `BENSOUND_LOCATION` location environment variable, in which case the 3 directories will be created there.

### Example `.env`
```dotenv
BENSOUND_SESSION=1234yourPHPSESSIDtoken5678
BENSOUND_LOCATION=D:\Music\Royalty Free
```

### Usage
Invoke the script with a single argument, the link to the track info page. Example using the first song on the list at time of writing:
```bash
python bengrab.py https://www.bensound.com/royalty-free-music/track/pulse-of-time-dark-electronic
```