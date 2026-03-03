# obj_loader.py
import numpy as np
from OpenGL.GL import *
import glm
import ctypes

class ObjModel:
    def __init__(self, filename, offset_x=0.0):
        self.filename = filename
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.vertex_count = 0
        self.model_matrix = self.load_obj(filename, offset_x)

    def load_obj(self, filename, offset_x):
        vertices = []
        normals = []
        faces = []

        with open(filename, 'r') as f:
            for line in f:
                if line.startswith('v '):
                    vertices.append([float(x) for x in line.strip().split()[1:]])
                elif line.startswith('vn '):
                    normals.append([float(x) for x in line.strip().split()[1:]])
                elif line.startswith('f '):
                    face = []
                    tokens = line.strip().split()[1:]
                    for tok in tokens:
                        v_parts = tok.split('//')  # v//vn 格式
                        v_idx = int(v_parts[0]) - 1
                        n_idx = int(v_parts[1]) - 1 if len(v_parts) > 1 else 0
                        face.append((v_idx, n_idx))
                    faces.append(face)

        # 输出统计信息
        print(f"\n[Loaded] {filename}")
        print(f"Total faces: {len(faces)}")
        print(f"Triangles: {sum(1 for f in faces if len(f) == 3)}")
        print(f"Quads:     {sum(1 for f in faces if len(f) == 4)}")
        print(f"Ngons:     {sum(1 for f in faces if len(f) > 4)}")

        final_vertices = []
        for face in faces:
            if len(face) < 3:
                continue
            # 三角化
            for i in range(1, len(face) - 1):
                for idx in [0, i, i + 1]:
                    v_idx, n_idx = face[idx]
                    pos = vertices[v_idx]
                    norm = normals[n_idx] if normals else [0, 1, 0]
                    final_vertices += pos + norm

        self.vertex_count = len(final_vertices) // 6
        vertex_array = np.array(final_vertices, dtype=np.float32)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertex_array.nbytes, vertex_array, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(12))

        glBindVertexArray(0)

        # 模型偏移
        model_matrix = np.identity(4, dtype=np.float32)
        model_matrix[0][3] = offset_x
        return model_matrix

    def draw(self, shader_program, view, projection):
        model = glm.mat4(*self.model_matrix.T.flatten())
        glUniformMatrix4fv(glGetUniformLocation(shader_program, "u_model"), 1, GL_FALSE, glm.value_ptr(model))
        glUniformMatrix4fv(glGetUniformLocation(shader_program, "u_view"), 1, GL_FALSE, glm.value_ptr(view))
        glUniformMatrix4fv(glGetUniformLocation(shader_program, "u_projection"), 1, GL_FALSE, glm.value_ptr(projection))

        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)

