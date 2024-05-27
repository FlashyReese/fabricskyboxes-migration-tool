#!/usr/bin/env python3
import os
import json
import math

import glob

# Check if an argument is provided
import sys

def is_within_range(value, range_min, range_max):
    return range_min <= value <= range_max

def is_within_any_range(value, ranges):
    for range_obj in ranges:
        if is_within_range(value, range_obj['min'], range_obj['max']):
            return True
    return False

def replace_range(range_obj, new_min, new_max):
    range_obj['min'] = new_min
    range_obj['max'] = new_max

def time_loop_helper(time, day):
    if time == 0:
        if day == 1:
            return 0
        else:
            return 24000 * day - 1
    else:
        return time * day

if len(sys.argv) < 2:
    print("Usage: {} directory_path".format(sys.argv[0]))
    sys.exit(1)

# Store the directory path from the argument
directory = sys.argv[1]

# List to store files that need manual intervention
manual_fix = []

# List of store files that need manual loop check
manual_loop_check = []

# Find all JSON files under exampledirectory/assets/*/sky/
json_files = glob.glob(os.path.join(directory, "assets", "*", "sky", "**", "*.json"), recursive=True)

print("Found", len(json_files), "JSON files under", directory)
for file in json_files:
    print("Processing file:", file)
    with open(file, 'r+') as f:
        try:
            json_data = json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON in file")
            continue

        # Check if the file contains a schemaVersion key
        if 'schemaVersion' in json_data:
            # Example condition to change schemaVersion based on its value
            current_version = json_data['schemaVersion']
            current_type = json_data.get('type', '')

            if current_version == 2:
                # Update the schemaVersion to a new value
                json_data['schemaVersion'] = 1
                print("Updated schemaVersion from", current_version, "to 1")

                if current_type == "single-sprite-square-textured":
                    json_data['type'] = "square-textured"
                    print("Updated type from", current_type, "to square-textured")
                elif current_type == "multi-texture":
                    json_data['type'] = "multi-textured"
                    print("Updated type from", current_type, "to multi-textured")

                    # Rename animations to animatableTextures
                    if 'animations' in json_data:
                        json_data['animatableTextures'] = json_data['animations']
                        del json_data['animations']
                        print("Renamed animations to animatableTextures")

                    # Rename uvRanges to uvRange in animatableTextures array
                    if 'animatableTextures' in json_data:
                        for texture in json_data['animatableTextures']:
                            if 'uvRanges' in texture:
                                texture['uvRange'] = texture['uvRanges']
                                del texture['uvRanges']
                                print("Renamed uvRanges to uvRange in an element of animatableTextures")
                elif current_type not in ["monocolor", "overworld", "end"]:
                    manual_fix.append(file)

                # Rename properties priority if present
                if 'properties' in json_data and 'priority' in json_data['properties']:
                    json_data['properties']['layer'] = json_data['properties']['priority']
                    del json_data['properties']['priority']
                    print("Rename priority to layer")

                # Rename blend mode alpha to normal if present
                if 'blend' in json_data and 'type' in json_data['blend'] and json_data['blend']['type'] == "alpha":
                    json_data['blend']['type'] = "normal"
                    print("Updated blend mode from alpha to normal")

                # Migrate properties.fade object if present
                if 'properties' in json_data and 'fade' in json_data['properties'] \
                        and all(key in json_data['properties']['fade'] for key in ['startFadeIn', 'endFadeIn', 'startFadeOut', 'endFadeOut']):
                    fade_data = json_data['properties']['fade']
                    startFadeIn = fade_data['startFadeIn']
                    endFadeIn = fade_data['endFadeIn']
                    startFadeOut = fade_data['startFadeOut']
                    endFadeOut = fade_data['endFadeOut']

                    # Check for maxAlpha and minAlpha in properties
                    maxAlpha = json_data['properties'].get('maxAlpha', 1.0)
                    minAlpha = json_data['properties'].get('minAlpha', 0.0)

                    json_data['properties']['fade']['keyFrames'] = {
                        startFadeIn: minAlpha,
                        endFadeIn: maxAlpha,
                        startFadeOut: maxAlpha,
                        endFadeOut: minAlpha
                    }

                    # Loop conditions
                    if 'conditions' in json_data and 'loop' in json_data['conditions']:
                        loop_data = json_data['conditions']['loop']
                        days = loop_data.get('days', 0.0)
                        ranges = loop_data.get('ranges', [])

                        if ranges and days > 0:
                            # Step 0: Transform ranges to scale
                            fade_duration = int(24000 * days)
                            for range1 in ranges:
                                storageMinTransformed = range1['min'] / days
                                storageMaxTransformed = range1['max'] / days
                                replace_range(range1, fade_duration * storageMinTransformed, fade_duration * storageMaxTransformed)

                            # Step 1: Account for days in the fade keyframes
                            json_data['properties']['fade']['duration'] = fade_duration

                            # Step 2: Populate the keyframes
                            newKeyFrames = {}
                            for day in range(1, int(math.ceil(days)) + 1):
                                newStartFadeIn = time_loop_helper(startFadeIn, day)
                                newEndFadeIn = time_loop_helper(endFadeIn, day)
                                newStartFadeOut = time_loop_helper(startFadeOut, day)
                                newEndFadeOut = time_loop_helper(endFadeOut, day)

                                newKeyFrames[newStartFadeIn] = minAlpha
                                newKeyFrames[newEndFadeIn] = maxAlpha
                                newKeyFrames[newStartFadeOut] = maxAlpha
                                newKeyFrames[newEndFadeOut] = minAlpha

                            # Step 3: Filter entire keyframes to only include the ones that are within the ranges
                            filteredKeyFrames = {k: v for k, v in newKeyFrames.items() if is_within_any_range(k, ranges)}

                            # Step 4: Clamp the keyframes to the ranges
                            transitionInDuration = json_data['properties'].get('transitionInDuration', 20)
                            transitionOutDuration = json_data['properties'].get('transitionOutDuration', 20)

                            for range1 in ranges:
                                rangeMin = int(range1['min'] - transitionInDuration)
                                rangeMax = int(range1['max'] + transitionOutDuration)
                                if rangeMin >= 0:
                                    filteredKeyFrames[rangeMin] = minAlpha
                                else:
                                    filteredKeyFrames[0] = minAlpha

                                if rangeMax < fade_duration:
                                    filteredKeyFrames[rangeMax] = minAlpha
                                else:
                                    filteredKeyFrames[fade_duration - 1] = minAlpha

                            # Step 5: Replace the keyframes
                            json_data['properties']['fade']['keyFrames'] = filteredKeyFrames
                            print("Converted loop to fade")
                            manual_loop_check.append(file)

                    del json_data['properties']['fade']['startFadeIn']
                    del json_data['properties']['fade']['endFadeIn']
                    del json_data['properties']['fade']['startFadeOut']
                    del json_data['properties']['fade']['endFadeOut']
                    # Delete maxAlpha and minAlpha if they exist
                    json_data['properties'].pop('maxAlpha', None)
                    json_data['properties'].pop('minAlpha', None)
                    print("Migrated properties.fade")

                # Check and remove conditions.loop key if present
                if 'conditions' in json_data and 'loop' in json_data['conditions']:
                    del json_data['conditions']['loop']
                    print("Removed conditions.loop key")

                # Rename conditions.weather to conditions.weathers
                if 'conditions' in json_data and 'weather' in json_data['conditions']:
                    json_data['conditions']['weathers'] = json_data['conditions']['weather']
                    del json_data['conditions']['weather']
                    print("Renamed conditions.weather to conditions.weathers")
                    
                # Migrate arrays in conditions to objects with an entries field
                if 'conditions' in json_data:
                    for key, value in json_data['conditions'].items():
                        if isinstance(value, list):
                            json_data['conditions'][key] = {'entries': value}
                            print(f"Migrated {key} in conditions to use entries field")
                
                # Save the modified JSON data back to the file
                f.seek(0)
                json.dump(json_data, f, indent=2)
                f.truncate()
        else:
            print("File does not contain a schemaVersion key.")

        print("\n")

# Print files that need manual intervention
if manual_fix:
    print("Files that need manual intervention:")
    for fix_file in manual_fix:
        print(fix_file)

    print("\n")

# Print files that need manual loop check
if manual_loop_check:
    print("Files that need manual loop check:")
    for loop_check_file in manual_loop_check:
        print(loop_check_file)