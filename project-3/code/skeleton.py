from OpenGL.GL import *
import glm
import numpy as np
import ctypes

class BoxRenderer:
    def __init__(self):
        """
        Constructor: Initializes the box renderer by creating a VAO for a unit cube.
        """
        self.vao, self.index_count = self.create_box_vao()

    def create_box_vao(self):
        """
        Creates a vertex array object (VAO) for a unit box centered at the origin
        and aligned along the +Z direction. The box has a height of 1.0 (from -0.5 to +0.5)
        and cross-sectional dimensions of 0.1 × 0.1.

        Returns:
            vao: OpenGL Vertex Array Object ID
            index_count: Total number of indices to draw
        """
        # Define vertex positions for a unit cube
        vertices = [
            # Front face (z = 0.5)
            -0.05, -0.05,  0.5,  # 0
             0.05, -0.05,  0.5,  # 1
             0.05,  0.05,  0.5,  # 2
            -0.05,  0.05,  0.5,  # 3
            # Back face (z = -0.5)
            -0.05, -0.05, -0.5,  # 4
             0.05, -0.05, -0.5,  # 5
             0.05,  0.05, -0.5,  # 6
            -0.05,  0.05, -0.5   # 7
        ]

        # Define index buffer (two triangles per face, 6 faces)
        indices = [
            0, 1, 2, 2, 3, 0,  # Front face
            4, 5, 6, 6, 7, 4,  # Back face
            0, 1, 5, 5, 4, 0,  # Bottom face
            3, 2, 6, 6, 7, 3,  # Top face
            1, 2, 6, 6, 5, 1,  # Right face
            0, 3, 7, 7, 4, 0   # Left face
        ]

        # Generate VAO, VBO, EBO
        vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        ebo = glGenBuffers(1)

        # Bind VAO and set up vertex data
        glBindVertexArray(vao)

        # Upload vertex data
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, np.array(vertices, dtype=np.float32), GL_STATIC_DRAW)

        # Upload index data
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, np.array(indices, dtype=np.uint32), GL_STATIC_DRAW)

        # Enable vertex attribute (position)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))

        return vao, len(indices)

    def draw_box(self, shader_program, from_pos, to_pos):
        """
        Renders a transformed box between two 3D points using the unit cube.

        Args:
            shader_program: The OpenGL shader program to use
            from_pos: glm.vec3, start position of the bone/joint
            to_pos: glm.vec3, end position of the bone/joint
        """
        glUseProgram(shader_program)

        # Compute direction and length of the bone
        direction = glm.normalize(to_pos - from_pos)
        length = glm.length(to_pos - from_pos)
        if length < 1e-5:
            return  # Skip drawing if bone is too short

        # Compute rotation from +Z to direction vector
        up = glm.vec3(0, 0, 1)
        axis = glm.cross(up, direction)
        angle = glm.acos(glm.clamp(glm.dot(up, direction), -1.0, 1.0))

        # If the direction is almost aligned with +Z, skip rotation
        if glm.length(axis) < 1e-5:
            rotation = glm.mat4(1.0)
        else:
            rotation = glm.rotate(glm.mat4(1.0), angle, glm.normalize(axis))

        # Scale the unit box along z-axis to match length
        scale = glm.scale(glm.mat4(1.0), glm.vec3(1, 1, length))

        # Translate to the midpoint between from_pos and to_pos
        translation = glm.translate(glm.mat4(1.0), (from_pos + to_pos) * 0.5)

        # Final model transformation matrix
        model = translation * rotation * scale

        # Upload model matrix to shader
        model_loc = glGetUniformLocation(shader_program, "M")
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))

        # Bind and draw the cube
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.index_count, GL_UNSIGNED_INT, None)