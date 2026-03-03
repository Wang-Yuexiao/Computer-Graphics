import glfw
from OpenGL.GL import *
import numpy as np
import glm
import sys

azimuth = 45.0
elevation = 30.0
distance = 10.0
pan_offset = glm.vec3(0.0, 0.0, 0.0)

mouse_prev = None
mode = None  # "orbit", "pan", "zoom"

def init_window(width, height, title):
    if not glfw.init():
        return None
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    window = glfw.create_window(width, height, title, None, None)
    if not window:
        glfw.terminate()
        return None
    glfw.make_context_current(window)
    glfw.set_cursor_pos_callback(window, mouse_callback)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    return window

def compile_shader(source, shader_type):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)
    if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
        raise RuntimeError(glGetShaderInfoLog(shader).decode())
    return shader

def create_shader_program():
    vertex_shader_src = '''
    #version 330 core
    layout(location = 0) in vec3 aPos;
    uniform mat4 MVP;
    void main() {
        gl_Position = MVP * vec4(aPos, 1.0);
    }
    '''
    fragment_shader_src = '''
    #version 330 core
    out vec4 FragColor;
    void main() {
        FragColor = vec4(1.0, 1.0, 1.0, 1.0);
    }
    '''
    vs = compile_shader(vertex_shader_src, GL_VERTEX_SHADER)
    fs = compile_shader(fragment_shader_src, GL_FRAGMENT_SHADER)
    program = glCreateProgram()
    glAttachShader(program, vs)
    glAttachShader(program, fs)
    glLinkProgram(program)
    return program

def create_grid_lines(grid_size=10, step=1):
    lines = []
    for i in range(-grid_size, grid_size + 1, step):
        lines += [[i, 0, -grid_size], [i, 0, grid_size]]
        lines += [[-grid_size, 0, i], [grid_size, 0, i]]
    return np.array(lines, dtype=np.float32)

# ========== 中键控制回调 ==========
def mouse_button_callback(window, button, action, mods):
    global mouse_prev, mode
    if button == glfw.MOUSE_BUTTON_MIDDLE:
        if action == glfw.PRESS:
            shift = glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS
            ctrl = glfw.get_key(window, glfw.KEY_LEFT_CONTROL) == glfw.PRESS
            if shift:
                mode = "pan"
            elif ctrl:
                mode = "zoom"
            else:
                mode = "orbit"
            mouse_prev = glfw.get_cursor_pos(window)
        elif action == glfw.RELEASE:
            mode = None
            mouse_prev = None

def mouse_callback(window, xpos, ypos):
    global azimuth, elevation, distance, pan_offset, mouse_prev
    if mouse_prev is None or mode is None:
        return
    dx = xpos - mouse_prev[0]
    dy = ypos - mouse_prev[1]
    mouse_prev = (xpos, ypos)

    if mode == "orbit":
        azimuth += dx * 0.3
        elevation += dy * 0.3
        elevation = max(-89.9, min(89.9, elevation))
    elif mode == "pan":
        right = glm.vec3(np.sin(np.radians(azimuth - 90)), 0, np.cos(np.radians(azimuth - 90)))
        up = glm.vec3(0, 1, 0)
        pan_offset += (-dx * 0.01) * right + (dy * 0.01) * up
    elif mode == "zoom":
        distance *= (1 - dy * 0.01)
        distance = max(1.0, distance)

def main():
    window = init_window(800, 800, "2019048240")
    if not window:
        print("Failed to create GLFW window")
        sys.exit()

    program = create_shader_program()
    glUseProgram(program)

    grid_vertices = create_grid_lines()
    VAO = glGenVertexArrays(1)
    VBO = glGenBuffers(1)
    glBindVertexArray(VAO)
    glBindBuffer(GL_ARRAY_BUFFER, VBO)
    glBufferData(GL_ARRAY_BUFFER, grid_vertices.nbytes, grid_vertices, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(0)

    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)

        # 计算相机位置
        rad_az = np.radians(azimuth)
        rad_el = np.radians(elevation)
        eye = glm.vec3(
            distance * np.cos(rad_el) * np.sin(rad_az),
            distance * np.sin(rad_el),
            distance * np.cos(rad_el) * np.cos(rad_az)
        ) + pan_offset
        center = pan_offset
        up = glm.vec3(0, 1, 0)

        view = glm.lookAt(eye, center, up)
        projection = glm.perspective(glm.radians(45.0), 1.0, 0.1, 100.0)
        model = glm.mat4(1.0)
        MVP = projection * view * model

        loc = glGetUniformLocation(program, "MVP")
        glUniformMatrix4fv(loc, 1, GL_FALSE, glm.value_ptr(MVP))

        glBindVertexArray(VAO)
        glDrawArrays(GL_LINES, 0, len(grid_vertices))

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()

