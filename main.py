#!/usr/bin/env python

# Source https://coderunner.io/shrink-videos-with-ffmpeg-and-preserve-metadata/

import traceback
import os
import subprocess
import platform
# shutil is consisting of high-level Python specific functions. shutil is on top of Python `os module`.
# Thus, we can use the shutil module for high-level operations on files.
# For example: Use it to copy files and metadata
import shutil
import argparse

import pprint
import json


def preserve_file_dates(source_file, destination_file):
    """
    Preserve original FILE dates.
    """

    stat = os.stat(source_file)
    # Preserve access and modification date FILE attributes (EXIF are other dates)
    os.utime(destination_file, (stat.st_atime, stat.st_mtime))


def get_video_metadata(video_path):

    # run the ffprobe process, decode stdout into utf-8 & convert to JSON
    ffprobe_output = subprocess.check_output([FFPROBE_BIN, '-v', 'quiet',
                                              '-print_format', 'json',
                                              '-show_streams',
                                              video_path]).decode('utf-8')
    video_metadata = json.loads(ffprobe_output)

    # DEBUG - Prints all the metadata available:
    # pp = pprint.PrettyPrinter(indent=2)
    # pp.pprint(video_metadata)

    video_stream = next(
        (stream for stream in video_metadata['streams'] if stream['codec_type'] == 'video'), None)
    audio_stream = next(
        (stream for stream in video_metadata['streams'] if stream['codec_type'] == 'video'), None)

    return {'video': video_stream,
            'audio': audio_stream}


def reduce_video_using_h264(video_source_path, video_destination_path, pix_fmt, crf='23'):
    # "copy_unknown" -> "",           //if there are streams ffmpeg doesn't know about, still copy them (e.g some GoPro data stuff)
    # "map_metadata" -> "0",          //copy over the global metadata from the first (only) input
    # "map"          -> "0",          //copy *all* streams found in the file, not just the best audio and video as is the default (e.g. including data)
    # "codec"        -> "copy",       //for all streams, default to just copying as it with no transcoding
    # "preset"       -> "medium"      //fmpeg speed preset to use
    #
    # "codec:v" -> "libx264",         //specifically for the video stream, reencode to x264
    # "pix_fmt" -> "yuv420p",         //default pix_fmt
    # "crf"     -> "23"               //default constant rate factor for quality. 0-52 where 18 is near visually lossless
    #
    # "codec:a" -> "libfdk_aac",      //specifically for the audio stream, reencode to aac
    # "vbr"     -> "4"                //variable bit rate quality setting

    # Default CRF value
    crf = crf or '23'

    subprocess.call([FFMPEG_BIN, '-i', video_source_path,
                     '-copy_unknown',
                     '-map_metadata', '0',
                     '-map', '0',
                     '-map', '-0:d',
                     '-codec', 'copy',
                     '-codec:v', 'libx264',
                     '-pix_fmt', pix_fmt,
                     '-preset', 'slow',
                     '-crf', crf,  video_destination_path])

    # Preserve file dates that are not in the video metadata. Example: modification_time
    preserve_file_dates(source_file=video_source_path,
                        destination_file=video_destination_path)


def reduce_video_using_h265(video_source_path, video_destination_path, pix_fmt, crf='28'):

    # Default CRF value
    crf = crf or '28'

    subprocess.call([FFMPEG_BIN, '-i', video_source_path,
                     '-copy_unknown',
                     '-map_metadata', '0',
                     '-map', '0',
                     '-map', '-0:d',
                     '-codec', 'copy',
                     '-codec:v', 'libx265',
                     '-pix_fmt', pix_fmt,
                     '-preset', 'slow',
                     '-crf', crf,  video_destination_path])

    # Preserve file dates that are not in the video metadata. Example: modification_time
    preserve_file_dates(source_file=video_source_path,
                        destination_file=video_destination_path)


