#!/usr/bin/env python3
#
# Reads a be_seq.csv file and adds a POV (Point of View) camera flag
# to each sequence for first-person rendering.
#
# Usage:
# python be_add_pov_flag.py <input_csv_path> <output_csv_path>
#
# Example:
# python be_add_pov_flag.py ../../images/test/be_seq.csv ../../images/test/be_seq_pov.csv
#

import sys
from pathlib import Path

def add_pov_flag_to_csv(input_path, output_path):
    """
    Modifies a be_seq.csv file to include a POV flag and renames sequences.
    """
    if not input_path.exists():
        print(f"ERROR: Input file not found at {input_path}", file=sys.stderr)
        return

    modified_lines = []
    with open(input_path, 'r') as f:
        lines = f.readlines()

    # Copy header
    modified_lines.append(lines[0])

    # Process data lines
    for line in lines[1:]:
        parts = line.strip().split(',')
        if len(parts) > 1 and parts[1] == 'Group':
            # This is a Group line, we need to modify its comment
            comment_str = parts[9]
            new_comment_str = comment_str

            # change any camera_hfov to 110
            import re
            new_comment_str = re.sub(r'camera_hfov=\d+(\.\d+)?', 'camera_hfov=110', new_comment_str)
            
            # Also modify the sequence name in the comment
            # Example: "sequence_name=seq_000000" -> "sequence_name=seq_000000_pov"
            new_comment_str = new_comment_str.replace("sequence_name=", "sequence_name_pov=")
            new_comment_str = new_comment_str.replace("sequence_name_pov=", "sequence_name=")
            new_comment_str = new_comment_str.replace("seq_", "seq_pov_")
            
            
            
            new_comment_str = f"{new_comment_str};pov_camera=true"
            
            parts[9] = new_comment_str
            modified_lines.append(",".join(parts) + "\n")
        else:
            # For all other lines (Body, Comment), just copy them
            modified_lines.append(line)

    with open(output_path, 'w') as f:
        f.writelines(modified_lines)
    
    print(f"Successfully created POV sequence file at: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_csv_path> <output_csv_path>", file=sys.stderr)
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    add_pov_flag_to_csv(input_file, output_file)