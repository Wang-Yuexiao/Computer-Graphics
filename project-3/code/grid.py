from OpenGL.GL import *
import ctypes
import numpy as np
import glm

class Grid:
    def __init__(self, n=10, spacing=1.0):
        """
        Initializes a 3D grid on the XZ plane, centered at the origin.
        Args:
            n (int): Number of lines in each direction (will generate n+1 lines).
            spacing (float): Distance between adjacent lines.
        """
        self.vertex_count = (n + 1) * 4  # 2 lines per direction (X and Z), each with 2 vertices
        self.vao = glGenVertexArrays(1)  # Create Vertex Array Object
        self.vbo = glGenBuffers(1)       # Create Vertex Buffer Object
        vertices = self.create_grid_lines(n, spacing)  # Generate grid line vertex data

        # Upload vertex data to GPU
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        # Set vertex attribute pointer (position only)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
        
        # Unbind VAO to avoid unintended modifications
        glBindVertexArray(0)

    def create_grid_lines(self, n, spacing):
        """
        Generates vertex positions for grid lines.
        Returns:
            numpy.ndarray: Array of 3D vertex positions for GL_LINES.
        """
        lines = []
        start = -n * spacing * 0.5
        end = n * spacing * 0.5
        for i in range(n + 1):
            offset = i * spacing
            # Z-direction line (constant Z, varying X)
            lines.append([start, 0, start + offset])
            lines.append([end, 0, start + offset])
            # X-direction line (constant X, varying Z)
            lines.append([start + offset, 0, start])
            lines.append([start + offset, 0, end])
        return np.array(lines, dtype=np.float32)

    def draw(self, shader_program):
        """
        Renders the grid using the currently active shader.
        Args:
            shader_program: The compiled and active shader program.
        """
        # Pass identity model matrix to avoid interfering with other transformations
        model = glm.mat4(1.0)
        model_loc = glGetUniformLocation(shader_program, "M")
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))

        # Draw the grid using GL_LINES
        glBindVertexArray(self.vao)
        glDrawArrays(GL_LINES, 0, self.vertex_count)
        glBindVertexArray(0)
