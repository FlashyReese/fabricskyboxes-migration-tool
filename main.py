#!/usr/bin/env python3
import os
import json

import glob

# Check if an argument is provided
import sys

if len(sys.argv) < 2:
    print("Usage: {} directory_path".format(sys.argv[0]))
    sys.exit(1)

# Store the directory path from the argument
directory = sys.argv[1]

# List to store files that need manual intervention
manual_fix = []

# Find all JSON files under exampledirectory/assets/*/sky/
json_files = glob.glob(os.path.join(directory, "assets", "*", "sky", "**", "*.json"), recursive=True)

for file in json_files:
    with open(file, 'r+') as f:
        try:
            json_data = json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON in file:", file)
            continue

        # Check if the file contains a schemaVersion key
        if 'schemaVersion' in json_data:
            # Check and remove conditions.loop key if present
            if 'conditions' in json_data and 'loop' in json_data['conditions']:
                del json_data['conditions']['loop']
                print("Removed conditions.loop key from", file)

            # Example condition to change schemaVersion based on its value
            current_version = json_data['schemaVersion']
            current_type = json_data.get('type', '')

            if current_version == 2:
                # Update the schemaVersion to a new value
                json_data['schemaVersion'] = 1
                print("Updated schemaVersion in", file, "from", current_version, "to 1")

                if current_type == "single-sprite-square-textured":
                    json_data['type'] = "square-textured"
                    print("Updated type in", file, "from", current_type, "to square-textured")
                elif current_type == "multi-texture":
                    json_data['type'] = "multi-textured"
                    print("Updated type in", file, "from", current_type, "to multi-textured")

                    # Rename uvRanges to uvRange
                    if 'uvRanges' in json_data:
                        json_data['uvRange'] = json_data['uvRanges']
                        del json_data['uvRanges']
                        print("Renamed uvRanges to uvRange in", file)

                    # Rename animations to animatableTextures
                    if 'animations' in json_data:
                        json_data['animatableTextures'] = json_data['animations']
                        del json_data['animations']
                        print("Renamed animations to animatableTextures in", file)
                elif current_type not in ["monocolor", "overworld", "end"]:
                    manual_fix.append(file)

                # Migrate properties.fade object if present
                if 'properties' in json_data and 'fade' in json_data['properties'] \
                        and all(key in json_data['properties']['fade'] for key in ['startFadeIn', 'endFadeIn', 'startFadeOut', 'endFadeOut']):
                    fade_data = json_data['properties']['fade']
                    startFadeIn = fade_data['startFadeIn']
                    endFadeIn = fade_data['endFadeIn']
                    startFadeOut = fade_data['startFadeOut']
                    endFadeOut = fade_data['endFadeOut']
                    json_data['properties']['fade']['keyFrames'] = {
                        startFadeIn: 0.0,
                        endFadeIn: 1.0,
                        startFadeOut: 1.0,
                        endFadeOut: 0.0
                    }
                    del json_data['properties']['fade']['startFadeIn']
                    del json_data['properties']['fade']['endFadeIn']
                    del json_data['properties']['fade']['startFadeOut']
                    del json_data['properties']['fade']['endFadeOut']
                    print("Migrated properties.fade in", file)

                # Save the modified JSON data back to the file
                f.seek(0)
                json.dump(json_data, f, indent=2)
                f.truncate()
        else:
            print("File", file, "does not contain a schemaVersion key.")

# Print files that need manual intervention
if manual_fix:
    print("Files that need manual intervention:")
    for fix_file in manual_fix:
        print(fix_file)