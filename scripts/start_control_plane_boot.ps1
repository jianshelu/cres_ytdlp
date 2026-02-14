$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $RepoRoot ".tmp\control-plane"
$StartupLog = Join-Path $LogDir "startup.log"
$TemporalExe = "D:\soft\temporal.exe"
$MinioExe = "D:\soft\minio\minio.exe"
$CondaBat = "D:\Miniconda3\condabin\conda.bat"
$WorkerPython = "D:\Miniconda3\envs\cres\python.exe"
$MinioDataDir = "D:\minio-data"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $StartupLog -Value "[$ts] $Message"
}

function Read-EnvFile {
    param([string]$Path)
    $envMap = @{}
    if (-not (Test-Path $Path)) {
        return $envMap
    }

    foreach ($line in Get-Content -Path $Path) {
        $text = $line.Trim()
        if (-not $text -or $text.StartsWith("#")) {
            continue
        }

        $parts = $text -split "=", 2
        if ($parts.Count -ne 2) {
            continue
        }

        $key = $parts[0].Trim().TrimStart([char]0xFEFF)
        $value = $parts[1].Trim().Trim("'`"")
        $envMap[$key] = $value
    }

    return $envMap
}

function Test-PortListening {
    param([int]$Port)
    try {
        return $null -ne (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1)
    }
    catch {
        return $false
    }
}

function Wait-Port {
    param(
        [int]$Port,
        [int]$TimeoutSeconds
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening -Port $Port) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Get-WorkerProcess {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "src\.backend\.worker" } |
        Select-Object -First 1
}

function Wait-Worker {
    param([int]$TimeoutSeconds)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($null -ne (Get-WorkerProcess)) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

Write-Log "=== control plane boot start ==="

if (-not (Test-Path $TemporalExe)) {
    Write-Log "ERROR: temporal executable missing: $TemporalExe"
    exit 1
}
if (-not (Test-Path $MinioExe)) {
    Write-Log "ERROR: minio executable missing: $MinioExe"
    exit 1
}
if (-not (Test-Path $CondaBat)) {
    Write-Log "ERROR: conda.bat missing: $CondaBat"
    exit 1
}
if (-not (Test-Path $WorkerPython)) {
    Write-Log "ERROR: worker python missing: $WorkerPython"
    exit 1
}

$envConfig = Read-EnvFile -Path (Join-Path $RepoRoot ".env")
$minioAccess = if ($envConfig.ContainsKey("MINIO_ACCESS_KEY")) { $envConfig["MINIO_ACCESS_KEY"] } elseif ($envConfig.ContainsKey("AWS_ACCESS_KEY_ID")) { $envConfig["AWS_ACCESS_KEY_ID"] } else { "minioadmin" }
$minioSecret = if ($envConfig.ContainsKey("MINIO_SECRET_KEY")) { $envConfig["MINIO_SECRET_KEY"] } elseif ($envConfig.ContainsKey("AWS_SECRET_ACCESS_KEY")) { $envConfig["AWS_SECRET_ACCESS_KEY"] } else { "minioadmin" }

if (Test-PortListening -Port 7233) {
    Write-Log "Temporal already listening on 7233"
}
else {
    $temporalOut = Join-Path $LogDir "temporal.log"
    $temporalErr = Join-Path $LogDir "temporal.err.log"
    $pTemporal = Start-Process -FilePath $TemporalExe -ArgumentList @("server", "start-dev", "--ip", "0.0.0.0") -WorkingDirectory (Split-Path $TemporalExe) -RedirectStandardOutput $temporalOut -RedirectStandardError $temporalErr -WindowStyle Hidden -PassThru
    Write-Log "Temporal started. PID=$($pTemporal.Id)"
}

if (-not (Wait-Port -Port 7233 -TimeoutSeconds 45)) {
    Write-Log "ERROR: Temporal did not open 7233 in time"
    exit 1
}

if (Test-PortListening -Port 9000) {
    Write-Log "MinIO already listening on 9000"
}
else {
    New-Item -ItemType Directory -Path $MinioDataDir -Force | Out-Null
    $oldRootUser = $env:MINIO_ROOT_USER
    $oldRootPassword = $env:MINIO_ROOT_PASSWORD
    $env:MINIO_ROOT_USER = $minioAccess
    $env:MINIO_ROOT_PASSWORD = $minioSecret

    $minioOut = Join-Path $LogDir "minio.log"
    $minioErr = Join-Path $LogDir "minio.err.log"
    $pMinio = Start-Process -FilePath $MinioExe -ArgumentList @("server", $MinioDataDir, "--address", ":9000", "--console-address", ":9001") -WorkingDirectory (Split-Path $MinioExe) -RedirectStandardOutput $minioOut -RedirectStandardError $minioErr -WindowStyle Hidden -PassThru
    Write-Log "MinIO started. PID=$($pMinio.Id)"

    if ($null -eq $oldRootUser) { Remove-Item Env:MINIO_ROOT_USER -ErrorAction SilentlyContinue } else { $env:MINIO_ROOT_USER = $oldRootUser }
    if ($null -eq $oldRootPassword) { Remove-Item Env:MINIO_ROOT_PASSWORD -ErrorAction SilentlyContinue } else { $env:MINIO_ROOT_PASSWORD = $oldRootPassword }
}

if (-not (Wait-Port -Port 9000 -TimeoutSeconds 45)) {
    Write-Log "ERROR: MinIO did not open 9000 in time"
    exit 1
}

if (Test-PortListening -Port 8000) {
    Write-Log "FastAPI already listening on 8000"
}
else {
    $fastapiOut = Join-Path $LogDir "fastapi.log"
    $fastapiErr = Join-Path $LogDir "fastapi.err.log"
    $cmdLine = "`"$CondaBat`" run -n cres python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    $pFastapi = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmdLine -WorkingDirectory $RepoRoot -RedirectStandardOutput $fastapiOut -RedirectStandardError $fastapiErr -WindowStyle Hidden -PassThru
    Write-Log "FastAPI started. PID=$($pFastapi.Id)"
}

if (-not (Wait-Port -Port 8000 -TimeoutSeconds 60)) {
    Write-Log "ERROR: FastAPI did not open 8000 in time"
    exit 1
}

if ($null -ne (Get-WorkerProcess)) {
    Write-Log "CPU worker already running"
}
else {
    $workerOut = Join-Path $LogDir "worker-cpu.log"
    $workerErr = Join-Path $LogDir "worker-cpu.err.log"

    $workerMode = "cpu"
    $baseTaskQueue = if ($envConfig.ContainsKey("BASE_TASK_QUEUE")) { $envConfig["BASE_TASK_QUEUE"] } else { "video-processing" }
    $temporalAddress = if ($envConfig.ContainsKey("TEMPORAL_ADDRESS")) { $envConfig["TEMPORAL_ADDRESS"] } else { "127.0.0.1:7233" }
    $minioEndpoint = if ($envConfig.ContainsKey("MINIO_ENDPOINT")) { $envConfig["MINIO_ENDPOINT"] } else { "127.0.0.1:9000" }
    $minioSecure = if ($envConfig.ContainsKey("MINIO_SECURE")) { $envConfig["MINIO_SECURE"] } else { "false" }

    $oldWorkerMode = $env:WORKER_MODE
    $oldBaseTaskQueue = $env:BASE_TASK_QUEUE
    $oldTemporalAddress = $env:TEMPORAL_ADDRESS
    $oldMinioEndpoint = $env:MINIO_ENDPOINT
    $oldMinioSecure = $env:MINIO_SECURE
    $oldMinioAccess = $env:MINIO_ACCESS_KEY
    $oldMinioSecret = $env:MINIO_SECRET_KEY
    $oldAwsAccess = $env:AWS_ACCESS_KEY_ID
    $oldAwsSecret = $env:AWS_SECRET_ACCESS_KEY

    $env:WORKER_MODE = $workerMode
    $env:BASE_TASK_QUEUE = $baseTaskQueue
    $env:TEMPORAL_ADDRESS = $temporalAddress
    $env:MINIO_ENDPOINT = $minioEndpoint
    $env:MINIO_SECURE = $minioSecure
    $env:MINIO_ACCESS_KEY = $minioAccess
    $env:MINIO_SECRET_KEY = $minioSecret
    $env:AWS_ACCESS_KEY_ID = $minioAccess
    $env:AWS_SECRET_ACCESS_KEY = $minioSecret

    $pWorker = Start-Process -FilePath $WorkerPython -ArgumentList @("-m", "src.backend.worker") -WorkingDirectory $RepoRoot -RedirectStandardOutput $workerOut -RedirectStandardError $workerErr -WindowStyle Hidden -PassThru
    Write-Log "CPU worker started. PID=$($pWorker.Id)"

    if ($null -eq $oldWorkerMode) { Remove-Item Env:WORKER_MODE -ErrorAction SilentlyContinue } else { $env:WORKER_MODE = $oldWorkerMode }
    if ($null -eq $oldBaseTaskQueue) { Remove-Item Env:BASE_TASK_QUEUE -ErrorAction SilentlyContinue } else { $env:BASE_TASK_QUEUE = $oldBaseTaskQueue }
    if ($null -eq $oldTemporalAddress) { Remove-Item Env:TEMPORAL_ADDRESS -ErrorAction SilentlyContinue } else { $env:TEMPORAL_ADDRESS = $oldTemporalAddress }
    if ($null -eq $oldMinioEndpoint) { Remove-Item Env:MINIO_ENDPOINT -ErrorAction SilentlyContinue } else { $env:MINIO_ENDPOINT = $oldMinioEndpoint }
    if ($null -eq $oldMinioSecure) { Remove-Item Env:MINIO_SECURE -ErrorAction SilentlyContinue } else { $env:MINIO_SECURE = $oldMinioSecure }
    if ($null -eq $oldMinioAccess) { Remove-Item Env:MINIO_ACCESS_KEY -ErrorAction SilentlyContinue } else { $env:MINIO_ACCESS_KEY = $oldMinioAccess }
    if ($null -eq $oldMinioSecret) { Remove-Item Env:MINIO_SECRET_KEY -ErrorAction SilentlyContinue } else { $env:MINIO_SECRET_KEY = $oldMinioSecret }
    if ($null -eq $oldAwsAccess) { Remove-Item Env:AWS_ACCESS_KEY_ID -ErrorAction SilentlyContinue } else { $env:AWS_ACCESS_KEY_ID = $oldAwsAccess }
    if ($null -eq $oldAwsSecret) { Remove-Item Env:AWS_SECRET_ACCESS_KEY -ErrorAction SilentlyContinue } else { $env:AWS_SECRET_ACCESS_KEY = $oldAwsSecret }
}

if (-not (Wait-Worker -TimeoutSeconds 30)) {
    Write-Log "ERROR: CPU worker did not stay running"
    exit 1
}

Write-Log "Control plane ready: Temporal(7233), MinIO(9000), FastAPI(8000)"
Write-Log "=== control plane boot finish ==="
