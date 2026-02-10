📜 Walkthrough (The "History")
Date: 2026-02-07 // Tag-To-Video Jump Fix & Karaoke UI Restoration
Plan Statement
This session focused on fixing the Tag-To-Video jump feature with a 1-second lead time and refining the transcription UI to restore the classic Karaoke effect with sentence-per-line display and active segment highlighting.

Root Cause/Findings
Tag-To-Video Jump Issue:

The 
data.json
 index had empty 
keywords
 arrays for all videos, preventing tags from appearing on the home page.
The keyword matching in 
generate_index.py
 used simple substring matching (if clean_k.lower() in seg.get('text', '').lower()), which could produce false positives and inaccurate start_time values.
The frontend logic in 
VideoCard.tsx
 already correctly calculated the seek time as Math.max(0, Math.floor(startTime) - 1).
Transcription UI Issue:

The initial implementation used a continuous paragraph layout with word-level interpolation for precision clicking.
The user requested the classic Karaoke effect with one sentence per line and full-segment highlighting, which is more visually intuitive and easier to track while watching.
Final Solution
1. Tag-To-Video Jump Fix
Backend: Precise Keyword Matching

Updated 
generate_index.py:89-96
 to use regex with word boundaries:
python
pattern = re.compile(rf'\b{re.escape(clean_k)}\b', re.IGNORECASE)
if pattern.search(seg.get('text', '')):
    start_time = seg.get('start', 0)
    break
This ensures keywords like "AI" don't match "again" and accurately captures the segment start time.
Frontend: Seek Offset Logic

Verified 
VideoCard.tsx:69-70
:
typescript
const startTime = kw.start_time || 0;
const seekTime = Math.max(0, Math.floor(startTime) - 1);
This produces a 1-second lead time for all tag jumps.
Remote Deployment:

Transferred updated 
generate_index.py
 via SCP to the Vast.ai instance
Ran python3 generate_index.py on the remote server
Successfully regenerated 
data.json
 with 26 entries containing precise start_time values
2. Karaoke UI Restoration
Component Refactor: Sentence-per-Line Layout

Updated 
KaraokeTranscript.tsx:75-97
 to render each segment as a separate div:
typescript
<div className="transcript-list">
    {transcript.segments.map((segment, idx) => {
        const isActive = currentTime >= segment.start && currentTime <= segment.end;
        return (
            <div
                className={`transcript-segment ${isActive ? 'active-segment' : ''}`}
                onClick={() => {
                    if (videoRef.current) {
                        videoRef.current.currentTime = segment.start;
                        videoRef.current.play();
                    }
                }}
            >
                {segment.text}
            </div>
        );
    })}
</div>
CSS Updates: Active Segment Highlighting

Updated 
globals.css:222-247
:
css
.transcript-segment.active-segment {
    color: var(--accent-foreground);
    background: var(--accent);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
    font-weight: 600;
}
This creates a bold, glowing highlight on the currently playing sentence.
Remote Frontend Rebuild:

Transferred 
KaraokeTranscript.tsx
 and 
globals.css
 to /workspace/web/src/...
Executed npm run build on the remote server
Build completed successfully in 2.5s using Turbopack
Verification
Tag Jump Accuracy:

Verified 
data.json
 on remote server contains structured keywords with start_time values:
json
"keywords": [
    {
        "word": "Skill",
        "count": 47,
        "score": 5,
        "start_time": 11.120000000000001
    }
]
Karaoke Effect:

Transcription now displays as a vertical list of sentences
Active segment highlights with blue background and bold text
Clicking any sentence jumps the video to that segment's start time
Service Health:

All backend services (MinIO, Temporal, Llama) restarted successfully after remote reboot
Frontend build process completed without errors
Artifacts Updated
implementation_plan.md
 - Added Plan 12, 13, and 14
task.md
 - Marked tasks 38-43 as completed
walkthrough.md
 - This document
Commits
b2e0ea5 - "feat: restore Karaoke effect with sentence-per-line and segment highlighting"
fa5df42 - "fix: Docker build disk space cleanup"
4abab18 - "fix: enforce Chinese language in LLM keyword generation"
Date: 2026-02-07 // Instance Recovery & Service Stability Optimization
Plan Statement
Regain access to the remote Vast.ai instance, restore all backend services, and resolve critical issues preventing video display and workflow completion.

