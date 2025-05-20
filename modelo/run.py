# %%
import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import math
from collections import Counter

from ultralytics.utils.checks import check_imshow
from ultralytics.utils.plotting import Annotator, colors

from collections import defaultdict

# %%
# COLORS = sv.ColorPalette.from_hex(["#E6194B", "#3CB44B", "#FFE119", "#3C76D1"])
COLORS = sv.ColorPalette.from_hex(["#00FF00", "#FF0000"])

ZONE_IN_POLYGONS = [
    np.array([[1021, 969], [1154, 982], [1218, 825], [1088, 808]]),
    np.array([[1510, 514], [1583, 459], [1378, 402], [1359, 453]]),
    np.array([[995, 227], [923, 211], [834, 268], [921, 288]]),
    np.array([[393, 540], [449, 467], [549, 507], [480, 593]]),
]

ZONE_OUT_POLYGONS = [
    np.array([[759, 962], [921, 951], [863, 806], [714, 823]]),
    np.array([[1419, 562], [1433, 654], [1586, 619], [1547, 536]]), ########
    np.array([[1063, 290], [1156, 271], [1138, 197], [1029, 207]]),
    np.array([[462, 452], [456, 366], [624, 347], [607, 434]]),
]

model = YOLO("model-v5.pt")
class_names = model.model.names

names = list(class_names.values())
for i in range(len(names)):
    names.append("indeterminado")

# inicializo en cero los dos arrays (de entrada y salida) que tendrán la cantidad de objetos finales por zona y por clase
"""
Example:
    {
        0: {
            "bicycle": 0,
            "bus": 0,
            "car": 0,
            "motorbike": 0,
            "truck": 0,
            "van": 0
        },
        .
        .
        .
        3: {
            "bicycle": 0,
            "bus": 0,
            "car": 0,
            "motorbike": 0,
            "truck": 0,
            "van": 0
        }
    }
"""
total_obj_zone_in = { i: {key: 0 for key in names} for i in range(len(ZONE_IN_POLYGONS)) }
total_obj_zone_out = { i: {key: 0 for key in names} for i in range(len(ZONE_OUT_POLYGONS)) }

"""
classes = {
    "car": "Auto",
    "bus": "Colectivo",
    "light_truck": "Camión liviano",
    "heavy_truck": "Camión pesado",
    "motorbike": "Moto",
    "bicycle": "Bicicleta",
}
"""

# %%
obj_zones_in = []
obj_zones_out = []
obj_in_for_zones = defaultdict(lambda: [])
obj_out_for_zones = defaultdict(lambda: [])
obj_in_out_zones = defaultdict(lambda: [])
track_results = defaultdict(lambda: [])

track_history = defaultdict(lambda: [])
data_obj_history = defaultdict(lambda: [])

def get_center_bb(box):
    x_center = int((box[0] + box[2]) / 2)
    y_center = int((box[1] + box[3]) / 2)
    return (x_center, y_center)

def draw_polygons(annotated_frame, polygon, number_polygon, zone_type, thickness):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    cv2.polylines(
        annotated_frame, [polygon], isClosed=True, color=COLORS.colors[zone_type].as_bgr(), thickness=thickness
    )
    zone_center = sv.get_polygon_center(polygon=polygon)
    cv2.putText(annotated_frame, str(number_polygon), (int(zone_center.x), int(zone_center.y)), font, font_scale, COLORS.colors[zone_type].as_bgr(), thickness=thickness)
    
    return annotated_frame

def draw_zones_in_out(annotated_frame, thickness):
    for i, (zone_in, zone_out) in enumerate(zip(ZONE_IN_POLYGONS, ZONE_OUT_POLYGONS)):
        draw_polygons(annotated_frame, zone_in, i, 0, thickness)
        draw_polygons(annotated_frame, zone_out, i, 1, thickness)
    return annotated_frame

def detect_zone_in(box):
    for i, (polygon) in enumerate(ZONE_IN_POLYGONS):
        if (cv2.pointPolygonTest(polygon, get_center_bb(box), False) > 0):  # > 0 dentro del polígono
            return i

    return -1

def save_zone_in(box, track_id):
    if track_id not in obj_zones_in:
        zone_in = detect_zone_in(box)
        if zone_in >= 0:
            obj_zones_in.append(track_id)
            obj_in_for_zones[zone_in].append(track_id)

