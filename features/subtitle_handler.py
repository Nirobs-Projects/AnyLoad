# -*- coding: utf-8 -*-

class SubtitleHandler:
    @staticmethod
    def yt_dlp_options(mode):
        if "Bangla Sub" in mode:
            return {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['bn', 'en'], # বাংলা না পেলে ইংরেজি আনবে
                'subtitlesformat': 'srt/best', # vtt এর বদলে srt ব্যবহার করা হলো (সব প্লেয়ার সাপোর্ট করে)
                'merge_output_format': 'mkv',
                'postprocessors':[{'key': 'FFmpegEmbedSubtitle'}],
            }
        return {}