Root Cause/Findings
IP Change: A remote reboot assigned a new host/port (ssh3.vast.ai:36535).
RAM Pressure: The 11GB system RAM was over-committed (6GB Worker + 4GB Llama), causing OOM and performance degradation.
Port Conflict: Lingering Node.js processes occupied port 3000, preventing the frontend from restarting.
Binary Incompatibility: The current llama-server build rejected the --n-batch flag, preferring -b.
Logic Flaw: Archived live streams were incorrectly rejected by a strict is_live: True check in 
activities.py
.
Final Solution
State Restoration: Updated all SSH and deployment scripts with the new instance defaults.
RAM Optimization: Reduced RLIMIT_AS to 3GB for Llama and 4GB for Worker to ensure system stability under the 11GB constraint.
Flag Correction: Rewrote 
start-llama.sh
 to use the -b flag and sanitized redundant parameters.
Display Fix: Corrected the index generation path to 
web/src/data.json
 and forcefully cleared port 3000 conflicts.
Workflow Recovery: Added an exception for live_status == 'was_live' in 
activities.py
 to allow processing of completed broadcasts.
Verification
/health endpoint confirms API, Temporal, and MinIO are healthy.
data.json
 successfully indexed with 9 videos.
gNHY1UR_2rU workflow passed the is_live check after logic refinement.
Vast.ai Instance Recovery: Successfully updated 
.env
 and 
connect_vast.py
 to port 32069 and verified LLM server start.
Date: 2026-02-07 // Transcription Search UI (Plan 17)
Plan Statement
Implement a keyword sidebar on the frontpage and a new transcription comparison page that allows users to view all videos containing a specific keyword side by side.

Root Cause/Findings
Frontpage used a single-column layout without keyword aggregation
No dedicated page existed for comparing transcriptions across videos
Keywords in 
data.json
 were empty (requires workflow processing to populate)
Final Solution
1. Frontpage 2-Column Layout (
page.tsx
)

Converted to grid layout with video cards on left (1fr) and keyword sidebar on right (280px)
Aggregates unique keywords from all videos with total occurrence counts
Sidebar links to /transcriptions?keyword=X for each keyword
2. Transcriptions Comparison Page (
transcriptions/page.tsx
)

Filters videos by keyword from URL parameter
Fetches transcripts and extracts sentences containing the keyword
Renders videos in a side-by-side grid layout
3. TranscriptionCard Component (
TranscriptionCard.tsx
)

Displays video title with link to full video page
Shows highlighted keyword sentence with blue accent styling
Includes scrollable full transcript below
4. CSS Styling (
globals.css
)

.main-layout: 2-column grid with responsive fallback
.keyword-sidebar: Sticky positioning with hover effects
.transcription-card, .keyword-sentence: Comparison page styling
Verification
Frontpage with Keyword Sidebar:
Frontpage Layout
Review
Frontpage Layout

Transcriptions Page:
Transcriptions Page
Review
Transcriptions Page

