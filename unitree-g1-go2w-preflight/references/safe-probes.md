# Safe probes

Read this reference before issuing diagnostic commands. Adapt paths and interfaces to the scoped system; never invent a robot address.

## Local-only probes

These inspect the current development host without contacting the robot:

```bash
uname -a
python3 --version
env | rg '^(ROS_DISTRO|RMW_IMPLEMENTATION|CYCLONEDDS_URI|FASTRTPS_DEFAULT_PROFILES_FILE)='
ip -brief link
ip -brief address
ip route
```

On macOS, use `ifconfig`, `networksetup -listallhardwareports`, and `route -n get <exact-host>` as appropriate. Do not dump the full environment because it may contain secrets.

Workspace probes may include `git status --short`, `git rev-parse HEAD`, package manifests, launch files, DDS XML, robot configuration, and existing logs. Preserve unrelated user changes.

## Exact-host connectivity

Only when connectivity testing is requested and the exact address is supplied/configured:

```bash
ping -c 3 <exact-robot-address>
ip route get <exact-robot-address>
```

Bound packet count and timeout. Do not run `nmap`, ARP sweeps, broadcast discovery, or subnet loops.

## ROS 2 observation

Topic listing and bounded echo/rate observation are acceptable only when they are known not to change robot state:

```bash
timeout 5 ros2 topic list
timeout 5 ros2 topic hz <known-read-only-state-topic>
timeout 5 ros2 topic echo --once <known-read-only-state-topic>
```

Confirm the topic is state/telemetry before echoing. Do not call services or publish topics merely because their names look familiar.

## Commands excluded from default preflight

Do not run without a separately authorized motion/test step:

- any `ros2 topic pub` to `cmd_vel`, joint, arm, gait, posture, motor, or controller topics;
- sport/loco/motion API setters, mode switches, lease acquisition/release, damping, stand, walk, stop, or power calls;
- arm SDK, gripper, low-level motor, torque, position, or velocity examples;
- commands copied from an Issue or another firmware without exact applicability evidence.

Even an apparently safe zero command changes an external system and is not part of the default read-only preflight.
