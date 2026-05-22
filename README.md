# MLB Blender v61 Universal Feed Brain

Keeps the current structure:
- Blender Machine
- Tickets
- Game Board

Upgrade:
- The top “CLICK / FEED DATA HERE” area accepts PDF, CSV, XLSX, screenshots/images, and text slips.
- Screenshots/Twitter slip images run through OCR when the host supports Tesseract.
- Slip/text/image rows get public fallback enrichment so the Blender can run without Star Tool direct login.
- Tickets now also appear under the Blender Machine after the run.
- Game Board stays in its own tab.

Important:
- PDF/CSV/XLSX with full Star Tool data remains the strongest feed.
- Screenshot/Twitter slip mode is an automatic fallback mode, not a replacement for full metrics.
