import threading
import subprocess
import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Path to store uploaded videos
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Global variables to track threads and stop events
stream_threads = {}
stop_events = {}
thread_id_counter = 1

@app.route('/')
def index():
    return render_template('index.html')

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

        # Create a new stop event for the thread
        stop_event = threading.Event()

        # Create a new thread to stream the video
        thread_id = thread_id_counter
        stream_thread = threading.Thread(target=stream_to_youtube, args=(video_path, youtube_url, stop_event), daemon=True)
        stream_thread.start()

        # Store the thread and stop event in the dictionaries with an ID
        stream_threads[thread_id] = stream_thread
        stop_events[thread_id] = stop_event
        thread_id_counter += 1

        return f"Video streaming to YouTube started with thread ID {thread_id}!"
    else:
        return "Please upload a video and provide a stream key."

@app.route('/stop_all_streams', methods=['POST'])
def stop_all_streams():
    # Stop all streaming threads by setting the stop event for each thread
    for thread_id in stream_threads:
        stop_events[thread_id].set()

        # Optionally join the thread (wait for it to finish)
        stream_threads[thread_id].join()

    # Clear the dictionaries of threads and stop events
    stream_threads.clear()
    stop_events.clear()

    return "All streaming threads stopped!"

# streams
@app.route('/streams')
def streams():
    global stream_threads
    return render_template('streams.html', stream_threads=stream_threads)

@app.route('/stop_stream/<int:thread_id>', methods=['POST'])
def stop_stream(thread_id):
    # Check if the thread with the given ID exists
    if thread_id in stream_threads and thread_id in stop_events:
        # Set the stop event to signal the thread to stop
        stop_events[thread_id].set()

        # Optionally join the thread (wait for it to finish)
        stream_threads[thread_id].join()

        # Remove the thread and stop event from the dictionaries
        del stream_threads[thread_id]
        del stop_events[thread_id]

        return f"Streaming stopped for thread ID {thread_id}!"
    else:
        return f"No streaming thread found with ID {thread_id}."

def stream_to_youtube(video_path, youtube_url, stop_event, is_loop=True):
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
    if is_loop:
        command.insert(1, '-stream_loop')
        command.insert(2, '-1')

    # Start the ffmpeg process
    process = subprocess.Popen(command)

    # Monitor the stop event
    while not stop_event.is_set():
        # Check periodically if the thread should stop
        process.poll()
        if process.returncode is not None:  # Process has finished
            break

    # If the stop event is set, terminate the ffmpeg process
    if stop_event.is_set():
        process.terminate()
        process.wait()

if __name__ == '__main__':
    app.run(debug=True)
