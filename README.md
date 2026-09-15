📌 **Project Title:** **EyeGuard - Desktop Eye Strain Prevention App**  
📅 **Project Timeline:** **December 2025 – Present [Active Development & Maintenance]**  
🎥 YouTube Demo: TBD  
📦 GitHub Source Code: <https://github.com/IvanSicaja/2025.12.15_RND_software_automation--EyeGuard>  

---

📍 My Personal Profiles ⬇︎  
🎥 Video Portfolio: To be added  
📦 GitHub Profile: <https://github.com/IvanSicaja>  
👔 LinkedIn: <https://www.linkedin.com/in/ivan-si%C4%8Daja-832682222>  
🎥 YouTube: <https://www.youtube.com/@ivan_sicaja>  

---

### 💡 Core Challenge This Project Resolves:

Reducing prolonged uninterrupted screen-work periods through an automated desktop reminder system that schedules configurable work-and-break cycles and delivers timed visual and audio notifications without requiring continuous user interaction.

---

### 🔧 Core Skills Tree Used To Build The Project - Skills and Tech Stack:
*(Project-Specific Structured Overview)*
```text
│
├── Software Engineering
│ ├── Software / Frameworks / Libraries
│ │ ├── Python
│ │ ├── Tkinter
│ │ ├── Pillow
│ │ ├── Pygame
│ │ ├── JSON
│ │ ├── Python threading
│ │ ├── Python Queue
│ │ ├── Python time
│ │ └── ctypes
│ │
│ └── Skills
│   ├── Desktop application development
│   ├── Event-driven application architecture
│   ├── Multithreaded execution
│   ├── Configuration-driven application design
│   ├── Timer & scheduling logic
│   ├── Popup notification workflows
│   ├── Audio notification integration
│   ├── Resource-path management
│   └── Error-tolerant configuration loading
│
├── System Integration Engineering
│ ├── Software / Frameworks / Libraries
│ │ ├── Tkinter
│ │ ├── Pygame Mixer
│ │ ├── Pillow
│ │ ├── Windows User32 API
│ │ └── JSON Configuration
│ │
│ └── Skills
│   ├── GUI-to-timer integration
│   ├── Audio notification integration
│   ├── Image-resource integration
│   ├── Windows display integration
│   ├── Configuration-to-runtime integration
│   ├── Background-thread communication
│   ├── Queue-based UI event handoff
│   └── End-to-end reminder workflow integration
│
├── Automation & Timing
│ ├── Software / Frameworks / Libraries
│ │ ├── Python time
│ │ ├── time.perf_counter
│ │ ├── threading
│ │ └── Queue
│ │
│ └── Skills
│   ├── Automated work-break cycles
│   ├── Configurable timing intervals
│   ├── Multi-stage break milestones
│   ├── Wall-clock cycle alignment
│   ├── Timing drift monitoring
│   ├── Asynchronous notification execution
│   └── Test-mode timing configuration
│
└── Research & Development Engineering
  ├── Software / Frameworks / Libraries
  │ └── Integrated within sections above
  │
  └── Skills
    ├── Desktop reminder workflow design
    ├── Timing-system refinement
    ├── Notification UX development
    ├── Configuration-driven prototyping
    ├── Runtime diagnostics
    └── Technical debugging & iteration
```

---

### 📋 Core System Capabilities - List Only:

- **Automated work-break reminder cycles**
- **Configurable work duration**
- **Multi-stage break milestones**
- **Desktop popup notifications**
- **Visual reminder images**
- **Audio reminder notifications**
- **Configurable popup opacity**
- **Configurable popup messages**
- **Configurable sounds & repeat counts**
- **Configurable font & message color**
- **Wall-clock cycle alignment**
- **Background timer execution**
- **Thread-safe popup queue**
- **Popup fade-in & fade-out effects**
- **Test timing mode**
- **Timing drift diagnostics**
- **Automatic fallback to default configuration**
- **Packaged-application resource path handling**...

---

