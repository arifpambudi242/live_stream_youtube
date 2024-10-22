from flask import Flask, render_template, request, redirect, url_for
import os
import subprocess
import threading

app = Flask(__name__)

# Path to store uploaded videos
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Dictionary to store threads
stream_threads = {}
thread_id_counter = 1

@app.route('/')
def index():
    # Send active stream IDs to the template
    return render_template('index.html', streams=stream_threads.keys())

@app.route('/upload', methods=['POST'])
def upload_video():
    global thread_id_counter

    # Get the uploaded video and stream key from the form
    video = request.files['video']
    stream_key = request.form['stream_key']

    if video and stream_key:
        # Save the uploaded video file
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video.filename).replace('\\', '/')
        video.save(video_path)

        # Stream the video to YouTube using the stream key
        youtube_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

        # Create a new thread to stream the video
        thread_id = thread_id_counter
        stream_thread = threading.Thread(target=stream_to_youtube, args=(video_path, youtube_url, thread_id))
        stream_thread.start()

        # Store the thread in the dictionary with an ID
        stream_threads[thread_id] = stream_thread
        thread_id_counter += 1

        return f"Video streaming to YouTube started! Stream ID: {thread_id}"
    else:
        return "Please upload a video and provide a stream key."

@app.route('/stop_stream/<int:thread_id>', methods=['POST'])
def stop_stream(thread_id):
    # Stop the stream by killing the ffmpeg process in the specified thread
    if thread_id in stream_threads:
        # Kill the ffmpeg process for the specific thread
        subprocess.run(['pkill', '-TERM', '-f', f'ffmpeg.*{thread_id}'], check=False)
        stream_threads.pop(thread_id)
        return f"Video streaming with Stream ID {thread_id} stopped!"
    else:
        return f"No active stream with Stream ID {thread_id}."

@app.route('/streams', methods=['GET'])
def list_streams():
    # Display the currently active streams
    return render_template('streams.html', streams=stream_threads.keys())

def stream_to_youtube(video_path, youtube_url, thread_id):
    global stream_threads

    
    # ffmpeg command to stream the video to YouTube in a loop
    video_path = video_path.replace('\\', '/')
    command = [
        'ffmpeg',
        '-stream_loop', '-1',  # Loop video infinitely
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

    # Run ffmpeg command as a subprocess and attach thread ID to the process name for easy identification
    subprocess.run(command, check=True)

if __name__ == '__main__':
    app.run(debug=True)
