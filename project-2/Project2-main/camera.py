# camera.py
import glm
import math

class Camera:
    def __init__(self):
        self.radius = 5.0  # 初始相机与原点距离
        self.theta = 0.0   # 水平方向角度
        self.phi = 0.0     # 垂直方向角度
        self.target = glm.vec3(0, 0, 0)
        self.last_x = 0
        self.last_y = 0
        self.pan_offset = glm.vec3(0)

    def orbit(self, dx, dy):
        self.theta += dx * 0.01
        self.phi += dy * 0.01
        self.phi = max(-math.pi / 2 + 0.01, min(math.pi / 2 - 0.01, self.phi))

    def zoom(self, dy):
        self.radius *= (1.0 + dy * 0.01)
        self.radius = max(0.1, self.radius)

    def pan(self, dx, dy):
        right = glm.normalize(glm.cross(self.get_direction(), glm.vec3(0, 1, 0)))
        up = glm.normalize(glm.cross(right, self.get_direction()))
        self.pan_offset += -right * dx * 0.01 + up * dy * 0.01

    def get_position(self):
        x = self.radius * math.cos(self.phi) * math.sin(self.theta)
        y = self.radius * math.sin(self.phi)
        z = self.radius * math.cos(self.phi) * math.cos(self.theta)
        return glm.vec3(x, y, z) + self.target + self.pan_offset

    def get_direction(self):
        return glm.normalize(self.target + self.pan_offset - self.get_position())

    def get_view_matrix(self):
        return glm.lookAt(self.get_position(), self.target + self.pan_offset, glm.vec3(0, 1, 0))
