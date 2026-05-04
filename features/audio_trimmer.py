# -*- coding: utf-8 -*-
from utils.ffmpeg_tools import FFmpegTools


class AudioTrimmer:
    @staticmethod
    def trim(filepath, start, end, output_dir):
        return FFmpegTools.trim_audio(filepath, start, end, output_dir)
