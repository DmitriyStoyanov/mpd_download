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
            for media in segment_media_list:  # Загружаем уникальные медиа файлы
                file_url = urljoin(base_url, media)
                content = download_file(file_url)
                if content:
                    out_file.write(content)
                    print(f'Downloaded and concatenated: {file_url}')
                else:
                    print(f'Unable to download the file: {file_url}. Stopping further downloads.')
                    return  # Прекращаем выполнение из-за ошибки
        else:
            # Если нет сегментов, загружаем файл по BaseURL
            content = download_file(base_url)
            if content:
                out_file.write(content)
                print(f'Downloaded and concatenated: {base_url}')
            else:
                print(f'Unable to download the base URL file: {base_url}')

def main(xml_file):
    adaptation_sets = parse_xml(xml_file)

    print("Список AdaptationSet:")
    for index, (mime_type, _) in enumerate(adaptation_sets):
        print(f"{index + 1}. MIME Type: {mime_type}")

    choice = int(input("Выберите номер AdaptationSet: ")) - 1
    chosen_mime_type, chosen_adaptation_set = adaptation_sets[choice]

    representations = list_representations(chosen_adaptation_set)
    print("Список Representation:")
    for index, rep in enumerate(representations):
        rep_info = f"{index + 1}. ID: {rep['id']}, Bandwidth: {rep['bandwidth']}"
        if rep.get('width') and rep.get('height'):
            rep_info += f", Width: {rep['width']}, Height: {rep['height']}"
        print(rep_info)

    rep_choice = int(input("Выберите номер Representation: ")) - 1
    chosen_rep = representations[rep_choice]

    base_url = chosen_adaptation_set.find('.//mpd:BaseURL', {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}).text.strip()

    segment_media_list = []  # Список для хранения уникальных значений media в порядке появления
    seen_media = set()  # Множество для отслеживания уже добавленных значений

    # Получение сегментов
    for segment in chosen_adaptation_set.findall('./mpd:Representation[@id="%s"]/mpd:SegmentList/mpd:SegmentURL' % chosen_rep['id'], {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}):
        segment_media = segment.get('media')
        if segment_media and segment_media not in seen_media:
            segment_media_list.append(segment_media)
            seen_media.add(segment_media)

    output_file = f"{chosen_rep['id']}.mp4"
    download_files(base_url, segment_media_list, output_file)

    print(f'Финальный объединенный файл создан: {output_file}')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Использование: python download_and_concatenate.py <путь к XML файлу>")
        sys.exit(1)

    xml_file = sys.argv[1]
    main(xml_file)
