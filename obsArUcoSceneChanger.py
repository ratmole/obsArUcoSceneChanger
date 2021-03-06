#!/usr/bin/python3
import cv2
import os
import sys
import time
import glob
import ffmpeg
import threading
import subprocess
import numpy as np
import obspython as obs
import cv2.aruco as aruco
import v4l2ctl

count = 0
timeout = 0

global source
global sourceFormat
global sourceFormats
global clone
global sceneFrom
global sceneTo
global ArUcoDict
global ArUcoID
global sourceName
global ProcessF
sourceFormats = []

def script_description():
    return "OBS ArUco Scene Switcher.\nClones and monitors a camera for ArUco markers.\nWhen a marker is detected, it switches to the specified scene.\n\nBy raTMole\nv0.1"

def script_properties():

    global sourceFormats

    tmp = []
    devices = [f for f in glob.glob("/dev/video*")]
    devices.sort()

    ArUcoDicts = ['DICT_4X4_50','DICT_4X4_100','DICT_4X4_250','DICT_4X4_1000','DICT_5X5_50','DICT_5X5_100','DICT_5X5_250','DICT_5X5_1000','DICT_6X6_50','DICT_6X6_100','DICT_6X6_250','DICT_6X6_1000','DICT_7X7_50','DICT_7X7_100','DICT_7X7_250','DICT_7X7_1000','DICT_ARUCO_ORIGINAL','DICT_APRILTAG_16h5','DICT_APRILTAG_25h9','DICT_APRILTAG_36h10','DICT_APRILTAG_36h11']

    props = obs.obs_properties_create()

    source = obs.obs_properties_add_list(props, "source", "Source Video Device", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    sourceFormat = obs.obs_properties_add_list(props, "sourceFormat", "Source Video Format", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    clone = obs.obs_properties_add_list(props, "clone", "Cloned Video Device", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)

    ArDicts = obs.obs_properties_add_list(props, "ArUcoDict", "ArUco Dictionary", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_properties_add_int(props, "ArUcoID", "ArUco Id", 1, 999, 1)


    sceneFrom = obs.obs_properties_add_list(props, "sceneFrom", "Scene From", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    sceneTo = obs.obs_properties_add_list(props, "sceneTo", "Scene To", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    
    sourceName = obs.obs_properties_add_list(props, "sourceName", "V4L2 Source To", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
        

    for device in devices:
        obs.obs_property_list_add_string(source, device, device)
        obs.obs_property_list_add_string(clone, device, device)

    for source_f in sourceFormats:
        obs.obs_property_list_add_string(sourceFormat, source_f, source_f)
       
    for ArUcoDict in ArUcoDicts:
        obs.obs_property_list_add_string(ArDicts, ArUcoDict, ArUcoDict)

    scenes = obs.obs_frontend_get_scenes()

    for scene in scenes:
        name = obs.obs_source_get_name(scene)
        obs.obs_property_list_add_string(sceneFrom, name, name)
        obs.obs_property_list_add_string(sceneTo, name, name)
 
    obs.source_list_release(scenes)

    ScSources = obs.obs_enum_sources()
    if ScSources is not None:
        for source_ in ScSources:
            source_id = obs.obs_source_get_id(source_)
            if source_id == "v4l2_input":
                name = obs.obs_source_get_name(source_)
                if name not in tmp:
                    obs.obs_property_list_add_string(sourceName, name, name)
                    tmp.append(name)

        obs.source_list_release(ScSources)

    return props

def stop_ffmpeg():
    pid = "/tmp/obsArUco.pid"
    global ProcessF

    try:
        ProcessF.communicate(str.encode("q")) #Equivalent to send a Q
    except:
        if os.path.isfile(pid):
            os.system("kill -9 `cat "+pid+"`")
            os.system("rm "+pid)


def start_ffmpeg(source,clone,sourceFormat):
    global ProcessF

    pid = "/tmp/obsArUco.pid"

    process = (
        ffmpeg
        .input(source, f="v4l2", pix_fmt=sourceFormat,r="30")
        .output(clone, f="v4l2", pix_fmt="yuyv422")
        .global_args('-loglevel', 'warning')
        .overwrite_output()
    )
    ProcessF = process.run_async(pipe_stdin=True)        

    pidfilename = os.path.join(pid)
    pidfile = open(pidfilename, 'w')
    pidfile.write(str(ProcessF.pid))
    pidfile.close()

def script_unload():
    stop_ffmpeg()


def script_load(settings):
    global source
    global sourceFormat
    global clone
    global sceneFrom
    global sceneTo
    global ArUcoDict
    global ArUcoID
    global sourceName

    source              = obs.obs_data_get_string(settings, "source")
    sourceFormat        = obs.obs_data_get_string(settings, "sourceFormat")
    clone               = obs.obs_data_get_string(settings, "clone")
    sceneFrom           = obs.obs_data_get_string(settings, "sceneFrom")
    sceneTo             = obs.obs_data_get_string(settings, "sceneTo")
    ArUcoDict           = obs.obs_data_get_string(settings, "ArUcoDict")
    ArUcoID             = obs.obs_data_get_int(settings, "ArUcoID")
    sourceName          = obs.obs_data_get_string(settings, "sourceName")

    if source:
        source_formats(source)

def script_update(settings):
    global source
    global sourceFormat
    global clone
    global sceneFrom
    global sceneTo
    global ArUcoDict
    global sourceName

    source              = obs.obs_data_get_string(settings, "source")
    sourceFormat        = obs.obs_data_get_string(settings, "sourceFormat")
    clone               = obs.obs_data_get_string(settings, "clone")
    sceneFrom           = obs.obs_data_get_string(settings, "sceneFrom")
    sceneTo             = obs.obs_data_get_string(settings, "sceneTo")
    ArUcoDict           = obs.obs_data_get_string(settings, "ArUcoDict")
    ArUcoID             = obs.obs_data_get_int(settings, "ArUcoID")
    sourceName          = obs.obs_data_get_string(settings, "sourceName")

def source_formats(source):
    global sourceFormats

    sourceFormats = []
    d = v4l2ctl.V4l2Device(source)
    for f in d.formats:
        sourceFormats.append(f"{f.format.name}".lower())

def set_current_scene(newName):
    scenes = obs.obs_frontend_get_scenes()
    for scene in scenes:
        name = obs.obs_source_get_name(scene)
        if name == newName:
            obs.obs_frontend_set_current_scene(scene)

def module_loaded(module_name):
    lsmod_proc = subprocess.Popen(['lsmod'], stdout=subprocess.PIPE)
    grep_proc = subprocess.Popen(['grep', module_name], stdin=lsmod_proc.stdout)
    grep_proc.communicate()  # Block until finished
    return grep_proc.returncode == 0

def updateSource():
    global sourceName

    current_scene = obs.obs_frontend_get_current_scene()
    scene = obs.obs_scene_from_source(current_scene)
    scene_item = obs.obs_scene_find_source(scene, sourceName)
    sourceItem = obs.obs_sceneitem_get_source(scene_item)

    settings = obs.obs_source_get_settings(sourceItem)
    obs.obs_data_set_string(settings, "device_id", clone )
    obs.obs_source_update(sourceItem, settings)
    obs.obs_data_release(settings)

def findArucoMarkers(frame):
    global count
    global timeout
    global source
    global clone
    global sceneFrom
    global sceneTo
    global ArUcoDict
    global ArUcoID

    img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    key = getattr(aruco, f'{ArUcoDict}')
    arucoDict = aruco.Dictionary_get(key)
    arucoParam = aruco.DetectorParameters_create()
    corners, ids, rejected = aruco.detectMarkers(img_gray, arucoDict, parameters = arucoParam)
    draw=True

    if draw:
        if np.all(ids is not None):  # If there are markers found by detector
            if ArUcoID in ids:
                if count == 0:
                    set_current_scene(sceneTo)
                count += 1
                timeout=0
        else:
            if count > 1:
                if timeout > 25:
                    set_current_scene(sceneFrom)
                    count = 0
                timeout+=1
def run():

    global source
    global sourceFormat
    global clone
    global sceneFrom
    global sceneTo
    global ArUcoDict
    global sourceName
    global ProcessF
    

    if not module_loaded('v4l2loopback'):
        obs.script_log(obs.LOG_ERROR, "v4l2loopback module missing!\nScript will not work!\nPlease install v4l2loopback module and run:\nsudo modprobe v4l2loopback devices=2")
        return
    
    if not source or not clone:
        obs.script_log(obs.LOG_WARNING, "Please set Source and Clone Video Device and reload the script")
        return

    if not sourceFormat:
        obs.script_log(obs.LOG_WARNING, "Please set Source Video Format and reload the script")
        return

    if not sceneFrom or not sceneTo:
        obs.script_log(obs.LOG_WARNING, "Please set Scene From and Scene To and reload the script")
        return

    if not ArUcoDict:
        obs.script_log(obs.LOG_WARNING, "Please set ArUco Dictionary and reload the script")
        return

    if not sourceName:
        obs.script_log(obs.LOG_WARNING, "Please set Source Name and reload the script")
        return

    stop_ffmpeg()
    
    start_ffmpeg(source,clone,sourceFormat)
    
    cam = cv2.VideoCapture(clone)

    set_current_scene(sceneFrom)
    updateSource()

    while True:
        ret, frame = cam.read()
        if not ret:
            obs.script_log(obs.LOG_ERROR, "Failed to grab frame! If you have changed the Source or Video Device, please restart OBS")
            break
        findArucoMarkers(frame)

    cam.release()
    cv2.destroyAllWindows()

x = threading.Thread(target=run, args=(),daemon = True)
x.start()

