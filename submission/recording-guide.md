# Finish the three-minute demo

The supplied screen footage records the real local application. It is silent so Shivam can provide the narration in his own voice. Do not describe this footage as a recording of the hosted Databricks App. Cloud execution evidence, when available, is a separate artifact unless the hosted app itself is recorded.

1. Open the silent MP4 in `output/video/` and the [verbatim script](video-script.md), or use the [printable narration](../output/pdf/hawkerbridge-video-narration.pdf).
2. Record your voice while watching the footage. Leave the indicated pauses for date, budget and screen changes. The target duration is **2:55**, safely below the three-minute limit. Use headphones so playback does not enter the microphone. A phone voice recorder or QuickTime audio recording is sufficient.
3. Save the audio outside the repository's tracked files, such as `tmp/voiceover.m4a`. Listen once for clipping, background noise and rushed explanations.
4. Combine the supplied footage and your actual audio:

   ```sh
   python3 scripts/assemble_demo.py \
     --footage output/video/hawkerbridge-demo-silent.mp4 \
     --voiceover tmp/voiceover.m4a \
     --output output/video/hawkerbridge-demo-with-voice.mp4
   ```

   FFmpeg must be installed. The script creates a new file, keeps the actual browser footage, pads its final frame when needed, and caps the output at 175 seconds. It refuses an overlong audio recording rather than silently cutting your sentence. If the narration finishes too early, record the intended pauses rather than accelerating the screen footage.
5. The [editable captions](hawkerbridge-captions.srt) contain the spoken script with approximate timings. Align them with your recorded voice in the video editor or upload them as a subtitle track. Check names, Singapore-dollar amounts and the distinction between planned meals and measured impact.
6. Watch the entire final MP4. Confirm the date is 28 September 2026, the budgets produce **225 / 450 / 450** planned meals, the capacity ceiling is clear, and no email, password or token appears.
7. Upload the finished video to YouTube or Vimeo as public or unlisted. Record its real URL in `submission/deployment-status.json`, then run `uv run python scripts/check_submission.py --round 2`.

The recording uses a synthetic guest account. It does not establish a customer relationship, verified service venue or dispatched meal. The proposal review screen confirms understanding of assumptions and the need for future field checks; it does not claim those checks have happened.

If a final cloud demo is recorded later, follow the conditional cloud paragraph in the script and show the actual successful job, governed tables and matching MLflow run. For archived input mode, state that the run processes a dated public-data archive. Never substitute a deployment diagram for execution evidence.
