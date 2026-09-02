<div align="center">

```
 ███████╗ █████╗ ███████╗███████╗██████╗  ██████╗  ██████╗ ███╗   ███╗
 ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔═══██╗██╔═══██╗████╗ ████║
 ███████╗███████║█████╗  █████╗  ██████╔╝██║   ██║██║   ██║██╔████╔██║
 ╚════██║██╔══██║██╔══╝  ██╔══╝  ██╔══██╗██║   ██║██║   ██║██║╚██╔╝██║
 ███████║██║  ██║██║     ███████╗██║  ██║╚██████╔╝╚██████╔╝██║ ╚═╝ ██║
 ╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝
```

### 🛡️ Autonomous Safety Patrol & Environmental Monitoring Rover

**A WiFi-connected autonomous rover that patrols indoor environments, monitors safety conditions, detects anomalies, and provides real-time control and proactive alerts through a web-based mission-control dashboard.**

![Platform](https://img.shields.io/badge/Platform-ESP32-blue?style=for-the-badge&logo=espressif&logoColor=white)
![Connectivity](https://img.shields.io/badge/Connectivity-WiFi-00979D?style=for-the-badge&logo=wifi&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Dashboard](https://img.shields.io/badge/Dashboard-Web%20Based-purple?style=for-the-badge&logo=react&logoColor=white)

</div>

---

## 🚨 Overview

SafeRoom is an autonomous indoor safety patrol system designed to provide **continuous monitoring** of rooms and facilities without requiring a person to be physically present at every location.

The system combines an **ESP32-based mobile rover**, environmental sensors, autonomous patrol logic, WiFi communication, voice/text commands, and a real-time web dashboard.

Instead of simply displaying sensor readings, SafeRoom continuously evaluates the environment and turns abnormal conditions into **actionable safety alerts**.

<div align="center">

| 🏠 Homes | 👵 Elderly-Care | 🏥 Hospital Wards | 🏢 Offices | 🏭 Industrial |
|:---:|:---:|:---:|:---:|:---:|

</div>

---

## 🎯 Problem

Traditional safety monitoring systems are often **stationary**. A fixed sensor can monitor one location, but it cannot physically move between different rooms.

<table>
<tr>
<td width="50%" valign="top">

### ❌ Without SafeRoom
- Important areas may remain unmonitored
- Multiple fixed sensors required per room
- Environmental changes go unnoticed
- Manual inspection is repetitive
- Hard to scale in large facilities
- Raw sensor data ≠ actionable info

</td>
<td width="50%" valign="top">

### ✅ With SafeRoom
- One rover, many rooms
- Continuous autonomous coverage
- Environmental drift caught early
- No repetitive manual walk-throughs
- Scales by adding waypoints, not hardware
- Sensor data → analyzed → alert

</td>
</tr>
</table>

---

## 💡 Solution

SafeRoom uses an autonomous rover that moves between **predefined room waypoints**. While patrolling, the rover collects environmental data such as:

| Sensor | Measures | Why It Matters |
|--------|----------|-----------------|
| 🌡️ Temperature | Ambient room temp | Detects fire risk, HVAC failure, cold exposure |
| 💧 Humidity | Moisture levels | Flags leaks, mold risk, discomfort conditions |
| 🔊 Sound Level | Ambient noise/spikes | Detects distress calls, alarms, unusual activity |
| 📡 Obstacle/Navigation | Distance & positioning | Safe autonomous movement between waypoints |

Data streams over **WiFi** to the monitoring system, and the **web dashboard** turns it into a live safety picture.

---

## 🧠 Key Idea — Data-to-Action Pipeline

```mermaid
flowchart TD
    A[🏢 Facility] --> B[🤖 Autonomous Rover]
    B --> C[📍 Patrol Waypoints]
    C --> D[📡 Environmental Sensors]
    D --> E[⚡ Real-Time Data]
    E --> F[🧮 Safety Analysis Engine]
    F --> G{Anomaly Detected?}
    G -- Yes --> H[🚨 Proactive Alert]
    G -- No --> C
    H --> I[👤 User Response]
    I --> C

    style A fill:#1f2937,stroke:#3b82f6,color:#fff
    style B fill:#1e3a8a,stroke:#60a5fa,color:#fff
    style C fill:#0f766e,stroke:#2dd4bf,color:#fff
    style D fill:#065f46,stroke:#34d399,color:#fff
    style E fill:#78350f,stroke:#fbbf24,color:#fff
    style F fill:#7c2d12,stroke:#fb923c,color:#fff
    style G fill:#7f1d1d,stroke:#f87171,color:#fff
    style H fill:#991b1b,stroke:#ef4444,color:#fff
    style I fill:#312e81,stroke:#818cf8,color:#fff
```

---

## 🏗️ System Architecture

```mermaid
flowchart LR
    subgraph ROVER["🤖 SafeRoom Rover (ESP32)"]
        S1[🌡️ Temp/Humidity Sensor]
        S2[🔊 Sound Sensor]
        S3[📡 Ultrasonic/Obstacle Sensor]
        MC[🧠 ESP32 Microcontroller]
        MOT[⚙️ Motor Driver + Wheels]
        S1 --> MC
        S2 --> MC
        S3 --> MC
        MC --> MOT
    end

    subgraph COMMS["📶 Communication Layer"]
        WIFI[WiFi Module]
    end

    subgraph BACKEND["☁️ Backend / Server"]
        API[REST / WebSocket API]
        DB[(Telemetry & Alert Database)]
        LOGIC[Patrol & Anomaly Logic]
        API --> LOGIC
        LOGIC --> DB
    end

    subgraph DASHBOARD["🖥️ Mission-Control Dashboard"]
        MAP[Live Rover Position]
        TEL[Sensor Telemetry]
        ALERTS[Active Alerts]
        HIST[Patrol History]
        CMD[Voice / Text Commands]
        HEALTH[System Health]
    end

    MC <--> WIFI
    WIFI <--> API
    API --> MAP
    API --> TEL
    API --> ALERTS
    API --> HIST
    CMD --> API
    API --> HEALTH

    style ROVER fill:#0c4a6e,stroke:#38bdf8,color:#fff
    style COMMS fill:#134e4a,stroke:#2dd4bf,color:#fff
    style BACKEND fill:#3730a3,stroke:#818cf8,color:#fff
    style DASHBOARD fill:#581c87,stroke:#c084fc,color:#fff
```

---

## 🔄 Patrol Cycle (Sequence)

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant D as 🖥️ Dashboard
    participant B as ☁️ Backend
    participant R as 🤖 Rover

    U->>D: Start / configure patrol
    D->>B: Send patrol command
    B->>R: Dispatch waypoint route
    loop Each Waypoint
        R->>R: Navigate to waypoint
        R->>R: Read sensors (temp, humidity, sound)
        R->>B: Transmit telemetry (WiFi)
        B->>B: Run safety analysis
        alt Anomaly detected
            B->>D: Push real-time alert
            D->>U: 🚨 Notify user
        else Normal reading
            B->>D: Update live telemetry
        end
    end
    R->>B: Patrol complete
    B->>D: Update patrol history
```

---

## 🚦 Room Safety State Machine

```mermaid
stateDiagram-v2
    [*] --> Monitoring
    Monitoring --> Caution: Threshold drift detected
    Caution --> Alert: Anomaly confirmed
    Caution --> Monitoring: Reading normalizes
    Alert --> Escalated: No user response
    Alert --> Monitoring: User acknowledges & resolves
    Escalated --> Monitoring: Issue resolved
```

---

## 🧩 Feature Highlights

<div align="center">

| Feature | Description |
|---|---|
| 📍 **Autonomous Patrol** | Rover navigates predefined waypoints without manual control |
| 📊 **Live Dashboard** | Real-time rover position, telemetry, and patrol progress |
| 🚨 **Proactive Alerts** | Converts raw sensor data into actionable safety notifications |
| 🗣️ **Voice/Text Commands** | Control and query the rover through natural commands |
| 🕓 **Patrol History** | Full log of past patrols, readings, and triggered alerts |
| ❤️ **System Health** | Battery, connectivity, and sensor status monitoring |

</div>

---

## 🛠️ Tech Stack

<div align="center">

![ESP32](https://img.shields.io/badge/Microcontroller-ESP32-E7352C?style=flat-square&logo=espressif&logoColor=white)
![WiFi](https://img.shields.io/badge/Comm-WiFi%20%2F%20WebSocket-00979D?style=flat-square)
![Sensors](https://img.shields.io/badge/Sensors-Temp%20%7C%20Humidity%20%7C%20Sound%20%7C%20Ultrasonic-4B5563?style=flat-square)
![Web](https://img.shields.io/badge/Dashboard-Web%20App-61DAFB?style=flat-square&logo=react&logoColor=black)
![Backend](https://img.shields.io/badge/Backend-REST%2FWebSocket%20API-000000?style=flat-square&logo=node.js&logoColor=white)

</div>

---

## 📦 Repository Structure (Suggested)

```text
SafeRoom/
├── firmware/            # ESP32 rover code (sensors, navigation, WiFi)
├── backend/             # API, patrol logic, anomaly detection, DB
├── dashboard/           # Web-based mission-control frontend
├── docs/                # Diagrams, architecture notes, setup guides
└── README.md
```

---

## 🌱 Roadmap

- [ ] Core patrol loop + waypoint navigation
- [ ] Environmental sensor integration
- [ ] Real-time WebSocket telemetry to dashboard
- [ ] Anomaly detection & alert engine
- [ ] Voice/text command interface
- [ ] Patrol history & analytics view
- [ ] Multi-rover / multi-facility support

---

<div align="center">

### 🛡️ SafeRoom — because safety shouldn't wait for someone to walk in.

</div>