"""Read a video and write 3D body and hand landmarks per frame. Usage: extract_pose.py in.mp4 out.json"""
import json, sys, cv2, mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision
src, out = sys.argv[1:3]
P = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path='data/pose_full.task'), running_mode=vision.RunningMode.VIDEO, num_poses=1))
H = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(base_options=BaseOptions(model_asset_path='data/hand.task'), running_mode=vision.RunningMode.VIDEO, num_hands=2, min_hand_detection_confidence=.3))
c = cv2.VideoCapture(src); fps = c.get(cv2.CAP_PROP_FPS) or 16; fr = []; i = 0
while True:
    ok, im = c.read()
    if not ok: break
    m = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(im, cv2.COLOR_BGR2RGB)); t = int(i / fps * 1000)
    p = P.detect_for_video(m, t); h = H.detect_for_video(m, t); e = dict(t=i / fps, pose=None, vis=None, hands=[])
    if p.pose_world_landmarks: l = p.pose_world_landmarks[0]; e['pose'] = [[round(v.x, 4), round(v.y, 4), round(v.z, 4)] for v in l]; e['vis'] = [round(v.visibility or 0, 2) for v in l]
    for w, side in zip(h.hand_world_landmarks, h.handedness): e['hands'].append(dict(side=side[0].category_name, pts=[[round(v.x, 4), round(v.y, 4), round(v.z, 4)] for v in w]))
    fr.append(e); i += 1
json.dump(dict(fps=fps, frames=fr), open(out, 'w'))
ok = sum(1 for f in fr if f['pose']); print('frames', len(fr), 'pose', ok, 'two hands', sum(1 for f in fr if len(f['hands']) == 2), 'one hand', sum(1 for f in fr if len(f['hands']) == 1))
