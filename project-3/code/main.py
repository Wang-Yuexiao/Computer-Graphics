from OpenGL.GL import *
from glfw.GLFW import *
import glm
import ctypes
import numpy as np
import os

# Import custom modules
from camera import OrbitCamera
from bvh_parser import BVHParser
from skeleton import BoxRenderer
from grid import Grid 
from obj_loader import OBJMesh 

# Global rendering mode ("BVH" or "OBJ")
render_mode = "BVH"
obj_mesh = None 

# Window size
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800

# Global scene variables
current_bvh_joint = None
camera = OrbitCamera()
shader = None
box_renderer = None
grid = None

# Animation state
current_frame = 0
is_playing = False
frame_time = 0.033  # ~30 FPS
motion_data = []
scale_factor = 1.0  # Scaling applied to joint offsets and translations

# Dictionary to store joint name → OBJ mesh
obj_dict = {}

def load_joint_obj_dict(joint, folder):
    """
    Recursively load OBJ files for each joint from the given folder.
    Joint names are matched with corresponding .obj filenames.
    """
    name = joint.name.lower()
    obj_file = f"{name}.obj"
    obj_path = os.path.join(folder, obj_file)

    if joint.name.lower() == "endsite":
        return  # Skip end effectors

    if os.path.exists(obj_path):
        try:
            obj_dict[joint.name] = OBJMesh(obj_path)
            print(f"[OK] Loaded mesh for joint: {joint.name}")
        except Exception as e:
            print(f"[ERROR] Failed to load OBJ for {joint.name}: {e}")
    else:
        print(f"[WARN] OBJ not found for joint: {joint.name}")

    # Recurse for all child joints
    for child in joint.children:
        load_joint_obj_dict(child, folder)

def scale_offsets(joint, scale):
    """
    Recursively apply scale factor to joint offsets.
    Useful when BVH files are in centimeter or millimeter units.
    """
    joint.offset = [x * scale for x in joint.offset]
    for child in joint.children:
        scale_offsets(child, scale)

def drop_callback(window, paths):
    """
    GLFW callback for drag-and-drop file loading.
    Parses BVH file, performs auto-scaling if necessary,
    and updates global scene data.
    """
    global current_bvh_joint, motion_data, current_frame, frame_time, scale_factor
    if paths:
        bvh_path = paths[0]
        print("Dropped file:", bvh_path)

        # Parse BVH file
        parser = BVHParser(bvh_path)
        parser.parse()

        # Auto-scale if root offset or motion data are too large
        root_offset_len = glm.length(glm.vec3(parser.root.offset))
        first_frame_root_pos = glm.length(glm.vec3(parser.motion[0][:3]))
        if root_offset_len > 10 or first_frame_root_pos > 10:
            scale_factor = 0.01
            print("[INFO] Detected large unit → applying scale 0.01")
            scale_offsets(parser.root, 0.01)  
        else:
            scale_factor = 1.0
            print("[INFO] Unit appears normalized → no scaling")

        # Update scene state
        current_bvh_joint = parser.root
        motion_data = parser.motion
        frame_time = parser.frame_time
        current_frame = 0

        # Print metadata
        print(f"\n=== BVH File Info ===")
        print(f"Filename: {bvh_path}")
        print(f"Frame count: {parser.num_frames}")
        print(f"FPS: {1.0 / parser.frame_time:.2f}")

        # Count total joints
        def count_joints(joint):
            return 1 + sum(count_joints(child) for child in joint.children)
        total_joints = count_joints(parser.root)
        print(f"Total joints (including root): {total_joints}")

        # List all joint names
        def list_joint_names(joint):
            names = [joint.name]
            for child in joint.children:
                names.extend(list_joint_names(child))
            return names
        joint_names = list_joint_names(parser.root)
        print("Joint names:")
        for name in joint_names:
            print(f" - {name}")
        print("======================\n")


def draw_joint_recursive(joint, parent_pos, shader_program):
    # Skip rendering if the joint is an End Site
    if joint.name.lower() == "endsite":
        return

    # Calculate current joint position by adding offset to parent position
    joint_pos = parent_pos + glm.vec3(joint.offset)

    # Render a box (bone) between parent and current joint
    box_renderer.draw_box(shader_program, parent_pos, joint_pos)

    # Recursively draw all child joints
    for child in joint.children:
        draw_joint_recursive(child, joint_pos, shader_program)

def compile_shader(vertex_src, fragment_src):
    # Compile vertex shader
    vs = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vs, vertex_src)
    glCompileShader(vs)

    # Compile fragment shader
    fs = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fs, fragment_src)
    glCompileShader(fs)

    # Create shader program and link both shaders
    program = glCreateProgram()
    glAttachShader(program, vs)
    glAttachShader(program, fs)
    glLinkProgram(program)

    return program  # Return the compiled shader program

