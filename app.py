import os
import re
import uuid
import threading
from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_cors import CORS
import yt_dlp
from moviepy.editor import AudioFileClip

app = Flask(__name__)
CORS(app) # Enable unrestricted access for testing. Restrict in production.

# Fix for Windows console encoding
import sys
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import imageio_ffmpeg

import shutil
import subprocess
import platform

# Config
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

def setup_ffmpeg():
    """Extracts/Copies ffmpeg binary to a local path for consistent use by yt-dlp."""
    try:
        src = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Determine executable name based on OS
        exe_name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
        local_ffmpeg = os.path.join(os.getcwd(), exe_name)
        
        # Only copy if it doesn't exist or size is different (simple check)
        if not os.path.exists(local_ffmpeg):
            print(f"Setting up local ffmpeg from {src}...")
            try:
                shutil.copy2(src, local_ffmpeg)
                # On Linux/Unix, ensure executable permissions
                if platform.system() != "Windows":
                    os.chmod(local_ffmpeg, 0o755)
            except Exception as copy_err:
                print(f"Copy failed ({copy_err}), using original source path")
                return src
            
        return local_ffmpeg
    except Exception as e:
        print(f"Failed to setup local ffmpeg: {e}")
        return imageio_ffmpeg.get_ffmpeg_exe() # Fallback

# Initialize FFMPEG path globally
FFMPEG_PATH = setup_ffmpeg()

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def process_video(video_url, output_format='mp3'):
    """Downloads video and converts to specified format."""
    try:
        temp_id = str(uuid.uuid4())
        
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'ffmpeg_location': FFMPEG_PATH
        }

        if output_format == 'mp4':
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'%(title)s.%(ext)s'),
            })
        else: # mp3
            ydl_opts.update({
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{temp_id}.%(ext)s'),
            })
        
        info_dict = None
        result_path = None
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            # For MP4, the filename is determined by the title in outtmpl
            if output_format == 'mp4':
                # Re-construct filename based on title
                sanitized_title = sanitize_filename(info_dict['title'])
                result_path = ydl.prepare_filename(info_dict)
                base, _ = os.path.splitext(result_path)
                final_mp4_path = base + '.mp4'
                
                # FIX: Re-encode audio to AAC to ensure compatibility on Windows
                # Some YT bestaudio are Opus, which breaks in mp4 container on some players
                temp_fixed_path = base + '_fixed.mp4'
                
                print(f"Fixing audio codec for {final_mp4_path}...")
                subprocess.run([
                    FFMPEG_PATH, '-y',
                    '-i', final_mp4_path,
                    '-c:v', 'copy', # Keep video stream as is (fast)
                    '-c:a', 'aac',  # Convert audio to AAC
                    '-b:a', '192k',
                    temp_fixed_path
                ], check=True)
                
                # Replace original with fixed
                if os.path.exists(temp_fixed_path):
                    os.replace(temp_fixed_path, final_mp4_path)

                return {"success": True, "filename": os.path.basename(final_mp4_path), "title": info_dict['title']}
            
            # For MP3 (existing flow)
            temp_file_path = ydl.prepare_filename(info_dict)
        
        if output_format == 'mp3':
            if not temp_file_path or not os.path.exists(temp_file_path):
                raise Exception("Download failed")

            # 2. Convert to MP3 using MoviePy
            title = sanitize_filename(info_dict.get('title', 'audio'))
            mp3_filename = f"{title}.mp3"
            mp3_path = os.path.join(DOWNLOAD_FOLDER, mp3_filename)
            
            # If file exists, append uuid to make unique
            if os.path.exists(mp3_path):
                mp3_filename = f"{title}_{temp_id[:8]}.mp3"
                mp3_path = os.path.join(DOWNLOAD_FOLDER, mp3_filename)

            print(f"Converting {temp_file_path} to {mp3_path}...")
            
            # Load and write
            audioclip = AudioFileClip(temp_file_path)
            audioclip.write_audiofile(mp3_path, logger=None)
            audioclip.close()
            
            # 3. Cleanup temp file
            try:
                os.remove(temp_file_path)
            except:
                pass
                
            return {"success": True, "filename": mp3_filename, "title": title}

    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    data = request.json
    url = data.get('url')
    fmt = data.get('format', 'mp3') # Default to mp3
    
    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400

    result = process_video(url, fmt)
    return jsonify(result)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
