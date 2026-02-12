---
name: cres-triage
description: Triage and execute tasks for cres_ytdlp (LAN control plane + NAT + floating Vast.ai GPU architecture with dual FastAPI and dual workers).
---

# cres-triage (Core Constraints)

Use this skill at the start of every task in this repo.
This file is the compact, authoritative entrypoint.
Detailed troubleshooting and extended checks live in `./REFERENCE.md`.

## 1) Topology (Authoritative)

| Node | Role | Address | Notes |
|---|---|---|---|
| Norfolk | Dev host | `192.168.2.131` | VS Code + Codex client only; no services hosted |
| huihuang | Control plane + web | `192.168.2.130` | Project root: `C:\Users\rama\cres_ytdlp_norfolk` |
| Vast.ai GPU | Floating compute | Public worker node | Runs compute worker + llama.cpp + Whisper + Compute API |
| github | Remote Codebase | Private repo | Project version control and Docker Image Building initializtion |

## 2) SSH Access Model (Authoritative)
| From | To | Method |
|---|---|---|
| Norfolk | huihuang | SSH (`id_ed25519_huihuang`) |
| huihuang | Vast.ai GPU | SSH (`id_huihuang2vastai`) |

## 3) Endpoints and NAT Rules

| Service | Private endpoint | Public endpoint | Rule |
|---|---|---|---|
| Temporal | `192.168.2.130:7233` | `64.229.113.233:7233` | GPU must use public endpoint |
| MinIO | `192.168.2.130:9000` | `64.229.113.233:9000` | GPU must use public endpoint |
| Control FastAPI | `192.168.2.130:8000` | `64.229.113.233:8000` | GPU must use public endpoint |
| Web UI | `192.168.2.130:3000` | none | LAN only; never expose publicly |

Router (`192.168.2.1`) forwards only `7233`, `9000`, and `8000` to `192.168.2.130`.

## 4) FastAPI Separation (Hard Constraint)

| Host | API role | Port | Exposure |
|---|---|---|---|
| huihuang | Control API | `8000` | Public via NAT |
| GPU node | Compute API | `8000` | Not public |

Control API handles trigger/management/dispatch.
Compute API handles inference and GPU compute.

## 5) Worker Routing (Hard Constraint)

| Worker | Queue suffix | Runs on | Must not do |
|---|---|---|---|
| CPU worker | `@cpu` | huihuang and/or GPU (optional) | Load LLM or consume GPU memory |
| GPU worker | `@gpu` | GPU only | Start when GPU checks fail |

Routing format must be `<base_task>@cpu` or `<base_task>@gpu`.
Never route GPU tasks to `@cpu`.

## 6) Runtime Limits on GPU Node (Hard Constraint)

| Resource | Required value | Notes |
|---|---|---|
| Background RAM | `<= 7 GB` | `3 GB` llama.cpp + `4 GB` workers |
| llama offload | `-ngl 999` | Reduce only if VRAM overflow or model load fails |
| llama batch | `-b 512` | If OOM, reduce batch before `-ngl` |
| llama threads | `--threads 8` | Targeted for 10 vCPU |
| LLM model | `/workspace/packages/models/llm/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | Missing file: skip llama start |
| Whisper model | `/workspace/packages/models/whisperx` | Missing directory: disable Whisper features |

## 7) Non-Negotiable Rules

1. No Docker-in-Docker.
2. Control plane stays on huihuang only.
3. GPU node runs compute only.
4. Web UI stays LAN only.
5. Dual FastAPI separation is mandatory.
6. Queue suffix routing is mandatory.
7. Never commit secrets/tokens.
8. Use minimal diffs; avoid broad rewrites.

## 8) Required Output Format When Invoked

1. Architecture State
2. Findings
3. Priority Actions (top 1-3; include file, change, why, validation, rollback)
4. Patch Plan (minimal diff)
5. `docs/PLAN.md` update suggestion (only when architecture/ops behavior changes)

## 9) Definition of Done

- Queue routing is correct and enforced.
- `@gpu` worker runs only on GPU and passes startup checks.
- NAT and endpoint usage (public/private) are correct.
- Dual FastAPI separation is respected.
- End-to-end smoke checks pass.
- No secrets exposed and no architectural rule violated.

## 10) Reference

For expanded validation commands, network flow examples, and troubleshooting playbook:
- `./REFERENCE.md`