def key_callback(window, key, scancode, action, mods):
    global is_playing, render_mode, obj_mesh, current_bvh_joint, motion_data, frame_time, current_frame

    # Toggle animation playback when spacebar is pressed
    if key == GLFW_KEY_SPACE and action == GLFW_PRESS:
        is_playing = not is_playing

    # Switch to OBJ rendering mode and load associated BVH and OBJ data
    elif key == GLFW_KEY_1 and action == GLFW_PRESS:
        render_mode = "OBJ"
        print("[INFO] Entering OBJ rendering mode...")

        from bvh_parser import BVHParser
        import os

        # Load predefined BVH file
        path = os.path.join("..", "01_01.bvh")
        parser = BVHParser(path)
        parser.parse()

        # Apply scale to normalize the skeleton if needed
        scale_offsets(parser.root, 0.01)

        # Store parsed data in global variables
        current_bvh_joint = parser.root
        motion_data = parser.motion
        frame_time = parser.frame_time
        current_frame = 0

        # Load OBJ meshes for each joint from models folder
        obj_folder = os.path.join("..", "models")
        load_joint_obj_dict(current_bvh_joint, obj_folder)

def draw_joint_with_motion(joint, parent_matrix, shader_program, frame_data, index_ref):
    t = glm.mat4(1.0)  # Initialize translation matrix
    r = glm.mat4(1.0)  # Initialize rotation matrix

    # If this is the root joint, extract global position from motion data
    if joint == current_bvh_joint:
        pos = glm.vec3(0)
        temp_index = index_ref[0]
        for channel in joint.channels:
            ch = channel.upper()
            value = frame_data[temp_index]
            temp_index += 1
            if ch == "XPOSITION":
                pos.x = value
            elif ch == "YPOSITION":
                pos.y = value
            elif ch == "ZPOSITION":
                pos.z = value

        # Apply scaling if position values are abnormally large
        if glm.length(pos) > 10:
            pos *= 0.01

        # Create translation matrix from root position
        t = glm.translate(glm.mat4(1.0), pos)

    # Process rotation channels for all joints
    for channel in joint.channels:
        value = frame_data[index_ref[0]]
        index_ref[0] += 1
        ch = channel.upper()

        if ch in ("XPOSITION", "YPOSITION", "ZPOSITION"):
            continue  # Skip translation (already handled above)
        elif ch == "XROTATION":
            r = r * glm.rotate(glm.mat4(1.0), glm.radians(value), glm.vec3(1, 0, 0))
        elif ch == "YROTATION":
            r = r * glm.rotate(glm.mat4(1.0), glm.radians(value), glm.vec3(0, 1, 0))
        elif ch == "ZROTATION":
            r = r * glm.rotate(glm.mat4(1.0), glm.radians(value), glm.vec3(0, 0, 1))

    # Compute local transformation matrix
    if joint == current_bvh_joint:
        local_matrix = t * r  # Root joint uses global translation
    else:
        offset_matrix = glm.translate(glm.mat4(1.0), glm.vec3(joint.offset))  # Other joints use offset
        local_matrix = offset_matrix * r

    # Compute global transformation matrix
    world_matrix = parent_matrix * local_matrix

    # Draw bone between this joint and its parent (except root)
    if joint != current_bvh_joint:
        parent_pos = glm.vec3(parent_matrix * glm.vec4(0, 0, 0, 1))
        current_pos = glm.vec3(world_matrix * glm.vec4(0, 0, 0, 1))
        box_renderer.draw_box(shader_program, parent_pos, current_pos)

    # Recursively draw all child joints
    for child in joint.children:
        draw_joint_with_motion(child, world_matrix, shader_program, frame_data, index_ref)

def draw_joint_with_obj(joint, parent_matrix, shader_program, frame_data, index_ref):
    # Skip End Site nodes (no visual representation needed)
    if joint.name.lower() == "endsite":
        return

    t = glm.mat4(1.0)  # Translation matrix
    r = glm.mat4(1.0)  # Rotation matrix

    # If this is the root joint, extract translation from motion data
    if joint == current_bvh_joint:
        pos = glm.vec3(0)
        temp_index = index_ref[0]
        for channel in joint.channels:
            ch = channel.upper()
            value = frame_data[temp_index]
            temp_index += 1
            if ch == "XPOSITION":
                pos.x = value
            elif ch == "YPOSITION":
                pos.y = value
            elif ch == "ZPOSITION":
                pos.z = value

        # If root position is too large (unit mismatch), apply scaling
        if glm.length(pos) > 10:
            pos *= 0.01

        # Create translation matrix from root position
        t = glm.translate(glm.mat4(1.0), pos)

    # Parse rotation channels
    for channel in joint.channels:
        value = frame_data[index_ref[0]]
        index_ref[0] += 1
        ch = channel.upper()
        if ch in ("XPOSITION", "YPOSITION", "ZPOSITION"):
            continue  # Skip translation (already handled)
        elif ch == "XROTATION":
            r = r * glm.rotate(glm.mat4(1.0), glm.radians(value), glm.vec3(1, 0, 0))
        elif ch == "YROTATION":
            r = r * glm.rotate(glm.mat4(1.0), glm.radians(value), glm.vec3(0, 1, 0))
        elif ch == "ZROTATION":
            r = r * glm.rotate(glm.mat4(1.0), glm.radians(value), glm.vec3(0, 0, 1))

    # Compute local transformation matrix
    if joint == current_bvh_joint:
        local_matrix = t * r  # Root joint uses translation and rotation
    else:
        offset_matrix = glm.translate(glm.mat4(1.0), glm.vec3(joint.offset))  # Other joints use offset
        local_matrix = offset_matrix * r

    # Compute world transformation by multiplying with parent's matrix
    world_matrix = parent_matrix * local_matrix

    # Apply a fixed scale to all OBJ meshes to match skeleton size
    scale_matrix = glm.scale(glm.mat4(1.0), glm.vec3(0.1))
    model_matrix = world_matrix * scale_matrix

    # Draw the corresponding OBJ mesh if available
    mesh = obj_dict.get(joint.name)
    if mesh:
        mesh.draw(shader_program, model_matrix)

    # Recursively process all child joints
    for child in joint.children:
        draw_joint_with_obj(child, world_matrix, shader_program, frame_data, index_ref)