Dev server runs without TypeScript errors
2-column layout renders correctly with sidebar on right
Transcriptions page loads with keyword badge and navigation
Note: Sidebar shows "No keywords extracted yet" because 
data.json
 has empty keyword arrays (requires running workflow processing to populate)
 # #   D a t e :   2 0 2 6 - 0 2 - 1 0   / /   P r o j e c t   M i g r a t i o n   E x p l a n a t i o n 
       *   * * P l a n   S t a t e m e n t : * *   R e a d   a n d   e x p l a i n   t h e   h y b r i d   r u n t i m e   m i g r a t i o n   s u m m a r y   ( d o c s / h y b r i d _ r u n t i m e _ m i g r a t i o n _ s u m m a r y . m d ) . 
       *   * * R o o t   C a u s e / F i n d i n g s : * *   T h e   p r o j e c t   h a s   s u c c e s s f u l l y   m o v e d   f r o m   a   s i n g l e - h o s t   m o n l i t h   o n   V a s t . a i   ( P h a s e   A )   t o   a   h y b r i d   m o d e l   ( P h a s e   C )   w i t h   a   L A N - h o s t e d   c o n t r o l   p l a n e   ( h u i h u a n g )   a n d   a   V a s t . a i   c o m p u t e   p l a n e . 
       *   * * F i n a l   S o l u t i o n : * *   D o c u m e n t e d   t h e   s e r v i c e   o w n e r s h i p   a n d   r e q u e s t   f l o w   t o   t h e   u s e r   a n d   i n i t i a l i z e d   t o d a y ' s   t r a c k i n g   a r t i f a c t s . 
       *   * * V e r i f i c a t i o n : * *   E x p l a i n e d   t h e   a u t h o r i t a t i v e   a r c h i t e c t u r e   a n d   k e y   f a i l u r e   p a t t e r n s   t o   t h e   u s e r .  
 
       *   * * T o p o l o g y   F a c t : * *   U s e r   c o n f i r m e d   a   3 - n o d e   s e t u p :   N o r f o l k   ( D e v / 1 3 1 ) ,   H u i h u a n g   ( S e r v e r / 1 3 0 ) ,   a n d   I n s t a n c e   ( G P U / R e m o t e ) .   I n s t a n c e   c o n n e c t s   t o   H u i h u a n g   v i a   r o u t e r   f o r w a r d i n g .  
 
       *   * * C o n n e c t i v i t y   U p d a t e : * *   U p d a t e d   . e n v   a n d   P e r i m e t e r   w i t h   n e w   V a s t   ( s s h 5 . v a s t . a i : 1 1 3 1 9 )   a n d   H u i h u a n g   ( 1 9 2 . 1 6 8 . 2 . 1 3 0 )   d e t a i l s   i n c l u d i n g   M i n I O   c r e d e n t i a l s .  
 
       *   * * T e s t   F a i l u r e : * *   s c r i p t s / g o o g l e _ a i _ p i p e l i n e _ t e s t . p y   f a i l e d   t o   c o n n e c t   t o   b a c k e n d   o n   p o r t   8 0 0 0 .   C o n f i r m e d   F a s t A P I   o n   H u i h u a n g   i s   n o t   r e a c h a b l e   f r o m   N o r f o l k   w i t h   l o c a l h o s t : 8 0 0 0   d e f a u l t .   M u s t   u p d a t e   s c r i p t   t o   u s e   h t t p : / / 1 9 2 . 1 6 8 . 2 . 1 3 0 : 8 0 0 0 .  
 
       *   * * S S H   A u t h   F a i l u r e : * *   T h e   n e w   V a s t   i n s t a n c e   ( s s h 5 . v a s t . a i : 1 1 3 1 9 )   r e j e c t e d   o u r   S S H   k e y .   W e   n e e d   t o   d e p l o y   t h e   p u b l i c   k e y   o r   u s e   t h e   c o r r e c t   I d e n t i t y F i l e .  
 
       *   * * W o r k e r   S t a t u s : * *   s u p e r v i s o r d   w a s   n o t   r u n n i n g .   S t a r t e d   i t   m a n u a l l y .   w o r k e r   p r o c e s s   i s   n o w   S T A R T I N G .   l l a m a   i s   R U N N I N G .  
 
       *   * * W o r k e r   C r a s h : * *   W o r k e r   f a i l e d   w i t h   C o n n e c t i o n   r e f u s e d   t o   1 2 7 . 0 . 0 . 1 : 7 2 3 3   b e c a u s e   s u p e r v i s o r   o r   t h e   w o r k e r   s c r i p t   i s   n o t   p i c k i n g   u p   T E M P O R A L _ A D D R E S S   f r o m   t h e   t r a n s p a r e n t   . e n v   w e   j u s t   u p l o a d e d .   O r   s u p e r v i s o r d . c o n f   e n v i r o n m e n t   l o a d i n g   i s   t r i c k y .  
 
       *   * * S u p e r v i s o r d   C o n f i g   C o r r u p t i o n : * *   T h e   s e d   o r   e c h o   c o m m a n d   c o r r u p t e d   t h e   c o n f i g   f i l e .   T h e r e   s e e m s   t o   b e   a   c l o s i n g   q u o t a t i o n   i s s u e .   R e - u p l o a d i n g   a   c l e a n   s u p e r v i s o r d . c o n f   i s   s a f e r .  
 
## Date: 2026-02-10 // Last 6 Hours Operational Walkthrough (EST)

Plan Statement
Capture the latest operations window and persist architecture/runtime decisions so subsequent sessions can execute without re-discovery.

Root Cause/Findings
- Combined/transcriptions view was still bounded by a 5-video ceiling across backend and frontend fetch paths.
- Team workflow requires Conda-first execution on Norfolk/huihuang and no WSL path.
- Current production split remains: huihuang hosts control-plane and web/API, instance hosts worker/GPU stack.

Final Solution
1. Lifted hard limit in API and page fetch defaults:
   - `src/api/routers/transcriptions.py`: query limit default/max changed to 50.
   - `web/src/app/transcriptions/page.tsx`: read/bound limit from URL, default 50.
   - `web/src/app/sentence/page.tsx`: read/bound limit from URL, default 50.
   - `web/src/app/api/transcriptions/route.ts`: default forwarded limit changed to 50.
   - `web/src/app/transcriptions/TranscriptionsClient.tsx`: display text changed to `max 50`.
2. Reconfirmed runtime policy for this architecture window:
   - No WSL execution path.
   - Conda environments on Norfolk/huihuang are the standard operator path.
   - Instance should not own local Temporal/MinIO in the current topology.

Verification
- Static code scan confirmed removal of hardcoded `limit = 5` in transcriptions/sentence fetch paths.
- API constraint now accepts up to 50 videos for combine/transcription response generation.
- Docs updated to keep architecture and operational conventions discoverable.

Notes
- This update does not claim all workflow activity-level limits are removed; it addresses the fetch/response cap path that caused 5-only combine behavior in pages.
