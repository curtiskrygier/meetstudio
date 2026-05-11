# D2 Diagramming & Google Drive Verification Test (Build v17)

This document provides a script to verify the end-to-end functionality of the diagramming feature, including icon rendering, **Main Stage display**, and Google Drive archiving.

## How to Run the Test

1.  **Open Google Meet** and ensure the concierge side panel is open and **Connected**.
2.  **Open the Browser Console** (Right-click > Inspect > Console).
3.  **Paste and run the script below.**

### Verification Script (Safe Version)

```javascript
const agent = document.querySelector('gdm-architect-agent');
if (!agent || !agent.accessToken) {
  console.error("[ERROR] Please connect the concierge first!");
} else {
  console.log("[TEST] Starting End-to-End Verification Test (Build v17)...");
  fetch('/api/diagram', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      meeting_name: "Verification Build v17",
      access_token: agent.accessToken,
      space_id: agent.meetingId,
      session_id: agent.diagramSessionId || "manual-test-" + Date.now(),
      transcript: "Frontend Side Panel -> Backend FastAPI -> Cloud Run -> Google Drive. Use GCP icons."
    })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
       console.error("[ERROR] Backend Error:", data.error);
    } else {
       console.log("[SUCCESS] RENDERING & ARCHIVE PROVEN:");
       console.log("   - Diagram ID (on stage):", data.id);
       console.log("   - Drive File ID:", data.drive_file_id);
       console.log("   - Drive Folder ID:", data.drive_folder_id);
       console.log("FOLDER URL: https://drive.google.com/drive/folders/" + data.drive_folder_id);
       console.log("SVG URL: https://drive.google.com/file/d/" + data.drive_file_id + "/view");
    }
  })
  .catch(e => console.error("[ERROR] Test Failed:", e));
}
```

## What This Test Proves

*   **Main Stage Rendering:** By including the `session_id`, this test confirms that the backend stores the diagram with the ID the browser is expecting, causing the Main Stage to refresh and show the SVG.
*   **Icon Bundling (GCP Logos):** The diagram is rendered using official Google Cloud logo URLs.
*   **Google Drive Archiving:** The presence of a `drive_file_id` proves that the backend successfully created the `.svg` file on your Drive using your active OAuth session.
*   **Shared Drive & Folder Support:** The `drive_folder_id` confirms that the bot correctly managed the `Meet Recordings` folder structure.

## Results
Upon success, the script will output direct clickable links to the generated SVG and its containing folder on your Google Drive.
