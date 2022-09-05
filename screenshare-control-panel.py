#!/usr/bin/env python

import subprocess
import sys
import time
import pulsectl
import tkinter as tk

root = tk.Tk(className='screenshare-control-panel')
pulse = pulsectl.Pulse('python-script')

# Example

#  Headphones                         Discord, Telegram, Zoom, etc.
#      ▲                                         ▲
#      │                                         │
#      │                                         │
# ScreenshareApplicationSink ──────► ScreenshareMicrophoneSink
#      ▲                                         ▲
#      │                                         │
#      │                                         │
#     VLC                                  USB Microphone

APPLICATION_SINK_NAME = "ScreenshareApplicationSink"
MICROPHONE_SINK_NAME = "ScreenshareMicrophoneSink"
HEADPHONES = "alsa_output.pci-0000_00_1f.3.analog-stereo"
MICROPHONE = "alsa_input.usb-OLYMPUS_IMAGING_CORP._DIGITAL_VOICE_RECORDER_2001320940264000-02.analog-stereo"

# Creates sink where application will be redirected
APPLICATION_SINK = subprocess.run(f"pactl load-module module-null-sink sink_name={APPLICATION_SINK_NAME} sink_properties=device.description={APPLICATION_SINK_NAME}", shell=True, capture_output=True).stdout.decode()

# When you redirect app, you stop hearing it, so this will loopback this back to our headphones
APPLICATION_SINK_LOOPBACK = subprocess.run(f"pactl load-module module-loopback source={APPLICATION_SINK_NAME}.monitor sink={HEADPHONES}", shell=True, capture_output=True).stdout.decode()

# Additional sink for microphone only, you could do without it and loopback to APPLICATION_SINK_NAME directly, but you would hear yourself then. This fixes it.
MICROPHONE_SINK = subprocess.run(f"pactl load-module module-null-sink sink_name={MICROPHONE_SINK_NAME} sink_properties=device.description={MICROPHONE_SINK_NAME}", shell=True, capture_output=True).stdout.decode()

# Loopback our microphone to MICROPHONE_SINK_NAME sink
MICROPHONE_SINK_LOOPBACK = subprocess.run(f"pactl load-module module-loopback source={MICROPHONE} sink={MICROPHONE_SINK_NAME}", shell=True, capture_output=True).stdout.decode()

# Loopback our APPLICATION_SINK_NAME to MICROPHONE_SINK_NAME.
LOOPBACK_FOR_ALL_APPLICATIONS = subprocess.run(f"pactl load-module module-loopback source={APPLICATION_SINK_NAME}.monitor sink={MICROPHONE_SINK_NAME}", shell=True, capture_output=True).stdout.decode()

# For some reason, on my machine, sinks are muted by default
# pactl set-sink-mute $APPLICATION_SINK 0
# pactl set-sink-mute $APPLICATION_SINK_LOOPBACK 0
# pactl set-sink-mute $MICROPHONE_SINK 0
# pactl set-sink-mute $MICROPHONE_SINK_LOOPBACK 0

def cleanup_and_exit():
    print("Unloading LOOPBACK_FOR_ALL_APPLICATIONS")
    subprocess.run(f"pactl unload-module {LOOPBACK_FOR_ALL_APPLICATIONS}", shell=True)

    print("\nUnloading MICROPHONE_SINK_LOOPBACK")
    subprocess.run(f"pactl unload-module {MICROPHONE_SINK_LOOPBACK}", shell=True)

    print("\nUnloading MICROPHONE_SINK")
    subprocess.run(f"pactl unload-module {MICROPHONE_SINK}", shell=True)

    print("\nUnloading APPLICATION_SINK_LOOPBACK")
    subprocess.run(f"pactl unload-module {APPLICATION_SINK_LOOPBACK}", shell=True)

    print("\nUnloading APPLICATION_SINK")
    subprocess.run(f"pactl unload-module {APPLICATION_SINK}", shell=True)

    print("\nGoodbye")
    sys.exit(0)

entries = {}
current_frame = tk.Frame(root)
current_frame.pack()

def reroute_app_to_application_sink(sink_index):
    if entries[sink_index]['isEnabled'].get():
        pulse.sink_input_move(sink_index, pulse.get_sink_by_name(APPLICATION_SINK_NAME).index)
    else:
        pulse.sink_input_move(sink_index, pulse.get_sink_by_name(HEADPHONES).index)

def update_info():
    global current_frame, entries, pulse

    try:
        sink_ids = []

        for sink in pulse.sink_input_list():
            if 'application.process.id' in sink.proplist:
                for index in entries:
                    if index == sink.index:
                        entries[index]['sink'] = sink

                sink_ids.append(sink.index)

                if not sink.index in entries:
                    inner_frame = tk.Frame(current_frame)
                    variable = tk.BooleanVar()
                    entries[sink.index] = {'sink': sink, 'frame': inner_frame, 'isEnabled': variable}
                    button = tk.Checkbutton(inner_frame, variable=variable, command=lambda index=sink.index: reroute_app_to_application_sink(index))
                    label = tk.Label(inner_frame, text=f"{sink.proplist['application.name']} (PID: {sink.proplist['application.process.id']}, EXE: {sink.proplist['application.process.binary']}, Title: \"{sink.name}\")")
                    button.pack(side=tk.LEFT)
                    label.pack(side=tk.LEFT)
                    inner_frame.pack(fill=tk.X)

        for index in entries:
            if entries[index]['sink'].index not in sink_ids:
                entries[index]['frame'].destroy()

            if entries[index]['sink'].__dict__['sink'] != pulse.get_sink_by_name(HEADPHONES).index:
                entries[index]['isEnabled'].set(True)
            else:
                entries[index]['isEnabled'].set(False)
    except Exception as e:
        print("Exception occured:", str(e))

    root.after(1000, update_info)

root.title("Screenshare Control Panel")
root.geometry('800x200')
root.protocol("WM_DELETE_WINDOW", cleanup_and_exit)

button = tk.Button(text="Exit", command=cleanup_and_exit)
button.pack(side=tk.BOTTOM)

root.after(0, update_info)
root.mainloop()