### 🧠️ How It Works - Core System Capabilities Workflow:

The project combines different software-engineering areas (**desktop automation, timer scheduling, configuration management, multithreading, GUI notifications, audio playback, image-resource handling, Windows integration...**)  
The core of the application is **Python**, **Tkinter**, **Pillow**, **Pygame**, and a configurable JSON-based timing system.

The application is also equipped with:

- **Automated work / break scheduling**
- **Configurable reminder milestones**
- **Visual popup notifications**
- **Audio notifications**
- **Cycle alignment**
- **Test-mode timing**
- **Runtime timing diagnostics**...

**Configuration loading:**  
EyeGuard loads its runtime configuration from `config.json`. If the configuration file is unavailable or cannot be parsed, the application falls back to built-in default values. Configurable parameters include work duration, popup opacity, test mode, cycle alignment, font settings, message colors, notification messages, images, sounds, and individual break-milestone durations.

**Work-break cycle generation:**  
The configured work duration and all configured break milestones are converted into seconds and combined into one complete cycle. Individual `break_end` entries define separate milestones, allowing multiple notifications to be scheduled during a single break sequence.

**Desktop notifications:**  
EyeGuard creates borderless, always-on-top Tkinter popup windows positioned near the bottom-right of the screen. Each popup can contain a custom message and image, while opacity and text styling are controlled through the configuration. Popups use fade-in and fade-out transitions before automatically closing.

**Audio notifications:**  
Notification sounds are played asynchronously through **Pygame Mixer**. Sound filenames and repeat counts are configured independently for each popup event, allowing different sounds to represent different stages of the reminder cycle.

**Threaded runtime architecture:**  
The timer runs in a daemon background thread while Tkinter remains responsible for the main GUI event loop. A thread-safe **Queue** transfers pending popup requests back to the GUI thread, where they are processed periodically without blocking the timing workflow.

**Cycle alignment:**  
When cycle alignment is enabled, EyeGuard calculates the next valid wall-clock boundary based on the complete work-and-break cycle duration. It then determines when the current cycle should have started so the final break milestone aligns with that boundary.

**Aligned first-cycle handling:**  
For an aligned startup, EyeGuard calculates absolute wall-clock targets for work completion and each break milestone. Events that are still in the future are awaited precisely, while already-passed stages can be skipped so the application can join the next valid schedule without restarting the entire cycle.

**Continuous scheduling:**  
After initial alignment, or immediately when alignment is disabled, EyeGuard executes recurring work and break cycles using `time.perf_counter()` for elapsed-time measurements. Each notification fires when its configured target offset is reached.

**Timing diagnostics:**  
The runtime prints expected and actual event timing together with calculated timing drift for work-end events, milestone events, and complete cycles. This provides diagnostic visibility into timer behavior without presenting the implementation as formal automated testing.

**Test mode:**  
A dedicated test mode replaces normal work and break durations with short fixed intervals, allowing reminder sequencing and notification behavior to be exercised without waiting through production-length cycles.

---

### ⚠️ Note:

EyeGuard is a configurable desktop reminder application intended to support structured screen-break habits. It provides timed prompts and workflow automation but does not measure eye strain, diagnose medical conditions, monitor the user's eyes, or provide medical treatment.

---

### 📸 Project Snapshots:

<p align="center">
TBD
</p>

<p align="center">
TBD
</p>

<p align="center">
TBD
</p>

<p align="center">
TBD
</p>

<p align="center">
TBD
</p>

<p align="center">
TBD
</p>

<p align="center">
TBD
</p>

---

### 🎥 Video Demonstration:

<p align="center">
TBD
</p>

---

### 📣 Hashtags Section:

**#EyeGuard #DesktopAutomation #Python #Tkinter #Pygame #Pillow #SoftwareEngineering #SystemIntegration #WorkflowAutomation #DesktopApplication #TimerAutomation #Multithreading #ConfigurationManagement #NotificationSystem #WindowsApplication #ResearchAndDevelopment**

<!-- Required project inputs: -->