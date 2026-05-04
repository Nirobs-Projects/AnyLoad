# -*- coding: utf-8 -*-


class AudioThumbnailEmbedder:
    @staticmethod
    def yt_dlp_audio_options():
        return {
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'embedthumbnail': True,
            'addmetadata': True,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                },
                {
                    'key': 'EmbedThumbnail',
                }
            ],
        }
