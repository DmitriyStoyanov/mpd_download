import os
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import sys
import time

def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}

    adaptation_sets = []
    for adaptation_set in root.findall('.//mpd:AdaptationSet', ns):
        mime_type = adaptation_set.get('mimeType')
        adaptation_sets.append((mime_type, adaptation_set))

    return adaptation_sets

def list_representations(adaptation_set):
    ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}

    representations = []
    for representation in adaptation_set.findall('./mpd:Representation', ns):
        rep_id = representation.get('id')
        bandwidth = representation.get('bandwidth')
        width = representation.get('width')
        height = representation.get('height')

        representation_info = {
            'id': rep_id,
            'bandwidth': bandwidth,
            'width': width,
            'height': height,
        }
        representations.append(representation_info)

    return representations

def download_file(url, retries=5, delay=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, allow_redirects=True)
            if response.status_code == 200:
                return response.content
            else:
                print(f'Attempt {attempt + 1}: Failed to download: {url} (Status code: {response.status_code})')
        except Exception as e:
            print(f'Attempt {attempt + 1}: Exception occurred while downloading {url}: {e}')
        
        time.sleep(delay)

    print(f'Failed to download after {retries} attempts: {url}')
    return None

def download_files(base_url, segment_media_list, output_file):
    with open(output_file, 'wb') as out_file:
        if segment_media_list:
            try:
                for media in segment_media_list:
                    file_url = urljoin(base_url, media)
                    content = download_file(file_url)
                    if content:
                        out_file.write(content)
                        print(f'Downloaded and concatenated: {file_url}')
                    else:
                        raise Exception(f'Failed to download segment: {file_url}')
            except Exception as e:
                print(f'Regular download failed: {e}')
                print('Attempting fallback to yt-dlp...')
                out_file.close()
                temp_incomplete = f"{output_file}.tmp"
                if os.path.exists(output_file):
                    os.rename(output_file, temp_incomplete)
                try:
                    import yt_dlp
                    ydl_opts = {
                        'format': 'best',
                        'outtmpl': output_file,
                        'retries': 5,  # Number of retries for each segment
                        'fragment_retries': 5,  # Number of retries for each fragment
                        'retry_sleep': 5,  # Time to sleep between retries in seconds
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([base_url])
                    print(f'Successfully downloaded using yt-dlp: {base_url}')
                    if os.path.exists(temp_incomplete):
                        os.remove(temp_incomplete)
                    return
                except Exception as ydl_error:
                    print(f'yt-dlp fallback also failed: {ydl_error}')
                    if os.path.exists(temp_incomplete):
                        if os.path.exists(output_file):
                            os.remove(output_file)
                        os.rename(temp_incomplete, output_file)
                    return
        else:
            # If no segments, try base URL directly
            content = download_file(base_url)
            if content:
                out_file.write(content)
                print(f'Downloaded and concatenated: {base_url}')
            else:
                out_file.close()
                temp_incomplete = f"{output_file}.tmp"
                if os.path.exists(output_file):
                    os.rename(output_file, temp_incomplete)
                print('Attempting fallback to yt-dlp...')
                try:
                    import yt_dlp
                    ydl_opts = {
                        'format': 'best',
                        'outtmpl': output_file,
                        'retries': 5,  # Number of retries for each segment
                        'fragment_retries': 5,  # Number of retries for each fragment
                        'retry_sleep': 5,  # Time to sleep between retries in seconds
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([base_url])
                    print(f'Successfully downloaded using yt-dlp: {base_url}')
                    if os.path.exists(temp_incomplete):
                        os.remove(temp_incomplete)
                except Exception as ydl_error:
                    print(f'yt-dlp fallback also failed: {ydl_error}')
                    if os.path.exists(temp_incomplete):
                        if os.path.exists(output_file):
                            os.remove(output_file)
                        os.rename(temp_incomplete, output_file)

def get_best_video_representation(adaptation_set):
    representations = list_representations(adaptation_set)
    # Filter out representations that don't have segments or a valid BaseURL
    valid_reps = []
    ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
    for rep in representations:
        rep_elem = adaptation_set.find(f'./mpd:Representation[@id="{rep["id"]}"]', ns)
        has_segments = rep_elem is not None and rep_elem.find('./mpd:SegmentList/mpd:SegmentURL', ns) is not None
        has_baseurl = rep_elem is not None and rep_elem.find('./mpd:BaseURL', ns) is not None
        if has_segments or has_baseurl:
            valid_reps.append(rep)
    if not valid_reps:
        raise Exception("No valid video representations with segments or BaseURL found.")
    # Prefer highest height, then width, then bandwidth
    return max(
        valid_reps,
        key=lambda x: (
            int(x['height'] or 0),
            int(x['width'] or 0),
            int(x['bandwidth'] or 0)
        )
    )

def get_audio_representation(adaptation_set):
    representations = list_representations(adaptation_set)
    return representations[0]  # Usually there's only one audio stream

def combine_streams(video_file, audio_file, output_file):
    import subprocess
    try:
        cmd = ['ffmpeg', '-i', audio_file, '-i', video_file, '-c', 'copy', output_file]
        subprocess.run(cmd, check=True)
        print(f"Successfully combined streams into: {output_file}")
        # Clean up temporary files
        os.remove(video_file)
        os.remove(audio_file)
    except subprocess.CalledProcessError as e:
        print(f"Error combining streams: {e}")
    except Exception as e:
        print(f"Error: {e}")

def main(xml_file):
    adaptation_sets = parse_xml(xml_file)

    # Find video and audio adaptation sets
    video_set = None
    audio_set = None
    for mime_type, adaptation_set in adaptation_sets:
        if mime_type.startswith('video/'):
            video_set = adaptation_set
        elif mime_type.startswith('audio/'):
            audio_set = adaptation_set

    if video_set is None or audio_set is None:
        print("Error: Could not find both video and audio streams")
        return

    # Get best quality video and audio representations
    video_rep = get_best_video_representation(video_set)
    audio_rep = get_audio_representation(audio_set)

    ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}

    # Download video stream
    video_rep_elem = video_set.find(f'./mpd:Representation[@id="{video_rep["id"]}"]', ns)
    video_base_url = video_rep_elem.find('./mpd:BaseURL', ns).text.strip()
    video_segments = []
    seen_media = set()
    for segment in video_set.findall(f'./mpd:Representation[@id="{video_rep["id"]}"]/mpd:SegmentList/mpd:SegmentURL', ns):
        segment_media = segment.get('media')
        if segment_media and segment_media not in seen_media:
            video_segments.append(segment_media)
            seen_media.add(segment_media)

    # Download audio stream
    audio_rep_elem = audio_set.find(f'./mpd:Representation[@id="{audio_rep["id"]}"]', ns)
    audio_base_url = audio_rep_elem.find('./mpd:BaseURL', ns).text.strip()
    audio_segments = []
    seen_media = set()
    for segment in audio_set.findall(f'./mpd:Representation[@id="{audio_rep["id"]}"]/mpd:SegmentList/mpd:SegmentURL', ns):
        segment_media = segment.get('media')
        if segment_media and segment_media not in seen_media:
            audio_segments.append(segment_media)
            seen_media.add(segment_media)

    # Download streams
    temp_video_file = 'temp_video.mp4'
    temp_audio_file = 'temp_audio.mp4'

    print("Downloading video stream...")
    download_files(video_base_url, video_segments, temp_video_file)
    print("Downloading audio stream...")
    download_files(audio_base_url, audio_segments, temp_audio_file)

    # Combine streams
    output_file = 'output.mp4'
    print("Combining streams...")
    combine_streams(temp_video_file, temp_audio_file, output_file)

    print(f'Final combined file created: {output_file}')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python download.py <path to XML file>")
        sys.exit(1)

    xml_file = sys.argv[1]
    main(xml_file)
