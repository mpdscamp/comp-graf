import os
from direct.actor.Actor import Actor
from panda3d.core import BitMask32, NodePath

from direct.showbase.ShowBase import ShowBase
base: ShowBase

"""
Load a model or actor from `path`.
Returns a tuple (model_node, anim_names).
  - model_node is either an Actor (if animations found) or a NodePath.
  - anim_names is a list of animation names (empty if static).
Automatically reparents to `parent` (defaults to render).
"""
def import_model(path: str, parent: NodePath = None, scale: float = 1.0, collide_mask=BitMask32(0)):
    if not os.path.isabs(path):
        here = os.path.dirname(__file__)
        path = os.path.abspath(os.path.join(here, "..", "models", path))

    parent = parent or base.render
    anim_names = []
    model_node = None

    try:
        actor = Actor(path)
        names = actor.getAnimNames()
        if names:
            model_node = actor
            anim_names = names
        else:
            actor.cleanup()
    except Exception:
        actor = None

    if model_node is None:
        model_node = base.loader.loadModel(path)

    model_node.reparentTo(parent)
    model_node.setScale(scale)
    model_node.setCollideMask(collide_mask)
    return model_node, anim_names


