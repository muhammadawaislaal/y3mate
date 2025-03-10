from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import logging

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set FFmpeg path correctly
FFMPEG_PATH = r"E:\y3mate\ffmpeg\bin\ffmpeg.exe"  # Ensure this path is correct
if not os.path.exists(FFMPEG_PATH):
    logging.error("FFmpeg path is incorrect! Please update the path.")

# Create downloads folder
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def fetch_video_info(url):
    """
    Fetch metadata for a given video URL.
    """
    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "socket_timeout": 10,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Video"),
                "thumbnail": info.get("thumbnail", ""),
            }
    except Exception as e:
        logging.error(f"Error fetching video info: {e}")
        return {"error": "Failed to retrieve video info. Please check the URL."}

@app.route('/video_info', methods=['POST'])
def video_info():
    """
    API route to fetch video metadata.
    """
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        video_data = fetch_video_info(url)
        return jsonify(video_data)
    except Exception as e:
        logging.error(f"Error in /video_info: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/download', methods=['POST'])
def download():
    """
    API route to download a video in the selected format.
    """
    try:
        data = request.json
        url = data.get('url')
        format_type = data.get('format')
        
        if not url or not format_type:
            return jsonify({"error": "Missing URL or format selection"}), 400
        
        # yt-dlp download options
        ydl_opts = {
            "ffmpeg_location": FFMPEG_PATH,
            "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s"),
        }

        if format_type == "mp3":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }]
        else:
            ydl_opts["format"] = "bestvideo+bestaudio/best"  # Proper merging
            ydl_opts["merge_output_format"] = "mp4"  # Ensures MP4 format

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            if format_type == "mp3":
                file_path = file_path.rsplit(".", 1)[0] + ".mp3"

        # Ensure file exists before sending
        if not os.path.exists(file_path):
            logging.error(f"Download failed: {file_path} not found")
            return jsonify({"error": "Download failed. Please try again."}), 500

        return send_file(file_path, as_attachment=True)
    
    except yt_dlp.DownloadError as e:
        logging.error(f"Download error: {e}")
        return jsonify({"error": "Video download failed. URL may be invalid or restricted."}), 400
    
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=True)
