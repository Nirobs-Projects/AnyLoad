import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error

class TagEditor:
    @staticmethod
    def inject_metadata(file_path, title, artist="AnyLoad Downloader", thumb_path=None):
        """অডিও ফাইলে মেটাডাটা এবং থাম্বনেইল যুক্ত করার ফাংশন"""
        if not file_path.endswith('.mp3'):
            return
            
        try:
            audio = MP3(file_path, ID3=ID3)
            
            # যদি ID3 ট্যাগ না থাকে তবে তৈরি করা
            try:
                audio.add_tags()
            except error:
                pass
            
            # টাইটেল এবং আর্টিস্ট সেট করা
            audio.tags.add(TIT2(encoding=3, text=title))
            audio.tags.add(TPE1(encoding=3, text=artist))
            
            # থাম্বনেইল ছবি যুক্ত করা
            if thumb_path and os.path.exists(thumb_path):
                with open(thumb_path, 'rb') as img:
                    audio.tags.add(
                        APIC(
                            encoding=3,
                            mime='image/jpeg',
                            type=3,
                            desc=u'Cover',
                            data=img.read()
                        )
                    )
            
            audio.save()
            print(f"[*] Metadata injected into: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"[!] Metadata Error: {e}")