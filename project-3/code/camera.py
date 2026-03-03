import glm
import glfw

class OrbitCamera:
    def __init__(self):
        # Camera distance from the target point
        self.distance = 5.0

        # Azimuth and elevation angles in radians (used for orbiting)
        self.azimuth = glm.radians(45)     # Horizontal angle
        self.elevation = glm.radians(30)   # Vertical angle

        # Target point the camera looks at
        self.target = glm.vec3(0, 0, 0)

        # Previous mouse cursor positions
        self.prev_x = 0
        self.prev_y = 0

        # Current mouse action ('ORBIT', 'PAN', or 'ZOOM')
        self.mouse_action = None

    def update(self):
        """
        Calculates and returns the view matrix based on current orbit parameters.
        """
        # Convert spherical coordinates to Cartesian coordinates for camera eye position
        eye = glm.vec3(
            self.distance * glm.cos(self.elevation) * glm.sin(self.azimuth),
            self.distance * glm.sin(self.elevation),
            self.distance * glm.cos(self.elevation) * glm.cos(self.azimuth)
        ) + self.target

        # Return the view matrix using glm.lookAt
        return glm.lookAt(eye, self.target, glm.vec3(0, 1, 0))

    def mouse_button_callback(self, window, button, action, mods):
        """
        Handles mouse button events to determine the intended camera action
        based on ALT + (optional SHIFT/CTRL) key combinations.
        """
        if action == glfw.PRESS:
            if mods & glfw.MOD_ALT:
                if button == glfw.MOUSE_BUTTON_LEFT:
                    if mods & glfw.MOD_SHIFT:
                        self.mouse_action = 'PAN'     # ALT + SHIFT + LMB → Pan
                    elif mods & glfw.MOD_CONTROL:
                        self.mouse_action = 'ZOOM'    # ALT + CTRL + LMB → Zoom
                    else:
                        self.mouse_action = 'ORBIT'   # ALT + LMB → Orbit
            # Store current mouse position
            self.prev_x, self.prev_y = glfw.get_cursor_pos(window)
        elif action == glfw.RELEASE:
            # Stop camera manipulation on mouse release
            self.mouse_action = None

    def cursor_pos_callback(self, window, xpos, ypos):
        """
        Handles cursor movement to perform camera transformation
        based on the current mouse action (orbit, pan, or zoom).
        """
        # Calculate mouse delta movement
        dx = xpos - self.prev_x
        dy = ypos - self.prev_y
        self.prev_x, self.prev_y = xpos, ypos

        if self.mouse_action == 'ORBIT':
            # Rotate around target
            self.azimuth -= glm.radians(dx * 0.5)
            self.elevation += glm.radians(dy * 0.5)
            # Clamp elevation to avoid flipping
            self.elevation = glm.clamp(self.elevation, glm.radians(-89), glm.radians(89))

        elif self.mouse_action == 'PAN':
            # Translate target left/right and up/down
            right = glm.vec3(glm.sin(self.azimuth - glm.pi()/2), 0, glm.cos(self.azimuth - glm.pi()/2))
            up = glm.vec3(0, 1, 0)
            self.target += right * (dx * 0.01)
            self.target += up * (-dy * 0.01)

        elif self.mouse_action == 'ZOOM':
            # Adjust distance from target (zoom in/out)
            self.distance *= 1.0 + dy * 0.01
            self.distance = max(0.1, self.distance)  # Prevent zooming too close