# main.py
import glfw
from OpenGL.GL import *
from OpenGL.GL.shaders import compileShader, compileProgram
import numpy as np
import glm
import ctypes
from camera import Camera
from obj_loader import ObjModel

# === Shader Sources ===
VERT_SHADER_SRC = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;

out vec3 FragPos;
out vec3 Normal;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;

void main() {
    FragPos = vec3(u_model * vec4(aPos, 1.0));
    Normal = mat3(transpose(inverse(u_model))) * aNormal;

    gl_Position = u_projection * u_view * vec4(FragPos, 1.0);
}
"""

FRAG_SHADER_SRC = """
#version 330 core
in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform vec3 lightPos;
uniform vec3 viewPos;

void main() {
    vec3 ambientColor = vec3(0.1);
    vec3 diffuseColor = vec3(0.6, 0.6, 0.8);
    vec3 specularColor = vec3(1.0);
    float shininess = 32.0;

    vec3 lightColor = vec3(1.0);

    vec3 ambient = ambientColor * lightColor;

    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diffuseColor * diff * lightColor;

    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), shininess);
    vec3 specular = specularColor * spec * lightColor;

    vec3 result = ambient + diffuse + specular;
    FragColor = vec4(result, 1.0);
}
"""

# === Globals ===
camera = Camera()
is_dragging = False
mode = None
models = []

# === Input Callbacks ===
def mouse_button_callback(window, button, action, mods):
    global is_dragging, mode
    if button == glfw.MOUSE_BUTTON_LEFT:
        if action == glfw.PRESS:
            is_dragging = True
            if mods & glfw.MOD_ALT and mods & glfw.MOD_SHIFT:
                mode = "pan"
            elif mods & glfw.MOD_ALT and mods & glfw.MOD_CONTROL:
                mode = "zoom"
            elif mods & glfw.MOD_ALT:
                mode = "orbit"
            else:
                mode = None
        elif action == glfw.RELEASE:
            is_dragging = False
            mode = None

def cursor_pos_callback(window, xpos, ypos):
    global camera
    if is_dragging and mode:
        dx = xpos - camera.last_x
        dy = ypos - camera.last_y
        if mode == "orbit":
            camera.orbit(dx, dy)
        elif mode == "pan":
            camera.pan(dx, dy)
        elif mode == "zoom":
            camera.zoom(dy)
    camera.last_x = xpos
    camera.last_y = ypos

def drop_callback(window, paths):
    global models
    offset = len(models) * 2.0
    for path in paths:
        try:
            model = ObjModel(path, offset)
            models.append(model)
        except Exception as e:
            print(f"Failed to load {path}: {e}")
    

# === Grid for reference ===
def create_grid():
    lines = []
    for i in range(-10, 11):
        lines += [i, 0, -10, i, 0, 10]
        lines += [-10, 0, i, 10, 0, i]
    return np.array(lines, dtype=np.float32)

def create_grid_vao():
    grid_vertices = create_grid()
    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, grid_vertices.nbytes, grid_vertices, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
    glBindVertexArray(0)
    return vao, len(grid_vertices) // 3

# === Shader Compile ===
def compile_shader_program():
    return compileProgram(
        compileShader(VERT_SHADER_SRC, GL_VERTEX_SHADER),
        compileShader(FRAG_SHADER_SRC, GL_FRAGMENT_SHADER)
    )

# === Main ===
def main():
    if not glfw.init():
        return
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    window = glfw.create_window(800, 800, "OBJ Viewer", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    glfw.set_cursor_pos_callback(window, cursor_pos_callback)
    glfw.set_drop_callback(window, drop_callback)

    glEnable(GL_DEPTH_TEST)

    shader = compile_shader_program()
    grid_vao, grid_count = create_grid_vao()

    while not glfw.window_should_close(window):
        glClearColor(0.05, 0.05, 0.05, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(shader)

        projection = glm.perspective(glm.radians(45.0), 1.0, 0.1, 100.0)
        view = camera.get_view_matrix()

        # 设置光照相关 uniform
        light_pos = glm.vec3(5.0, 5.0, 5.0)
        view_pos = camera.get_position()
        glUniform3fv(glGetUniformLocation(shader, "lightPos"), 1, glm.value_ptr(light_pos))
        glUniform3fv(glGetUniformLocation(shader, "viewPos"), 1, glm.value_ptr(view_pos))

        # 绘制网格
        model = glm.mat4(1.0)
        glUniformMatrix4fv(glGetUniformLocation(shader, "u_model"), 1, GL_FALSE, glm.value_ptr(model))
        glUniformMatrix4fv(glGetUniformLocation(shader, "u_view"), 1, GL_FALSE, glm.value_ptr(view))
        glUniformMatrix4fv(glGetUniformLocation(shader, "u_projection"), 1, GL_FALSE, glm.value_ptr(projection))
        glBindVertexArray(grid_vao)
        glDrawArrays(GL_LINES, 0, grid_count)

        # 绘制模型
        for m in models:
            m.draw(shader, view, projection)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()
