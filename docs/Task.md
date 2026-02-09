📑 Task List (The "Ledger")
Date: 2026-02-06

 1. List scripts in scripts/ [DONE 19:18:00]
 2. Analyze script contents [DONE 19:22:00]
 3. Create/Update artifacts (Plan, Task, Perimeter) [DONE 19:35:00]
 4. Move legacy scripts to archive/scripts/ [DONE 19:42:00]
 5. Commit move changes [DONE 19:48:00]
 6. Discuss archival vs. ignore strategy with user [DONE 19:55:00]
 7. Permanently delete archive/ folder [DONE 20:05:00]
 8. Commit archive deletion [DONE 20:05:00]
 9. Restore original Workspace Rules content [DONE 19:58:00]
 10. Un-ignore workwithvastai.md in 
.gitignore
 [DONE 19:58:00]
 11. Commit Workspace Rules to codebase [DONE 19:59:00]
 12. Eliminate Agent rules from .gitignore [DONE 20:16:00]
 13. Locate and read deployment config files [DONE 20:38:00]
 14. Analyze configs against 7 requirements [DONE 20:45:00]
 15. Create deployment analysis document [DONE 20:45:00]
 16. Implement comprehensive health check endpoint [DONE 21:08:00]
 17. Add httpx dependency to requirements.txt [DONE 21:08:00]
 18. Add runtime resource limits to supervisord.conf [DONE 21:10:00]
 19. Update start-llama.sh with batch/memory limits [DONE 21:09:00]
 20. Commit all runtime improvements [DONE 21:14:00]
 21. Fix Temporal CLI installation path in Dockerfile.base [DONE 21:25:00]
 22. Commit and push Temporal CLI fix [DONE 21:25:00]
 23. Tune RLIMIT_AS and LLAMA_THREADS for 11GB RAM / 10 CPU [DONE 21:50:00]
 24. Commit and push final tuned configs [DONE 21:50:00]
 25. Establish SSH tunnel with port 8080 forwarding [/]
 26. Sync local codebase to remote /workspace/ via rsync [ ]
 27. Debug and monitor remote services [ ]
 28. Create 
.dockerignore
 for clean builds [DONE 22:25:00]
 29. Update 
Dockerfile
 for full project inclusion [DONE 22:25:00]
 30. Fix Dockerfile stage inheritance [DONE 23:30:00]
 31. Deploy to RTX 3060 Instance [DONE 23:45:00]
 32. Verify Oracle Batch Processing [DONE 23:30:00]
 33. Final Configuration Push [DONE 23:45:00]
 34. Implement GPU-accelerated video decoding [ ]
 35. Fix LLM language detection for Chinese tags [DONE 23:55:00]
 36. Enhance Video Page Transcription UI (Full view, click-to-jump) [DONE 00:15:00]
 37. Fix Docker build disk space exhaustion [DONE 00:25:00]
 38. Verify connectivity and file integrity after remote reboot [DONE 00:40:00]
 39. Rebuild remote frontend to apply UI changes [DONE 00:45:00]
 40. Execute 
generate_index.py
 on remote to fix tag jumps [DONE 00:50:00]
 41. Restart essential services (MinIO, etc.) after reboot [DONE 00:48:00]
 42. Refactor 
KaraokeTranscript.tsx
 for sentence-per-line and highlighting [DONE 01:00:00]
 43. Ensure full-height display of transcript in CSS [DONE 01:00:00]
44. Implement GPU-accelerated video decoding (FFmpeg NVDEC) [ ]
 45. Recover Vast.ai instance and restore service connectivity (IP/Port change) [DONE 01:28:00]
 46. Analyze and estimate Docker image size [DONE 01:15:00]
 47. Update SSH connection and deployment scripts with new defaults [DONE 01:25:00]
 48. Verify all services healthy via /health endpoint [DONE 01:35:00]
 49. Debug failed workflow video-Oracle-gNHY1UR_2rU (Live stream was_live fix) [DONE 01:45:00]
 50. Investigate "Videos not showing up" issue on frontend (Port & Path fix) [DONE 01:50:00]
 51. Optimize resource limits for 11GB RAM constraint [DONE 01:40:00]
 52. Correct llama-server flags (-b vs --n-batch) [DONE 01:52:00]
 53. Modify frontpage layout to 2-column (video grid + keyword sidebar) [DONE 20:55:00]
 54. Create /transcriptions route for keyword comparison page [DONE 20:56:00]
 55. Create 
TranscriptionCard.tsx
 component with keyword highlighting [DONE 20:56:00]
 56. Add sidebar and comparison styles to 
globals.css
 [DONE 20:55:00]
 57. Commit and push UI changes to repository [DONE 21:26:00]
 58. Create llama.cpp HTTP client service (llm_llamacpp.py) [DONE 22:40:00]
 59. Implement keyword extraction with LLM integration (keyword_service.py) [DONE 22:41:00]
 60. Implement coverage compensation algorithm [DONE 22:41:00]
 61. Create combined sentence extraction service (sentence_service.py) [DONE 22:42:00]
 62. Create FastAPI transcriptions endpoint (/api/transcriptions) [DONE 22:45:00]
 63. Revert frontpage to 3-column video grid [DONE 22:48:00]
 64. Create TranscriptionCarousel component [DONE 22:50:00]
65. Update transcriptions page with combined section and carousel [ ]
 66. Add carousel and combined content CSS styling [DONE 22:52:00]
67. Test backend endpoint with curl [ ]
68. Verify carousel navigation and combined keywords display [ ]
 69. Add cookies.txt support to 
activities.py
 [DONE 23:55:00]
70. Notify user to upload cookies.txt [ ]
 71. Re-trigger failed "Oracle" workflows [ ]
 72. Verify successful download and transcription [ ]