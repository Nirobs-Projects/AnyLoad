import subprocess
import os

class FFmpegTools:
    @staticmethod
    def trim_audio(input_path, start_time, end_time, output_folder):
        """অডিও ফাইল নির্দিষ্ট সময় অনুযায়ী ট্রিম করার ফাংশন"""
        try:
            filename = os.path.basename(input_path)
            output_path = os.path.join(output_folder, f"Trimmed_{filename}")
            
            # FFmpeg Command: ffmpeg -ss [start] -to [end] -i input -c copy output
            command = [
                'ffmpeg', '-y', '-i', input_path,
                '-ss', str(start_time),
                '-to', str(end_time),
                '-c', 'copy', output_path
            ]
            
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_path
        except Exception as e:
            print(f"[!] FFmpeg Trimmer Error: {e}")
            return None