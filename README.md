# THE BLENDER v39 No Import Crash

Hotfix: feeder_brain.py is self-contained and no longer imports team lists from config.py. This prevents Streamlit import failure before app launch.
