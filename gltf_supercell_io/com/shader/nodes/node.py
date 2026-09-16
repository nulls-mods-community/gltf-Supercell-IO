import typing_extensions
from bpy.props import StringProperty
from bpy.types import Context, Node, ShaderNodeCustomGroup, ShaderNodeTree

from ..loader import LibraryLoader


def update_tree(node: "ShaderNodeScNode", _context: Context) -> None:
    if not node.tree_id or node.tree_id == "":
        return

    tree = LibraryLoader.load_shader_tree(node.tree_id)
    node.node_tree = tree
    node.width = tree.default_group_node_width


class ShaderNodeScNode(ShaderNodeCustomGroup):
    bl_idname = "ShaderNodeScNode"
    bl_label = "Supercell IO Node"
    bl_icon = "NODE"

    tree_id: StringProperty(default="", update=update_tree)  # ty: ignore[invalid-type-form]

    def copy(self, node) -> None:
        self.tree_id: str = node.tree_id
        self.node_tree: ShaderNodeTree = node.node_tree
        self.width: int = node.width