def reduce_video(source_folder, codec_output, destination_folder, failures_folder, other_codecs_folder, crf, entry):
    try:
        print(entry.name)

        video_source_path = f'{source_folder}/{entry.name}'
        video_destination_path = f'{destination_folder}/{entry.name}'

        video_metadata = get_video_metadata(video_source_path)
        pix_fmt = video_metadata['video']['pix_fmt']

        # Only process videos with these codecs (at this moment)
        if video_metadata['video']['codec_name'] in ['h264', 'hevc']:
            print(f"Video format detected: {video_metadata['video']['codec_name']}")


            # Use the same pix_fmt than the source video
            if codec_output == 'h264':
                reduce_video_using_h264(
                    video_source_path=video_source_path,
                    video_destination_path=video_destination_path,
                    pix_fmt=pix_fmt,
                    crf=crf
                )
            elif codec_output == 'h265':
                reduce_video_using_h265(
                    video_source_path=video_source_path,
                    video_destination_path=video_destination_path,
                    pix_fmt=pix_fmt,
                    crf=crf
                )
            else:
                raise Exception('Output codec not supported')

        else:
            print(f"Non supported video format detected: {video_metadata['video']['codec_name']}")

                        # Create folder if it does not exist
            if not os.path.exists(other_codecs_folder):
                os.makedirs(other_codecs_folder)

            video_other_codecs_path = f'{other_codecs_folder}/{entry.name}'
                        # Copy files with other video formats
            shutil.copy2(video_source_path, video_other_codecs_path)
    except Exception as exception:
                    # Create failures folder if it does not exist
        if not os.path.exists(failures_folder):
            os.makedirs(failures_folder)

        video_failure_path = f'{failures_folder}/{entry.name}'
                    # Copy files that have raised an exception to the failure folder
        shutil.copy2(video_source_path, video_failure_path)

                    # Show exception stack trace
        traceback.print_exc()


def crawl(source_folder, codec_output, destination_folder, failures_folder, other_codecs_folder, crf):
    with os.scandir(source_folder) as entries:
        for entry in entries:
            if entry.is_file():
                reduce_video(
                    source_folder,
                    codec_output,
                    destination_folder,
                    failures_folder,
                    other_codecs_folder,
                    crf,
                    entry
                )
            elif entry.is_dir() and entry.path != destination_folder:
                crawl(entry.path, codec_output, destination_folder, failures_folder, other_codecs_folder, crf)



if __name__ == '__main__':
    """
    Main operation of this script:
    1. NON-H.264 videos are copied to the other_codecs folder without being modified
    2. H.264 videos:
      2.1 Reduce video quality
        2.1.1 Use a fixed quality that the human eye can not detect
        2.1.2 Use H.264 or H.265 output code. If H.265 is used, 50 percent of the video is reduced maintaining the same quality
      2.2 Preserve FILE metadata (dates...)
    3. Invalid video files are copied to failures folder
    """

    # INPUT arguments
    ###
    parser = argparse.ArgumentParser(description='Compress Video files size')
    # Source folder is mandatory
    parser.add_argument('source_folder',
                        help='videos source folder')
    parser.add_argument('codec_output',
                        choices=['h264', 'h265'],
                        help='output codec to use')
    parser.add_argument('--destination_folder',
                        help='videos destination folder. Default is `source_folder/results`')
    parser.add_argument('--failures_folder',
                        help='videos destination folder. Default is `destination_folder/failures`')
    parser.add_argument('--crf',
                        type=str,
                        help='video crf between 0-51`. Default is 23 for h264 and 28 for h265')

    args = parser.parse_args()

    source_folder = args.source_folder
    codec_output = args.codec_output
    destination_folder = args.destination_folder or f'{source_folder}/results'
    failures_folder = args.failures_folder or f'{destination_folder}/failures'
    other_codecs_folder = f'{destination_folder}/other_codecs'
    # Because ffmpeg needs a str for CRF
    crf = args.crf
    #
    ###

    # Check that it is an allowed platform
    assert (platform.system().upper() in ['LINUX', 'WINDOWS']), 'OS not allowed'

    if platform.system().upper() == 'LINUX':
        FFMPEG_BIN = 'ffmpeg'
        FFPROBE_BIN = 'ffprobe'
    elif platform.system().upper() == 'WINDOWS':
        FFMPEG_BIN = 'ffmpeg.exe'
        FFPROBE_BIN = 'ffprobe.exe'

    # Destination folder. Create if does not exist
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # Process videos
    crawl(source_folder, codec_output, destination_folder, failures_folder, other_codecs_folder, crf)
