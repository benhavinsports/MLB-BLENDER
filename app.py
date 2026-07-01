from engine.core import run_slate
from services.slate_stable import get_mlb_slate_stable

def main():

    print("⚾ BLENDER V4.1 TEST MODE")

    games = get_mlb_slate_stable()

    print("Loaded games:", len(games))

    results = run_slate(games)

    for r in results:
        print(r)

if __name__ == "__main__":
    main()
