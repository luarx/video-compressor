![Python 3.7](https://img.shields.io/badge/Python-3.7-blue.svg)

# VIDEO COMPRESSOR
Script to reduce the **size of video files** using FFMPEG.

Idea of this script:  https://coderunner.io/shrink-videos-with-ffmpeg-and-preserve-metadata/


Which input codecs are supported?
--------------------------------------
- **H.264 & H.265**:
  - **CRF** (Constant Rate Factor). Basically translates as *"try to keep this quality overall"*, and will use more or less bits at different parts of the video, depending on the content. (the **bitrate* is variable**).
  - **Output codec**. Possible options are **H.264** or **H.265** codecs. When using H.265 video is reduced half of its size maintaining the same video quality.
  - **Rest of video properties**. They are not modified.
- **Videos with different codecs**:
  - They are copied to another folder without being modified


How to use
------------
- Install **Python** (3.7 version recommended)
- [Optional] Configure virtualenv:
  - Install virtual env: `python3.7 -m venv venv`
  - Activate it: `source venv/bin/activate`
- Install **FFmpeg** and add it to system PATH
- Install **FFprobe** (*This is installed on ffmpeg installation by default*)
- Look at script options: `python main.py -h`
- Execute it: `python main.py [VIDEOS_FOLDER] [--ANOTHER_OPTIONS]`


TIPS
-----------
You can create an isolated Python environment to install required libraries with virtualenv:
  - Create a virtualenv: `python -m venv [VENV_FOLDER]`
  - Activate virtualenv: `source [VENV_FOLDER]/bin/activate`


F.A.Q
------------

### What about original video metadata?

Original video  metadata will be copied to the new modified video:
  - **Container metadata**. All the original container metadata is copied using ffmpeg `-map_metadata` option
  - **FILE dates**. Access and modification file dates.

### What happens if I have h.264 & h.265 videos and another videos which use different codecs in the same folder?

Non `h.264` or `h.265` videos will be copied to the destination_folder/other_codecs by default **without being modified**

### What happens if in the middle of the process there is a failure with one video?

That video will be copied to the `failures` folder so that you can analyze why later


More source information that helped to build this script
---------------------------------------------------

### History

#### Timeline video codecs
[![Timeline video codecs](/readme_images/codecs_history.jpg "Timeline video codecs")](https://www.slideshare.net/mohieddin.moradi/an-introduction-to-versatile-video-coding-vvc-for-uhd-hdr-and-360-video-135899487)
<br/>
[Source link](https://www.slideshare.net/mohieddin.moradi/an-introduction-to-versatile-video-coding-vvc-for-uhd-hdr-and-360-video-135899487)

[![MPEG and VCEG codecs history](/readme_images/mpeg_vceg_history.jpg "MPEG and VCEG codec history")](https://blog.wildix.com/understanding-video-codecs/)
<br/>
[Source link](https://blog.wildix.com/understanding-video-codecs/)


#### Bitrate reduction
![Bitrate reduction](/readme_images/bitrate_reduction.jpg "Bitrate reduction")

#### Comparison of video codecs and containers
http://download.das-werkstatt.com/pb/mthk/info/video/comparison_video_codecs_containers.html

#### ISO vs IEC vs ITU (the Big Three international standards organizations)

[![ISO, IEC and ITU organizations](/readme_images/big_three.JPG "ISO, IEC and ITU organizations")](https://slideplayer.com/slide/4687304/)
[Source link](https://slideplayer.com/slide/4687304/)


### Video Quality
  - Different methods to compare video quality after modifying videos
  https://superuser.com/questions/338725/compare-two-video-files-to-find-out-which-has-best-quality

  - Compare video quality with FFMPEG
  https://github.com/stoyanovgeorge/ffmpeg/wiki/How-to-Compare-Video


### H.264

#### Tips about H.264
https://trac.ffmpeg.org/wiki/Encode/H.264


#### Bits per frame war -> CRF (Constant Rate Factor) vs CBR (Constant Bitrate)
https://slhck.info/video/2017/02/24/crf-guide.html
https://slhck.info/video/2017/03/01/rate-control.html

### VFR (Variable Frame Rate) and CFR (Constant Frame Rate)

#### Know video VFR (Variable Frame Rate)
https://github.com/stoyanovgeorge/ffmpeg/wiki/Variable-Frame-Rate

Using ffmpeg: `ffmpeg -i [VIDEO] -vf vfrdet -f null -`

Result example:
```
[Parsed_vfrdet_0 @ 0x56518fa3f380] VFR:0.400005 (15185/22777) min: 1801 max: 3604)
```

**A non-zero value for VFR indicates a VFR stream**. The first value in brackets (15185) is the number of frames with a duration different than the expected duration implied by the detected frame rate of the stream. The 2nd value (22777) is number of frames having the expected duration. The VFR value (0.400005) is the ratio of the first number to the sum of both.

If there were frames with variable delta, than it will also show min and max delta encountered.


#### FFMPEG uses CFR (Constant Frame Rate) by default for MP4 output
https://trac.ffmpeg.org/wiki/ChangingFrameRate

### H.265

#### Tips about H.265
https://trac.ffmpeg.org/wiki/Encode/H.265
