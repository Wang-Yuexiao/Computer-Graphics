class Joint:
    def __init__(self, name, offset, channels=None):
        self.name = name                          # Joint name
        self.offset = offset                      # Offset from parent joint [x, y, z]
        self.channels = channels or []            # List of channel types (e.g. Xposition, Zrotation)
        self.children = []                        # List of child joints
        self.channel_order = []                   # (Optional) channel order, not used here
        self.channel_indices = []                 # (Optional) indices in the motion data

    def __repr__(self):
        return f"Joint({self.name}, offset={self.offset}, children={len(self.children)})"


class BVHParser:
    def __init__(self, filepath):
        self.filepath = filepath          # Path to the .bvh file
        self.lines = []                   # All lines in the file (after reading)
        self.index = 0                    # Current line index during parsing
        self.root = None                  # Root joint of the skeleton hierarchy
        self.motion = []                  # List of all motion frames
        self.frame_time = 0.0             # Time between each frame
        self.num_frames = 0               # Total number of frames in the motion

    def parse(self):
        # Read and clean all lines
        with open(self.filepath, 'r') as f:
            self.lines = [line.strip() for line in f.readlines()]
        self.index = 0

        # Expect and skip "HIERARCHY" line
        assert self.lines[self.index] == "HIERARCHY"
        self.index += 1

        # Parse the joint hierarchy starting from root
        self.root = self._parse_joint()

        # Expect and skip "MOTION" line
        assert self.lines[self.index] == "MOTION"
        self.index += 1

        # Parse motion metadata: number of frames and frame time
        self.num_frames = int(self.lines[self.index].split(":")[1])
        self.index += 1
        self.frame_time = float(self.lines[self.index].split(":")[1])
        self.index += 1

        # Parse all motion frames
        self.motion = []
        while self.index < len(self.lines):
            if self.lines[self.index]:  # skip empty lines
                frame_data = list(map(float, self.lines[self.index].split()))
                self.motion.append(frame_data)
            self.index += 1
            
    def _parse_joint(self):
        line = self.lines[self.index]
        # Detect joint name, "EndSite" if it’s the terminal node
        joint_name = "EndSite" if line.startswith("End Site") else line.split()[1]
        self.index += 1

        # Joint block must start with {
        assert self.lines[self.index] == "{"
        self.index += 1

        offset = [0.0, 0.0, 0.0]     # Default offset
        channels = []               # Channel list (e.g., Xrotation, Yrotation, etc.)
        children = []               # List of child joints

        # Parse joint body
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line.startswith("OFFSET"):
                offset = list(map(float, line.split()[1:]))  # Parse offset
                self.index += 1
            elif line.startswith("CHANNELS"):
                parts = line.split()
                channels = parts[2:]                         # Skip "CHANNELS n"
                self.index += 1
            elif line.startswith("JOINT") or line.startswith("End Site"):
                # Recursively parse children
                child = self._parse_joint()
                children.append(child)
            elif line == "}":
                # End of joint block
                self.index += 1
                break
            else:
                # Ignore unknown lines
                self.index += 1

        # Construct and return the joint
        joint = Joint(joint_name, offset, channels)
        joint.children = children
        return joint

