from flask import Flask, render_template, request, redirect, url_for
import os
import subprocess

app = Flask(__name__)

# Path to store uploaded videos
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    # Get the uploaded video and stream key from the form
    video = request.files['video']
    stream_key = request.form['stream_key']

    if video and stream_key:
        # Save the uploaded video file
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video.filename).replace('\\', '/')
        video.save(video_path)

        # Stream the video to YouTube using the stream key
        youtube_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
        
        # Run ffmpeg command to stream to YouTube
        try:
            stream_to_youtube(video_path, youtube_url)
        except Exception as e:
            return f"Error streaming video: {e}"
        
        return "Video streaming to YouTube started!"
    else:
        return "Please upload a video and provide a stream key."

@app.route('/stop_tream', methods=['POST'])
def stop_stream():
    # Kill the ffmpeg process
    subprocess.run(['pkill', 'ffmpeg'], check=False)
    return "Video streaming stopped!"

def stream_to_youtube(video_path, youtube_url):
    # ffmpeg command to stream the video to YouTube
    video_path = video_path.replace('\\', '/')
    command = [
        'ffmpeg',
        '-re',  # Read input at native frame rate
        '-i', video_path,  # Input file
        '-c:v', 'libx264',  # Video codec
        '-preset', 'veryfast',  # Encoding speed
        '-maxrate', '3000k',  # Max bitrate
        '-bufsize', '6000k',  # Buffer size
        '-pix_fmt', 'yuv420p',  # Pixel format
        '-g', '50',  # Group of picture size (keyframes)
        '-c:a', 'aac',  # Audio codec
        '-b:a', '160k',  # Audio bitrate
        '-f', 'flv',  # Output format for RTMP streaming
        youtube_url
    ]
    
    # Run ffmpeg command as a subprocess
    subprocess.run(command, check=True)

if __name__ == '__main__':
    app.run(debug=True)
