# Unitree SDK2 and ROS 2 DDS coexistence

Use this reference when ROS 2 and Unitree SDK2 share a host or process and the evidence includes `failed to create domain`, `Precondition Not Met`, missing topics, stale data, or `ClientStub send request error`.

## Freeze before changing anything

Record:

- ROS distribution and `RMW_IMPLEMENTATION`;
- `ROS_DOMAIN_ID` and the Domain passed to Unitree `ChannelFactoryInitialize` / `ChannelFactory::Init`;
- `CYCLONEDDS_URI` source, with peer and interface addresses redacted in shared reports;
- exact Unitree SDK, ROS workspace, and CycloneDDS commits or package versions;
- loaded `ddsc` / `ddscxx` paths and SHA-256 hashes for the affected process;
- whether the observation is participant creation, discovery, fresh data, RPC response, or physical behavior.

Run the bundled collector without `--process-pid` for a configuration-only snapshot. Add the exact affected Linux PID only when inspecting that process is authorized:

```bash
python3 scripts/unitree_sdk2_ros2_dds_snapshot.py \
  --process-pid <exact-pid> \
  --unitree-domain <domain> \
  --format markdown
```

The collector creates no DDS participant, sends no network packet, imports no ROS/Unitree package, and sends no robot command. It intentionally omits hostnames, IP/peer addresses, and non-whitelisted environment variables.

Collector V1.3 preserves these evidence scopes:

- with `--process-pid`, target conclusions use only the target process environment plus explicit CLI overrides; an unreadable target `environ` stays `not_proved` instead of inheriting the collector shell;
- target-owned absolute, relative, and `~` configuration paths and library prefixes are read through `/proc/<pid>/root`, `/proc/<pid>/cwd`, and the captured target HOME; if that namespace evidence is unavailable, the result stays `not_proved`;
- paths reported by `/proc/<pid>/maps` are hashed through the target process root, so a container or chroot does not silently substitute a same-named collector-host file;
- libraries found under configured prefixes are installation candidates and remain separate from `/proc/<pid>/maps` loaded libraries;
- only distinct hashes actually loaded by the target process can produce a loaded-build conflict signal;
- Markdown includes the safe environment, command basename, loaded paths and hashes, configured candidates, parsed/redacted CycloneDDS configuration, and package versions;
- package versions are explicitly scoped to the collector runtime and are not automatically attributed to the target process.

## Interpret in order

| Gate | Evidence needed | What it does not prove |
|---|---|---|
| Configuration loaded | current process config or trace | participant creation |
| Participant created | current return or exception evidence | endpoint discovery |
| Topic discovery | matched endpoints on intended Domain | fresh data |
| Data freshness | bounded age using monotonic timing | RPC response |
| RPC response | request ID, response code, latency, server identity | physical behavior |
| Physical result | separately authorized observation | general safety or production readiness |

Different Domains isolate discovery. The same Domain permits discovery but does not prove binary/config compatibility or RPC success. Two DDS library builds in one process are a conflict risk to investigate, not proof that either library caused the failure.

## Primary evidence

- Unitree SDK2 Python issue 82: https://github.com/unitreerobotics/unitree_sdk2_python/issues/82
- Unitree SDK2 Python issue 118: https://github.com/unitreerobotics/unitree_sdk2_python/issues/118
- Unitree ROS 2 setup: https://github.com/unitreerobotics/unitree_ros2
- CycloneDDS configuration reference: https://cyclonedds.io/docs/cyclonedds/latest/config/index

An independent explanatory page and direct collector download are available at:

https://jixun-robot-lab.guo1988yan.chatgpt.site/unitree-sdk2-ros2-dds-conflict-diagnosis?src=github-unitree-preflight-skill
