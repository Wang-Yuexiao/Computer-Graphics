import os
import numpy as np
import glm
from OpenGL.GL import *
import ctypes

class OBJMesh:
    def __init__(self, path):
        """
        Constructor: Loads an OBJ file and initializes OpenGL buffers.
        Args:
            path (str): File path to the .obj model.
        """
        self.vertices = []      # List of vertex positions
        self.indices = []       # List of triangle indices
        self.vao = None         # Vertex Array Object
        self.index_count = 0    # Number of indices to draw
        self.load(path)         # Load data from the OBJ file
        self.setup()            # Upload data to GPU

    def load(self, path):
        """
        Parses the OBJ file to extract vertex and face data.
        Supports faces with 3 or 4 vertices (quads are triangulated).
        """
        v = []  # Temporary list to store vertex positions
        f = []  # Temporary list to store faces (as index lists)

        with open(path, 'r') as file:
            for line in file:
                if line.startswith('v '):
                    # Vertex line: v x y z
                    parts = line.strip().split()
                    v.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif line.startswith('f '):
                    # Face line: f v1 v2 v3 or f v1//n1 v2//n2 ...
                    parts = line.strip().split()
                    face = []
                    for p in parts[1:]:
                        try:
                            idx = int(p.split('/')[0]) - 1  # Convert OBJ index to 0-based
                            face.append(idx)
                        except:
                            continue
                    if len(face) == 3:
                        f.append(face)
                    elif len(face) == 4:
                        # Quad → split into two triangles
                        f.append([face[0], face[1], face[2]])
                        f.append([face[0], face[2], face[3]])

        # Convert to numpy arrays
        self.vertices = np.array(v, dtype=np.float32)
        self.indices = np.array(f, dtype=np.uint32).flatten()
        self.index_count = len(self.indices)
        print(f"[OBJMesh] Loaded {len(self.vertices)} vertices, {len(self.indices)} indices from {path}")

    def setup(self):
        """
        Creates and uploads vertex/index data to GPU buffers (VAO, VBO, EBO).
        """
        self.vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        ebo = glGenBuffers(1)

        glBindVertexArray(self.vao)

        # Upload vertex data
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)

        # Upload index data
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.indices.nbytes, self.indices, GL_STATIC_DRAW)

        # Enable position attribute (location = 0)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))

        # Unbind VAO to avoid accidental modification
        glBindVertexArray(0)

    def draw(self, shader_program, model_matrix):
        """
        Renders the loaded mesh with the given shader and model transform.
        Args:
            shader_program: The OpenGL shader program in use.
            model_matrix: glm.mat4 model transformation matrix.
        """
        # Set model matrix uniform
        glUniformMatrix4fv(glGetUniformLocation(shader_program, "M"), 1, GL_FALSE, glm.value_ptr(model_matrix))

        # Bind VAO and draw indexed triangles
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.index_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)