"""Ableton Live 11/12 control-surface entry point."""
def create_instance(c_instance):
    from .bridge import PromptBridge
    return PromptBridge(c_instance)
