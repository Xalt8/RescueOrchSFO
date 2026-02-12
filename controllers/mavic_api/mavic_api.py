"""Mavic controller that polls Rescue Command Center API and applies commands."""

import json
import urllib.request
import urllib.error
from controller import Robot, Camera

DEFAULT_API = "http://127.0.0.1:8000"

# Camera sampling: 128ms (~8 fps) - getImageArray is slower than getImage
CAMERA_SAMPLE_PERIOD_MS = 128


# def fetch_command(api_url):
#     try:
#         req = urllib.request.Request(f"{api_url}/mavic/command")
#         with urllib.request.urlopen(req, timeout=0.5) as resp:
#             return json.loads(resp.read().decode())
#     except (urllib.error.URLError, OSError, json.JSONDecodeError):
#         return None

def fetch_command(api_url):
    try:
        req = urllib.request.Request(f"{api_url}/mavic/command")
        print(f"[mavic_api] Polling {api_url}/mavic/command")  # DEBUG
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            cmd = json.loads(resp.read().decode())
            print(f"[mavic_api] Received: {cmd}")  # DEBUG
            return cmd
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f"[mavic_api] Connection error: {e}")  # DEBUG
        return None


def send_camera_frame(api_url, data, width, height):
    try:
        url = f"{api_url}/mavic/camera/frame?width={width}&height={height}"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/octet-stream")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            pass
    except (urllib.error.URLError, OSError):
        pass


def main():
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())

    # Devices
    imu = robot.getDevice("inertial unit")
    imu.enable(timestep)
    gps = robot.getDevice("gps")
    gps.enable(timestep)
    gyro = robot.getDevice("gyro")
    gyro.enable(timestep)
    camera_roll = robot.getDevice("camera roll")
    camera_pitch = robot.getDevice("camera pitch")

    # Camera for live feed - find device with getImageArray (Camera)
    camera = None
    for i in range(robot.getNumberOfDevices()):
        dev = robot.getDeviceByIndex(i)
        if dev and hasattr(dev, "getImageArray"):
            camera = dev
            break
    if camera:
        camera.enable(CAMERA_SAMPLE_PERIOD_MS)
    front_left_led = robot.getDevice("front left led")
    front_right_led = robot.getDevice("front right led")

    front_left = robot.getDevice("front left propeller")
    front_right = robot.getDevice("front right propeller")
    rear_left = robot.getDevice("rear left propeller")
    rear_right = robot.getDevice("rear right propeller")

    for m in [front_left, front_right, rear_left, rear_right]:
        m.setPosition(float("inf"))
        m.setVelocity(1.0)

    # Constants (from mavic2pro C controller)
    K_VERTICAL_THRUST = 68.5
    K_VERTICAL_OFFSET = 0.6
    K_VERTICAL_P = 3.0
    K_ROLL_P = 50.0
    K_PITCH_P = 30.0

    # Get API URL from controller args (optional)
    try:
        args = robot.getControllerArguments()
        api_url = (args[0] if isinstance(args, (list, tuple)) and args else args or DEFAULT_API) or DEFAULT_API
    except Exception:
        api_url = DEFAULT_API

    target_altitude = 1.0
    poll_counter = 0
    cmd = None
    api_connected = False
    camera_counter = 0

    while robot.step(timestep) != -1:
        t = robot.getTime()
        poll_counter += 1

        # Poll API every ~32ms for responsive control
        if poll_counter >= 4:
            poll_counter = 0
            cmd = fetch_command(api_url)
            if cmd and not api_connected:
                api_connected = True
                print("[mavic_api] Connected to Rescue Command Center API")
            if cmd:
                if cmd.get("flying"):
                    target_altitude = cmd.get("target_altitude", target_altitude)
                data = cmd.get("data", {})
                if cmd.get("type") == "velocity":
                    target_altitude = target_altitude + 0.02 * data.get("vertical", 0)
                    target_altitude = max(0.0, min(50.0, target_altitude))

        data = cmd.get("data", {}) if cmd else {}
        roll_disturbance = data.get("roll", 0)
        pitch_disturbance = data.get("pitch", 0)
        yaw_disturbance = data.get("yaw", 0)

        roll, pitch, _ = imu.getRollPitchYaw()
        altitude = gps.getValues()[2]
        roll_vel, pitch_vel, _ = gyro.getValues()

        front_left_led.set(int(t) % 2)
        front_right_led.set(1 - int(t) % 2)

        # Send camera frame periodically (use getImageArray for reliable RGB format)
        if camera:
            camera_counter += 1
            if camera_counter * timestep >= CAMERA_SAMPLE_PERIOD_MS:
                camera_counter = 0
                arr = camera.getImageArray()
                if arr:
                    w, h = camera.getWidth(), camera.getHeight()
                    # Convert [x][y][r,g,b] to flat RGB bytes
                    data = bytearray(w * h * 3)
                    for x in range(w):
                        for y in range(h):
                            r, g, b = arr[x][y][0], arr[x][y][1], arr[x][y][2]
                            idx = (y * w + x) * 3
                            data[idx : idx + 3] = bytes([r, g, b])
                    send_camera_frame(api_url, bytes(data), w, h)

        # Camera roll/pitch limits: roll [-0.5, 0.5], pitch [-0.5, 1.7] per proto
        camera_roll.setPosition(max(-0.5, min(0.5, -0.115 * roll_vel)))
        camera_pitch.setPosition(max(-0.5, min(1.7, -0.1 * pitch_vel)))

        def clamp(v, lo, hi):
            return max(lo, min(hi, v))

        roll_in = K_ROLL_P * clamp(roll, -1, 1) + roll_vel + roll_disturbance
        pitch_in = K_PITCH_P * clamp(pitch, -1, 1) + pitch_vel + pitch_disturbance
        yaw_in = yaw_disturbance
        alt_diff = clamp(target_altitude - altitude + K_VERTICAL_OFFSET, -1, 1)
        vertical_in = K_VERTICAL_P * (alt_diff ** 3)

        fl = K_VERTICAL_THRUST + vertical_in - roll_in + pitch_in - yaw_in
        fr = K_VERTICAL_THRUST + vertical_in + roll_in + pitch_in + yaw_in
        rl = K_VERTICAL_THRUST + vertical_in - roll_in - pitch_in + yaw_in
        rr = K_VERTICAL_THRUST + vertical_in + roll_in - pitch_in - yaw_in

        front_left.setVelocity(fl)
        front_right.setVelocity(-fr)
        rear_left.setVelocity(-rl)
        rear_right.setVelocity(rr)


if __name__ == "__main__":
    main()