def main():
    global shader, box_renderer, grid
    global current_frame, is_playing, motion_data, frame_time

    # Initialize GLFW
    if not glfwInit():
        return

    # Configure GLFW to use OpenGL 3.3 Core Profile
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3)
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3)
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE)

    # Create window
    window = glfwCreateWindow(WINDOW_WIDTH, WINDOW_HEIGHT, "2019048240", None, None)
    if not window:
        glfwTerminate()
        return
    glfwMakeContextCurrent(window)

    # Set input callbacks: mouse, drag-and-drop, keyboard, cursor movement
    glfwSetMouseButtonCallback(window, camera.mouse_button_callback)
    glfwSetCursorPosCallback(window, camera.cursor_pos_callback)
    glfwSetDropCallback(window, drop_callback)
    glfwSetKeyCallback(window, key_callback)

    # Shader source code: vertex shader and fragment shader
    vertex_src = '''
    #version 330 core
    layout (location = 0) in vec3 position;
    uniform mat4 MVP;
    uniform mat4 M;
    void main() {
        gl_Position = MVP * M * vec4(position, 1.0);
    }
    '''
    fragment_src = '''
    #version 330 core
    out vec4 FragColor;
    void main() {
        FragColor = vec4(0.8, 0.8, 0.8, 1.0);
    }
    '''

    # Compile and activate shader program
    shader = compile_shader(vertex_src, fragment_src)
    glUseProgram(shader)

    # Create helpers for box rendering and grid display
    box_renderer = BoxRenderer()
    grid = Grid()

    # Enable depth testing for proper 3D rendering
    glEnable(GL_DEPTH_TEST)

    last_time = glfwGetTime()
    begin = True  # Indicates whether animation has started

    # Main rendering loop
    while not glfwWindowShouldClose(window):
        # Clear the screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Update camera projection and view matrices
        projection = glm.perspective(glm.radians(45), WINDOW_WIDTH / WINDOW_HEIGHT, 0.1, 100.0)
        view = camera.update()
        MVP = projection * view

        # Send updated matrices to shader
        glUseProgram(shader)
        glUniformMatrix4fv(glGetUniformLocation(shader, "MVP"), 1, GL_FALSE, glm.value_ptr(MVP))

        # Draw background grid
        grid.draw(shader)

        # Animation timing update
        current_time = glfwGetTime()
        delta_time = current_time - last_time

        # Start animation playback on spacebar press
        if is_playing:
            begin = False

        # Advance animation frame if time has passed
        if is_playing and motion_data:
            if delta_time >= frame_time:
                current_frame = (current_frame + 1) % len(motion_data)
                last_time = current_time

        # Draw skeleton animation or OBJ mesh depending on mode
        if current_bvh_joint and motion_data and not begin and render_mode == "BVH":           
            draw_joint_with_motion(current_bvh_joint, glm.mat4(1.0), shader, motion_data[current_frame], [0])
        elif render_mode == "OBJ" and current_bvh_joint and not begin:
            draw_joint_with_obj(current_bvh_joint, glm.mat4(1.0), shader, motion_data[current_frame], [0])

        # If animation hasn't started, draw static pose (first frame or rest pose)
        if current_bvh_joint and begin:
            if render_mode == "BVH":
                draw_joint_recursive(current_bvh_joint, glm.vec3(0, 0, 0), shader)
            elif render_mode == "OBJ" and motion_data:
                draw_joint_with_obj(current_bvh_joint, glm.mat4(1.0), shader, motion_data[0], [0])

        # Swap buffers and poll input events
        glfwSwapBuffers(window)
        glfwPollEvents()

    # Clean up after window is closed
    glfwTerminate()

# Entry point
if __name__ == "__main__":
    main()



