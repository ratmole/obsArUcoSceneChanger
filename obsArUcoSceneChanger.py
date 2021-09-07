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

count = 0
timeout = 0

global source
global clone
global sceneFrom
global sceneTo
global ArUcoDict
global ScSourceArUco
global newSourceName
global newSourceResolution
global process

def script_description():

    return "OBS ArUco Scene Switcher.\nClones and monitors a camera for ArUco markers.\nWhen a marker is detected, it switches to the specified scene.\n\nBy raTMole\nv0.1"

def script_properties():
    devices = [f for f in glob.glob("/dev/video*")]
    devices.sort()
    ArUcoDicts = ['DICT_4X4_50','DICT_4X4_100','DICT_4X4_250','DICT_4X4_1000','DICT_5X5_50','DICT_5X5_100','DICT_5X5_250','DICT_5X5_1000','DICT_6X6_50','DICT_6X6_100','DICT_6X6_250','DICT_6X6_1000','DICT_7X7_50','DICT_7X7_100','DICT_7X7_250','DICT_7X7_1000','DICT_ARUCO_ORIGINAL','DICT_APRILTAG_16h5','DICT_APRILTAG_25h9','DICT_APRILTAG_36h10','DICT_APRILTAG_36h11']

    Resolutions = ['None','16:9','16:10','4:1','1:1','1920x1080','1536x864','1440x810','1280x720','1152x648','1097x617','960x540','853x480','768x432','698x392','640x360']

    props = obs.obs_properties_create()

    source = obs.obs_properties_add_list(props, "source", "Source Video Device", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    clone = obs.obs_properties_add_list(props, "clone", "Cloned Video Device", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)

    ArDicts = obs.obs_properties_add_list(props, "ArUcoDict", "ArUco Dictionary", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)

    sceneFrom = obs.obs_properties_add_list(props, "sceneFrom", "Scene From", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    sceneTo = obs.obs_properties_add_list(props, "sceneTo", "Scene To", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
        
    obs.obs_properties_add_text(props, "newSourceName", "New Source Name", obs.OBS_TEXT_DEFAULT)
    newSourceResolution = obs.obs_properties_add_list(props, "newSourceResolution", "New Source Resolution", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)


    for device in devices:
        obs.obs_property_list_add_string(source, device, device)
        obs.obs_property_list_add_string(clone, device, device)
        
    for ArUcoDict in ArUcoDicts:
        obs.obs_property_list_add_string(ArDicts, ArUcoDict, ArUcoDict)

    scenes = obs.obs_frontend_get_scenes()

    for scene in scenes:
        name = obs.obs_source_get_name(scene)
        obs.obs_property_list_add_string(sceneFrom, name, name)
        obs.obs_property_list_add_string(sceneTo, name, name)
 
    for Resolution in Resolutions:
        obs.obs_property_list_add_string(newSourceResolution, Resolution, Resolution)
           
    obs.source_list_release(scenes)


    return props

    
def script_unload():
    global process
    try:
        process.communicate(str.encode("q")) #Equivalent to send a Q
    except:
        obs.script_log(obs.LOG_INFO, "ffmpeg not running. Restarting")


def script_load(settings):
    global source
    global clone
    global sceneFrom
    global sceneTo
    global ArUcoDict
    global ScSourceArUco
    global newSourceName
    global newSourceResolution

    source              = obs.obs_data_get_string(settings, "source")
    clone               = obs.obs_data_get_string(settings, "clone")
    sceneFrom           = obs.obs_data_get_string(settings, "sceneFrom")
    sceneTo             = obs.obs_data_get_string(settings, "sceneTo")
    ArUcoDict           = obs.obs_data_get_string(settings, "ArUcoDict")
    ScSourceArUco       = obs.obs_data_get_string(settings, "ScSourceArUco")
    newSourceName       = obs.obs_data_get_string(settings, "newSourceName")
    newSourceResolution = obs.obs_data_get_string(settings, "newSourceResolution")

def script_update(settings):
    global source
    global clone
    global sceneFrom
    global sceneTo
    global ArUcoDict
    global ScSourceArUco
    global newSourceName
    global newSourceResolution

    source              = obs.obs_data_get_string(settings, "source")
    clone               = obs.obs_data_get_string(settings, "clone")
    sceneFrom           = obs.obs_data_get_string(settings, "sceneFrom")
    sceneTo             = obs.obs_data_get_string(settings, "sceneTo")
    ArUcoDict           = obs.obs_data_get_string(settings, "ArUcoDict")
    ScSourceArUco       = obs.obs_data_get_string(settings, "ScSourceArUco")
    newSourceName       = obs.obs_data_get_string(settings, "newSourceName")
    newSourceResolution = obs.obs_data_get_string(settings, "newSourceResolution")

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
     
   
def create_ArUco_source():

    global newSourceName
    global newSourceResolution

    current_scene = obs.obs_frontend_get_current_scene()
    scene = obs.obs_scene_from_source(current_scene)
    scene_item = obs.obs_scene_find_source(scene, newSourceName)

    settings = obs.obs_data_create()

    if not scene_item:
        ScSourceArUco = obs.obs_source_create_private("v4l2_input", newSourceName, settings)
        obs.obs_data_set_string(settings, "resolution", newSourceResolution)

        obs.obs_data_set_string(settings, "device_id", clone )
        obs.obs_data_set_bool(settings, "auto_reset", True )
        obs.obs_data_set_int(settings, "timeout_frames", 50 )
        obs.obs_data_set_bool(settings, "buffering", False);
        ScSourceArUco = obs.obs_source_create_private("v4l2_input", newSourceName, settings)
        obs.obs_data_set_string(settings, "resolution", newSourceResolution)
        scale = obs.obs_source_create_private("scale_filter", "Scale", settings)
        obs.obs_source_filter_add(ScSourceArUco, scale)   
    
        obs.obs_scene_add(scene, ScSourceArUco)
        obs.obs_data_release(settings)
        obs.obs_source_release(ScSourceArUco)
        
        obs.obs_scene_release(scene)
        obs.obs_sceneitem_set_order(scene_item,obs.OBS_ORDER_MOVE_BOTTOM)


def findArucoMarkers(frame):
    global count
    global timeout
    global source
    global clone
    global sceneFrom
    global sceneTo
    global ArUcoDict

    img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    key = getattr(aruco, f'{ArUcoDict}')
    arucoDict = aruco.Dictionary_get(key)
    arucoParam = aruco.DetectorParameters_create()
    corners, ids, rejected = aruco.detectMarkers(img_gray, arucoDict, parameters = arucoParam)
    draw=True


    if draw:
        if np.all(ids is not None):  # If there are markers found by detector
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
    global clone
    global sceneFrom
    global sceneTo
    global ArUcoDict
    global ScSourceArUco
    global newSourceName
    global newSourceResolution
    global process

    if not module_loaded('v4l2loopback'):
        obs.script_log(obs.LOG_ERROR, "v4l2loopback module missing!\nScript will not work!\nPlease install v4l2loopback module and run:\nsudo modprobe v4l2loopback devices=2")
        return

    if not source or not clone:
        obs.script_log(obs.LOG_WARNING, "Please set Source and Clone Video Device and reload the script")
        return

    if not sceneFrom or not sceneTo:
        obs.script_log(obs.LOG_WARNING, "Please set Scene From and Scene To and reload the script")
        return

    if not ArUcoDict:
        obs.script_log(obs.LOG_WARNING, "Please set ArUco Dictionary and reload the script")
        return

    if not newSourceName:
        obs.script_log(obs.LOG_WARNING, "Please set New Source Name and reload the script")
        return

    if not newSourceResolution:
        obs.script_log(obs.LOG_WARNING, "Please set New Source Resolution and reload the script")
        return

    process = (
        ffmpeg
        .input(source, f="v4l2")
        .output(clone, f="v4l2")
        .global_args('-loglevel', 'quiet')
        .overwrite_output()
    )


    process = process.run_async(pipe_stdin=True)        

    cam = cv2.VideoCapture(clone)
    cv2_version_major = int(cv2.__version__.split('.')[0])

    set_current_scene(sceneFrom)
    create_ArUco_source()

    while True:

        ret, frame = cam.read()
        if not ret:
            obs.script_log(obs.LOG_ERROR, "Failed to grab frame! If you have changed the Source or Video Device, please restart OBS")
            break
                    
        findArucoMarkers(frame)

    cam.release()
    cv2.destroyAllWindows()

x = threading.Thread(target=run, args=())
x.start()

