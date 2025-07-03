#!/usr/bin/env python
 
"""
List gopro files.

Check which files belong together and create ffconcat files to extract them.

"""
import re
import datetime
import sys
import argparse
import io

from pathlib import Path

def get_parsed_args():
    p = argparse.ArgumentParser(prog='GoPro')
    p.add_argument("src_dir" )
    p.add_argument("select_videos", nargs="*", type=int)
    p.add_argument("--output", "-o", help="Use the specified output")
    return p.parse_args()


def default_output(videos, stream):
    for video in videos:
        print(video, file=stream)


def ffconcat_output(videos, stream):
    print("ffconcat version 1.0", file=stream)
    for video in videos:
        for chapter in video.chapters:
            print(f"file {chapter.f}", file=stream)

def mpv_output(videos, stream):
    for video in videos:
        names = ' '.join([str(chapter.f) for chapter in video.chapters])
        print(f"mpv {names}", file=stream)


class VideoChapter:
    def __init__(self, ix, f, created, closed):
        self.f = f
        self.ix = ix
        self.birth = created
        self.modified = closed


class GoProVideo:
    def __init__(self, ix):
        self.birth = None
        self.modified  = None
        self.ix = ix
        self.chapters = []

    def add_chapter(self, chapter: VideoChapter):
        if not self.birth or chapter.birth < self.birth:
            self.birth = chapter.birth
        if not self.modified or chapter.modified < self.modified:
            self.modified = chapter.modified
        self.chapters = [*self.chapters, chapter]

    def __str__(self):
        s = io.StringIO()
        print(f"video: {self.ix}", file=s)
        for chapter in self.chapters:
            print(f"\t{chapter.f} {chapter.birth} {chapter.modified}", file=s)
        return s.getvalue()


def main(args):
    p = Path(args.src_dir)
    if not p.is_dir():
        print("src-dir must be a directory", file=sys.stderr)

    output = default_output
    available_outputs = {
        "ffconcat": ffconcat_output,
        "mpv": mpv_output,
    }
    if o := args.output:
        output = available_outputs[args.output]

    select_videos = args.select_videos or []
    videos = {}

    gopro_re = re.compile(r"G([A-Z]{1})(\d{2})(\d{4}).MP4")

    for f in p.iterdir():
        if f.suffix == ".MP4" and f.is_file():
            f_s = f.stat()
            # print(f_s.st_birthtime, f_s.st_mtime)

            m = gopro_re.match(f.name)
            if m:
                grps = m.groups()
                chapter_ix, video_ix = int(grps[1]), int(grps[2])
                
                if video_ix not in videos:
                    videos[video_ix] = GoProVideo(video_ix)
            
                videos[video_ix].add_chapter(VideoChapter(
                    chapter_ix,
                    f,
                    datetime.datetime.fromtimestamp(f_s.st_birthtime),
                    datetime.datetime.fromtimestamp(f_s.st_mtime))
                 )


    filtered_videos = []

    for video in sorted(videos.values(), key=lambda gpv: gpv.ix):
        if select_videos:
            if video.ix not in select_videos:
                continue
        filtered_videos.append(video)

    output(filtered_videos, sys.stdout)

if __name__ == "__main__":
    main(get_parsed_args())
