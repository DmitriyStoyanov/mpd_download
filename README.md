# mpd_download
Download video/audio from master.mpd files.

Usually when some webinar in progress, if it is already recorded we can download them.

# Prepare environment

If you use macos you can install python3 and ffmpeg using brew
```shell
brew install python3 ffmpeg
```

# Prepare python environment

```shell
python3 -m venv venv
source venv/bin/activate
python3 -m pip install requests
```

# Download video or audio

```shell
python3 download.py master.mpd
```

Then you will choose video or audio file
After selecting all available streams will be shown for selection. For example you have 480p, 720p and 1080p video streams

After that it will download all parts (if there will be several parts) and concatenate them in one file

Then you can combine audio and video files using ffmpeg

```shell
ffmpeg -i audio.mp4 -i video.mp4 -c copy output.mp4
```

Thats it, you have output.mp4 file which contain video+audio tracks
