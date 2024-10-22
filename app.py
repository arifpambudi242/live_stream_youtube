import threading
import subprocess
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# Path to store uploaded videos
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class CustomThread(threading.Thread):
    def __init__(self, thread_id, video_path, youtube_url, stop_event):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.video_path = video_path
        self.youtube_url = youtube_url
        self.stop_event = stop_event
        self.repeat = True

    def stream_to_youtube(self):
        # ffmpeg command to stream the video to YouTube
        video_path = self.video_path.replace('\\', '/')
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
            self.youtube_url
        ]
        if self.repeat:
            command.insert(1, '-stream_loop')
            command.insert(2, '-1')

        # Start the ffmpeg process
        if subprocess.Popen(command):
            return True
        else:
            return False

    def run(self):
        self.stream_to_youtube()
    
    def stop(self):
        self.stop_event.set()

stream_threads = []

@app.route('/')
def index():
    global stream_threads
    if len(stream_threads) > 0:
        print(stream_threads[0].thread_id)
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    global stream_threads
    # Get the uploaded video and stream key from the form
    video = request.files['video']
    stream_key = request.form['stream_key']

    if video and stream_key:
        # Save the uploaded video file
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video.filename).replace('\\', '/')
        video.save(video_path)

        # Stream the video to YouTube using the stream key
        youtube_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

        # Start a new thread to stream the video
        stop_event = threading.Event()
        thread_id = len(stream_threads) + 1
        stream_thread = CustomThread(thread_id, video_path, youtube_url, stop_event)
        stream_threads.append(stream_thread)
        stream_thread.run()

        return f"Video streaming to YouTube started with thread ID !"
    else:
        return "Please upload a video and provide a stream key."

@app.route('/stop_all_streams', methods=['POST'])
def stop_all_streams():
    global stream_threads
    for stream_thread in stream_threads:
        stream_thread.stop()
    return "All streaming threads stopped!"

# streams
@app.route('/streams')
def streams():
    global stream_threads
    return render_template('streams.html', stream_threads=stream_threads)

@app.route('/stop_stream/<int:thread_id>', methods=['POST'])
def stop_stream(thread_id):
    global stream_threads
    for stream_thread in stream_threads:
        if stream_thread.thread_id == thread_id:
            stream_thread.stop()
            stream_threads.remove(stream_thread)
            return f"Stream {thread_id} stopped!"
    return f"Stream {thread_id} not found!"

if __name__ == '__main__':
    app.run(debug=True)
