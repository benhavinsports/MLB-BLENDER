
from core.environment import apply_environment
from gates.gate import gate

def run_blender(slate):

    state = {
        "active_pool": slate["hitters"],
        "trace": []
    }

    state = apply_environment(state, slate)

    for i in range(1, 24):
        state = gate(state, i)

    return {
        "final": state["active_pool"],
        "trace": state["trace"]
    }
