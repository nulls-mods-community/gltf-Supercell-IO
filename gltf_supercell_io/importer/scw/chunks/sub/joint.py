from dataclasses import dataclass, field

from mathutils import Matrix

from .. import BinaryReader, ScwChunk


@dataclass
class ScwJoint(ScwChunk):
    name = ""
    inverse_bind_matrix: Matrix = field(default_factory=Matrix)

    def __br_read__(self, br: "BinaryReader", *_args, **_kwargs):
        self.name: str | None = br.read_str()
        self.inverse_bind_matrix = br.read_matrix()
