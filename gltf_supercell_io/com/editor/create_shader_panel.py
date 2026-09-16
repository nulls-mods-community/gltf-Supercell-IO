# ty: ignore[invalid-type-form]

from typing import TYPE_CHECKING

import bpy
from bpy.types import Context, Operator, Panel
from typing_extensions import override

from ..shader.loader import LibraryLoader
from ..shader_presets import ShaderPresets, ShaderPresetType
from ..utilities.shader import ShaderUtils

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems


class SHADER_OT_SC_create_shader(Operator):
    bl_idname = "supercell.create_tree"
    bl_label = "Create shader"

    item_type: bpy.props.StringProperty()
    item_id: bpy.props.StringProperty()
    item_label: bpy.props.StringProperty(default="")

    @override
    def execute(self, context: Context) -> set["OperatorReturnItems"]:
        obj = context.active_object
        if obj is None:
            self.report({"WARNING"}, "No active object")
            return {"CANCELLED"}

        mat = obj.active_material
        if mat is None:
            self.report({"WARNING"}, "No active material")
            return {"CANCELLED"}

        if self.item_type == "utility":
            node = LibraryLoader.instantiate_utility(
                ShaderUtils.get_node_tree(mat), self.item_id
            )
        elif self.item_type == "shader":
            node = LibraryLoader.instantiate_shader(
                ShaderUtils.get_node_tree(mat), self.item_id
            )

            if not self.item_label:
                preset = ShaderPresets.get_preset_by_id(self.item_id)
                node.label = preset.shader_label
        else:
            raise NotImplementedError()

        if node:
            if self.item_label:
                node.label = self.item_label

        return {"FINISHED"}


class SHADER_PT_SC_create_shader(Panel):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_label = "Shaders"
    bl_category = "Supercell"

    @override
    def draw(self, context: Context) -> None:
        _context = context  # to suppress typechecker

        if self.layout is not None:
            unlit = self.layout.operator(
                "supercell.create_tree", text="Create unlit shader"
            )
            assert unlit is not None
            unlit.item_id = ShaderPresetType.UNLIT
            unlit.item_type = "shader"

            bs = self.layout.operator(
                "supercell.create_tree", text="Create Brawl Stars shader"
            )
            assert bs is not None
            bs.item_id = ShaderPresetType.BRAWL_STARS
            bs.item_type = "shader"

            bs_legacy = self.layout.operator(
                "supercell.create_tree", text="Create Brawl Stars Legacy shader"
            )
            assert bs_legacy is not None
            bs_legacy.item_id = ShaderPresetType.BRAWL_STARS_LEGACY
            bs_legacy.item_type = "shader"


class SHADER_PT_SC_create_utilities(Panel):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_label = "Utilities"
    bl_category = "Supercell"

    @override
    def draw(self, context: Context) -> None:
        _context = context  # to suppress typechecker

        if self.layout is not None:
            lightmap = self.layout.operator(
                "supercell.create_tree", text="Create Lightmap UV"
            )
            assert lightmap is not None
            lightmap.item_id = "ScLightmapUV"
            lightmap.item_type = "utility"
            lightmap.item_label = "Lightmaps"

            screen = self.layout.operator(
                "supercell.create_tree", text="Create Screen Modifier"
            )
            assert screen is not None
            screen.item_id = "ScScreenModifier"
            screen.item_type = "utility"
            screen.item_label = "Screen"

            add = self.layout.operator(
                "supercell.create_tree", text="Create Additive Modifier"
            )
            assert add is not None
            add.item_id = "ScAdditiveModifier"
            add.item_type = "utility"
            add.item_label = "Screen"