def detect_zone_out(box):
    for i, (polygon) in enumerate(ZONE_OUT_POLYGONS):
        if (cv2.pointPolygonTest(polygon, get_center_bb(box), False) > 0):  # > 0 dentro del polígono
            return i

    return -1

def save_zone_out(box, track_id):
    if track_id not in obj_zones_out:
        zone_out = detect_zone_out(box)
        if zone_out >= 0:
            obj_zones_out.append(track_id)
            obj_out_for_zones[zone_out].append(track_id)

                
def draw_bb_and_save_track(frame, annotator, box, cls, track_id, act_frame, confidence):
    annotator.box_label(box, color=colors(int(cls), True), label=f"{track_id} - {class_names[int(cls)]}")

    # Store tracking and data object history
    data_obj_history[track_id].append(
        {
            "act_frame": act_frame,
            "class_id": int(cls),
            "confidence": confidence
        })
    track = track_history[track_id]
    track.append((int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)))
    if len(track) > 30:
        track.pop(0)

    # Plot tracks
    points = np.array(track, dtype=np.int32).reshape((-1, 1, 2))
    cv2.polylines(frame, [points], isClosed=False, color=colors(int(cls), True), thickness=2)


H_UMBRAL = 0.8  # Ajusta según tu necesidad

def calculate_entropy(track_data, track_id):
    total_track = len(track_data)
    class_counts = Counter()
    for item in track_data:
        class_counts[item['class_id']] += 1
    probabilities = [count / total_track for class_id, count in class_counts.items()]
    entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
    
    return class_counts, entropy

def classify_track(entropy, class_counts):
    """Determina la clase del trackeo o si hay incertidumbre."""
    assigned_class = max(class_counts, key=class_counts.get)
    return class_names[assigned_class]

def get_final_results():
    for track_id, data in data_obj_history.items():
        class_counts, entropy = calculate_entropy(data, track_id)
        classification = classify_track(entropy, class_counts)
        track_results[track_id] = {
            "entropy": entropy,
            "classification": classification
        }

# %%
video_path = "vuelo03_4k.mp4"
cap = cv2.VideoCapture(video_path)

w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

# result = cv2.VideoWriter("object_tracking.avi",
#                        cv2.VideoWriter_fourcc(*'mp4v'),
#                        fps,
#                        (w, h))

# inicializo en cero los arays que tendrán la cantidad de objetos finales por zona
act_frame = 0

while cap.isOpened() and act_frame < 500:
    success, frame = cap.read()

    alto_original, ancho_original = frame.shape[:2]
    ancho_nuevo = 1920
    alto_nuevo = int(alto_original * (ancho_nuevo / ancho_original))
    frame = cv2.resize(frame, (ancho_nuevo, alto_nuevo))

    act_frame += 1
    if act_frame % 2 == 0:
        if success:
            results = model.track(frame, persist=True, verbose=False, agnostic_nms=True)
            boxes = results[0].boxes.xyxy.cpu()

            draw_zones_in_out(frame, 2)
            
            if results[0].boxes.id is not None:
                clss = results[0].boxes.cls.cpu().tolist()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                confs = results[0].boxes.conf.float().cpu().tolist()
                # Annotator Init
                annotator = Annotator(frame, line_width=1)
                for box, cls, track_id, confidence in zip(boxes, clss, track_ids, confs):
                    save_zone_in(box, track_id)
                    save_zone_out(box, track_id)
                    # if (track_id in obj_in_out_zones):
                    draw_bb_and_save_track(frame, annotator, box, cls, track_id, act_frame, confidence)

            cv2.imshow("Video", frame)
            # result.write(frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            break

# print(total_obj_zone_in)
# print(total_obj_zone_out)
# result.release()
cap.release()
cv2.destroyAllWindows()

get_final_results()

# %%
print(obj_in_for_zones.items())
print(obj_out_for_zones.items())
for zone, tracks in obj_in_for_zones.items():
    for track in tracks:
        print(track)
        total_obj_zone_in[zone][track_results[track]["classification"]] += 1
    # print(f"    {zone}: {tracks}")
print(total_obj_zone_in)

# %%
for i, (zone) in enumerate(total_obj_zone_in):
    print(f"Zona de entrada {i}")
    for key, value in total_obj_zone_in[i].items():
        print(f"    {key}: {value}")

for i, (zone) in enumerate(total_obj_zone_out):
    print(f"Zona de salida {i}")
    for key, value in total_obj_zone_out[i].items():
        print(f"    {key}: {value}")

# %%



