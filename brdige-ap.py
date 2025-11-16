import re
import pandas as pd
import numpy as np

input_file = "basicbridge-walledv6_PLA_7m52s.gcode"

x_vals = []
y_vals = []
e_vals = []

bridge = False

# Your volume rate per mm of filament extruded for bridging! (= E value per mm, my is standard = 0.0331724073)
bridge_extrusion_mm = 0.05307585168

# flowrate percentage drop when near a wall
flow_rate_percentage = 0.8

# mm from the wall to start modifying the flowrate
wall_distance_threshold = 10.0

# feed rate in mm/min for bridging moves
feed_rate_bridge_middle = 600
feed_rate_bridge_start_end = 480

with open(input_file, "r") as f:
    lines = f.readlines()

i = 0

while i < len(lines):
    line = lines[i].strip()


    # Detect start of bridge
    if line.startswith(";TYPE:Bridge"):
        bridge = True
        start_line = lines[i-4].strip() # Look 4 lines back to get the first X,Y,E line, starting point of the bridge, manually check, could be 3 lines also.
        x_match = re.search(r"X([0-9.+-]+)", start_line)
        y_match = re.search(r"Y([0-9.+-]+)", start_line)
        e_match = re.search(r"E([0-9.+-]+)", start_line)

        x = float(x_match.group(1)) if x_match else None
        y = float(y_match.group(1)) if y_match else None
        e = float(e_match.group(1)) if e_match else None

        x_vals.append(x)
        y_vals.append(y)
        e_vals.append(e)
        

    # Collect X, Y, E values during bridging
    if line.startswith("G1 X") and bridge == True:
        # Extract X or Y if present
        x_match = re.search(r"X([0-9.+-]+)", line)
        y_match = re.search(r"Y([0-9.+-]+)", line)
        e_match = re.search(r"E([0-9.+-]+)", line)

        x = float(x_match.group(1)) if x_match else None
        y = float(y_match.group(1)) if y_match else None
        e = float(e_match.group(1)) if e_match else None

        # Only append if all are present
        if x is not None and y is not None and e is not None:
            x_vals.append(x)
            y_vals.append(y)
            e_vals.append(e)


    # Detect end of bridge, use ";WIPE_START" or "G1 E-", check your own gcode file
    if line.startswith("G1 E-") and bridge == True:
            bridge = False


    i += 1

# Make DataFrame
df = pd.DataFrame({"X": x_vals, "Y": y_vals, "E": e_vals})

# Calculate segment lengths
df['segment_length'] = np.hypot(df['X'].diff(), df['Y'].diff())


#print(df.tail(20))




# Create new G-code text for the bridge with modified extrusion
new_gcode = []

for i in range(1, len(df)):
     
    curr_x = df.at[i, "X"]
    curr_y = df.at[i, "Y"]
    prev_x = df.at[i-1, "X"]
    prev_y = df.at[i-1, "Y"]
    segment_length = df.at[i, "segment_length"]

    curr_e = df.at[i, "E"]

    # vector unit components (direction of movement +1 or -1)
    ux = (curr_x - prev_x) / segment_length

    
    if (segment_length > (wall_distance_threshold * 2)):
        p1_x = prev_x + (wall_distance_threshold * ux)
        p1_e = wall_distance_threshold * bridge_extrusion_mm * flow_rate_percentage
        p2_x = curr_x - (wall_distance_threshold * ux)
        p2_e = (p2_x - p1_x) * bridge_extrusion_mm * ux
        p3_x = curr_x 
        p3_e = wall_distance_threshold * bridge_extrusion_mm * flow_rate_percentage

        new_gcode.append(f"G1 X{p1_x:.3f} Y{curr_y:.3f} E{p1_e:.5f} F{feed_rate_bridge_start_end}")
        new_gcode.append(f"G1 X{p2_x:.3f} Y{curr_y:.3f} E{p2_e:.5f} F{feed_rate_bridge_middle}")
        new_gcode.append(f"G1 X{p3_x:.3f} Y{curr_y:.3f} E{p3_e:.5f} F{feed_rate_bridge_start_end}")

    else:
        new_gcode.append(f"G1 X{curr_x:.3f} Y{curr_y:.3f} E{curr_e:.5f} F{feed_rate_bridge_middle}")


for line in new_gcode:
    print(line)
