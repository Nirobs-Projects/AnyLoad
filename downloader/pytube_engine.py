# -*- coding: utf-8 -*-
import os
import time

from utils.encoding_helper import sanitize_filename


class PytubeDownloader:
    def __init__(self, url, mode, base_path, progress_callback):
        self.url = url
        self.mode = mode
        self.base_path = base_path
        self.progress_callback = progress_callback
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            from pytube import YouTube
        except ImportError:
            return False, None, "pytube missing"

        retries = 3
        for attempt in range(1, retries + 1):
            if self.is_cancelled:
                return False, None, "Cancelled"
            try:
                yt = YouTube(self.url, on_progress_callback=self._pytube_hook)
                if "Audio" in self.mode:
                    stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                    save_path = os.path.join(self.base_path, "Audio")
                else:
                    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                    if not stream:
                        stream = yt.streams.filter(adaptive=True, file_extension='mp4').order_by('resolution').desc().first()
                    save_path = os.path.join(self.base_path, "Videos")

                if not stream:
                    raise Exception("No compatible stream found")
                os.makedirs(save_path, exist_ok=True)
                out_file = stream.download(output_path=save_path)
                if self.is_cancelled:
                    return False, None, "Cancelled"
                out_file = self._normalize_filepath(out_file)
                return True, out_file, None
            except Exception as exc:
                if self.is_cancelled:
                    return False, None, "Cancelled"
                message = str(exc)
                print(f"[pytube internal] {message}")
                if attempt == retries:
                    return False, None, message
                time.sleep(attempt)
                continue

        return False, None, "pytube failed"

    def _pytube_hook(self, stream, chunk, bytes_remaining):
        if self.is_cancelled:
            raise Exception("PAUSED")
        total = stream.filesize or 0
        percent = 0.0
        if total > 0:
            percent = ((total - bytes_remaining) / total) * 100
        self.progress_callback({
            'title': stream.default_filename if stream else 'Downloading...',
            'percent': f"{percent:.1f}%",
            'speed': 'N/A',
            'eta': 'N/A',
            'total': f"{total / (1024 * 1024):.1f}MB" if total else 'Unknown',
        })

    def _normalize_filepath(self, path):
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        filename = sanitize_filename(filename)
        if directory:
            os.makedirs(directory, exist_ok=True)
            return os.path.join(directory, filename)
        return filename
