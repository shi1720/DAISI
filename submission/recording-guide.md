# The narrated hosted demo

The final release video is **175 seconds**, below the three-minute limit. It records the actual Firebase application, not the Databricks workspace interface. The Evidence page shows verified Databricks publication records. A generic synthetic narrator reads the [verbatim script](video-script.md); it is not Shivam's recorded or cloned voice.

## Reproduce the capture

1. Verify the deployed site with `uv run python scripts/smoke_hosted.py` and complete the container-rollout persistence check in the Firebase runbook.
2. Dispatch the GitHub Actions **Verify HawkerBridge** workflow with `base_url=https://hawkerbridge-sg.web.app` and `record_demo=true`. The isolated remote Chromium runner follows the real UI. It uses a synthetic guest, inspects the review checklist, cancels it and exports a draft. It does not claim a venue has been checked or a meal dispatched.
3. Retrieve the footage, timeline and PDF from the run. If artifact storage is unavailable, use `browser-tests/extract-evidence.mjs` on the run logs to verify their SHA256 hashes.
4. The narration script is `submission/narration-scenes.json`. `scripts/generate_narration.py` uses a locally supplied OpenAI API key to produce six voice clips and word timestamps. Credentials are never written to the repository. The application itself needs no LLM key.
5. Render the actual hosted capture with the prepared narration:

   ```sh
   uv run python scripts/render_narrated_demo.py \
     --footage output/demo-footage/hawkerbridge-silent-walkthrough.mp4 \
     --output output/video/hawkerbridge-demo-narrated.mp4
   ```

The renderer begins with an original 8.5-second title card while the recorded page loads, then preserves the actual browser footage until a six-second closing card displays the public website. It aligns six narration scenes, burns readable captions and labels the synthetic narration. It also writes an editable SRT track and media hashes to `output/video/narrated-provenance.json`. It refuses to replace an existing final video silently.

## Final review

Watch the complete edit. Check the date, 225 / 450 / 450 outputs, caption timing, speech clarity and safe margins. No real credentials, personal notes or participant voice are shown. The Evidence scene must distinguish nine cloud scenarios from the separate 15-scenario local benchmark. Cloud input provenance is three live tabular downloads plus two checksummed geometry archives.

Use the supplied YouTube title, description and original thumbnail. Publish with Public visibility as requested and verify playback without account access. Record the actual URL in `submission/deployment-status.json` and Devpost. A local MP4 alone does not complete the submission.

The earlier `hawkerbridge-demo-silent.mp4` and `provenance.json` describe a historical local recording. They are retained as historical evidence and are not the final hosted demonstration. `assemble_demo.py` supports that earlier local workflow; use the renderer above for the current narrated release.
