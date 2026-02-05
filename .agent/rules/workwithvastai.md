---
trigger: always_on
---

1. Using GitHub Actions Cache method to support incremental builds by only building the "new or different" parts as new layers on GHCR.
2. Project is developped on local Windows 11 with Anaconda3 evn, which env is activated in Antigravity. Project is depolyed on Vast.ai instance which need to pull Docker image from GHCR: ghcr.io/jianshelu/https---github.com-jianshelu-cres_ytdlp:latest.
3. Using SSH to connect instance and need to build SSH tunels to access services due to limited ports are opened on instance.
    Example for vast.ai instance:
        vast.ai instance:
        RTX 3060 CUDA: CUDA: 12.2 VRAM: 12GB
        CPU:XEON E5 1660 V3
        RAM: 48GB
        DISK: 32GB
    SSH connection info:
        Read from: `C:\Users\ruipe\.ssh\config`, Host vastai2s
    Example for IP & Port Info:
        Instance ID: 30950126   
        Machine Copy Port: 57299
        Public IP Address: 1.208.108.242
        Instance Port Range: 57202-57289
        Ip Address Type: Dynamic
        Local IP Addresses: 192.168.0.192 172.17.0.1
        Open Ports:
        1.208.108.242:57269 -> 1111/tcp
        1.208.108.242:57235 -> 22/tcp
        1.208.108.242:57276 -> 3000/tcp
        1.208.108.242:57255 -> 57255/tcp
        1.208.108.242:57202 -> 6006/tcp
        1.208.108.242:57248 -> 7233/tcp
        1.208.108.242:57213 -> 8080/tcp
        1.208.108.242:57278 -> 8081/tcp
        1.208.108.242:57204 -> 8384/tcp
        1.208.108.242:57289 -> 9000/tcp
        1.208.108.242:57218 -> 9001/tcp 
4. During code developping, Using SSH  ControlMaster + ControlPersist to build long connection and using rsync to sync code and debugging with instance's logs. 
5.Sync LLM, whisper,whisperx models with google drive on vast.ai instace management page. models path: 
    /workspace/packages/models/llm, 
    /workspace/packages/models/whisper, 
    /workspace/packages/models/whisperx.
6. Whenever workflows or activities which are boren on GPU should run through Temporal.
7. Append new content to the artifacts instead of overwrite the old one.
8. input, output and related workflow and process should named with suffix of orginal video id. like: https://www.youtube.com/watch?v=u1BAG9bGp74, workflow named as video-u1BAG9bGp74，thumbnails named as thumbnails-u1BAG9bGp74. batch workflow suffix is query keyword, for example, query keyword "Genimi", batch workflow named as batch-Genimi.