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
python3 -m pip install requests yt-dlp
```

# Download video

```shell
python3 download.py master.mpd
```

The script will automatically:
1. Find the best quality video stream
2. Download the video stream
3. Download the audio stream
4. Combine them into a single output.mp4 file

The final video file will be saved as output.mp4 in the current directory.
