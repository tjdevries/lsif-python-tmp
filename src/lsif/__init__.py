import abc
import dataclasses
import json
from functools import cached_property
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple

from jedi.api import Script
from jedi.api.classes import Name

from lsif.padawan import Definition
from lsif.padawan import Reference
from lsif.types import Range
from lsif.types import Writer

__version__ = "0.1.0"


# THREAD
IGNORE_ID = -1


def _get_next_id() -> Generator[int, None, None]:
    count = 1
    while True:
        yield count
        count += 1


class BaseNode(abc.ABC):
    __id_generator = _get_next_id()
    id: int

    _base_fields: Tuple[str, ...] = ("label", "type", "id")

    @property
    @abc.abstractmethod
    def type(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def label(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def _fields(self) -> Tuple[str, ...]:
        raise NotImplementedError

    def __init__(self, id: Optional[int] = None) -> None:
        self.id = id or next(self.__id_generator)

    def to_dictionary(self) -> Dict[str, Any]:
        fields = list(self._base_fields + self._fields)

        # Can pass IGNORE_ID to not serialize ID
        #   Thus far, only metadata needs this.
        if self.id == IGNORE_ID:
            fields.remove("id")

        return {field: getattr(self, field) for field in fields}

    def serialize(self) -> str:
        return json.dumps(self.to_dictionary()) + "\n"


class EdgeBase(BaseNode):
    type = "edge"

    def __init__(self) -> None:
        super().__init__()


class NextNode(EdgeBase):
    label = "next"

    inV: int
    outV: int

    _fields = ("inV", "outV")

    def __init__(self, inV: int, outV: int) -> None:
        super().__init__()
        self.inV = inV
        self.outV = outV


class SingleEdgeBase(EdgeBase):
    inV: int
    outV: int

    _fields = ("inV", "outV")

    def __init__(self, inV: int, outV: int) -> None:
        super().__init__()
        self.inV = inV
        self.outV = outV


class TextDocumentHoverNode(SingleEdgeBase):
    label = "textDocument/hover"


class TextDocumentDefinitionNode(SingleEdgeBase):
    label = "textDocument/definition"


class TextDocumentReferenceNode(SingleEdgeBase):
    label = "textDocument/references"


class MultiEdgeBase(EdgeBase):
    inVs: List[int]
    outV: int

    _fields: Tuple[str, ...] = ("inVs", "outV")

    def __init__(self, inVs: List[int], outV: int) -> None:
        super().__init__()
        self.inVs = inVs
        self.outV = outV


class ItemNode(MultiEdgeBase):
    label = "item"
    document: int

    _fields = ("document", *MultiEdgeBase._fields)

    def __init__(self, document: "DocumentNode", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.document = document.id


class ContainsNode(MultiEdgeBase):
    label = "contains"


class VertexBase(BaseNode):
    type = "vertex"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class MetadataNode(VertexBase):
    """Node for metadata stuff"""

    label = "metaData"

    _fields = ("version", "positionEncoding", "projectRoot")

    """ The version of the LSIF format using semver notation. See https://semver.org/. Please note
    the version numbers starting with 0 don't adhere to semver and adopters have to assume
    the each new version is breaking.
    """
    version: str = "0.5.0"

    """ Always utf-16 because lsp. """
    positionEncoding: str = "utf-16"

    """ The project root (in form of an URI) used to compute this dump."""
    projectRoot: str

    def __init__(self, projectRoot: Path) -> None:
        super().__init__(id=IGNORE_ID)
        self.projectRoot = projectRoot.absolute().as_uri()


class ProjectNode(VertexBase):
    label = "project"
    kind = "python"

    _fields = ("label", "kind")


class DocumentNode(VertexBase):
    """{
        id         : 1,
        type       : "vertex",
        label      : "document",
        uri        : "file:///Users/dirkb/sample.ts",
        languageId : "typescript"
    }
    """

    label = "document"
    languageId: str = "python"

    _fields = ("label", "languageId", "uri")

    uri: str
    path: Path

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path.absolute()
        self.uri = self.path.as_uri()

    @cached_property
    def script(self) -> Script:
        return Script(path=str(self.path))


class ResultSetNode(VertexBase):
    label = "resultSet"
    _fields = tuple()

    def __init__(self) -> None:
        super().__init__()


class RangeNode(VertexBase):
    label = "range"
    _fields = ("start", "end", "document")

    _range: Range
    _document: DocumentNode

    def __init__(self, range: Range, document: DocumentNode) -> None:
        super().__init__()
        self._range = range
        self._document = document

    @property
    def start(self) -> Dict:
        return dataclasses.asdict(self._range.start)

    @property
    def end(self) -> Dict:
        return dataclasses.asdict(self._range.end)

    @property
    def document(self) -> int:
        return self._document.id


class HoverResult(VertexBase):
    label = "hoverResult"
    result: Dict

    _fields = ("result",)

    def __init__(self, definition: Definition) -> None:
        super().__init__()
        self.result = {"contents": [definition.docstring]}


class DefinitionResult(VertexBase):
    label = "definitionResult"
    _fields = tuple()


class ReferenceResult(VertexBase):
    label = "referenceResult"
    _fields = tuple()


_ = """
// The document
{ id: 4, type: "vertex", label: "document", uri: "file:///Users/dirkb/sample.ts", languageId: "typescript" }

// The bar declaration
{ id: 6, type: "vertex", label: "resultSet" }
{ id: 9, type: "vertex", label: "range", start: { line: 0, character: 9 }, end: { line: 0, character: 12 } }
{ id: 10, type: "edge", label: "next", outV: 9, inV: 6 }
"""


def index(project_path: Path, writer: Writer) -> None:
    mt = MetadataNode(project_path)
    writer.write(mt.serialize())

    project_node = ProjectNode()
    writer.write(project_node.serialize())

    names_to_result_sets: Dict[str, ResultSetNode] = {}
    module_path_to_document_node: Dict[str, DocumentNode] = {}

    document_ids: List[int] = []

    for file in project_path.glob("**/*.py"):
        # TODO: Keep track of the ranges to associate them with this document
        print("Parsing:", file)

        filepath = Path(file)
        abs_path = str(filepath.absolute())
        document_node = module_path_to_document_node.get(abs_path, None)
        if not document_node:
            document_node = DocumentNode(filepath)
            writer.write(document_node.serialize())

        document_ids.append(document_node.id)
        module_path_to_document_node[str(document_node.script.path.absolute())] = document_node

        contained_ranges: List[RangeNode] = []

        # I think this is always empty
        # names = document.script.get_names(all_scopes=True, definitions=False, references=False)
        # print(names)

        definitions = document_node.script.get_names(all_scopes=True, definitions=True, references=False)
        for jedi_def in definitions:
            result_set = ResultSetNode()

            def_name = jedi_def.full_name or jedi_def.name
            print(def_name)
            assert def_name, f"Missing name for: {jedi_def}"

            names_to_result_sets[def_name] = result_set

            definition = Definition(jedi_def)
            definition_node = RangeNode(range=definition.range, document=document_node)

            contained_ranges.append(definition_node)

            writer.write(result_set.serialize())
            writer.write(definition_node.serialize())

            definition_next_node = NextNode(inV=result_set.id, outV=definition_node.id)
            writer.write(definition_next_node.serialize())

            hover_node = HoverResult(definition=definition)
            writer.write(hover_node.serialize())

            writer.write(TextDocumentHoverNode(inV=hover_node.id, outV=result_set.id).serialize())

            definition_result_node = DefinitionResult()
            writer.write(definition_result_node.serialize())

            writer.write(TextDocumentDefinitionNode(inV=definition_result_node.id, outV=result_set.id).serialize())
            writer.write(
                ItemNode(inVs=[definition_node.id], outV=definition_result_node.id, document=document_node).serialize()
            )

        references = document_node.script.get_names(all_scopes=True, definitions=False, references=True)
        for jedi_ref in references:
            reference = Reference(jedi_ref)
            reference_node = RangeNode(range=reference.range, document=document_node)
            contained_ranges.append(reference_node)

            writer.write(reference_node.serialize())

            possible_definitions = jedi_ref.goto(follow_imports=True)
            if not possible_definitions:
                print("No definitions found:", jedi_ref)
                continue

            jedi_reference_def = possible_definitions[0]
            if jedi_reference_def.full_name not in names_to_result_sets:
                print("SKIPPING:", jedi_reference_def, jedi_reference_def.module_name)
                continue

            jedi_reference_def_name = jedi_reference_def.full_name
            assert jedi_reference_def_name
            jedi_reference_def_result_set = names_to_result_sets[jedi_reference_def_name]

            writer.write(NextNode(inV=jedi_reference_def_result_set.id, outV=reference_node.id).serialize())

            reference_result_node = ReferenceResult()
            writer.write(reference_result_node.serialize())

            writer.write(
                TextDocumentReferenceNode(
                    inV=reference_result_node.id, outV=jedi_reference_def_result_set.id
                ).serialize()
            )

            writer.write(
                ItemNode(inVs=[reference_node.id], outV=reference_result_node.id, document=document_node).serialize()
            )

            # I make this edge earlier maybe? otherwise feels like you keep a ton of stuff in memory for lookups...
            # writer.write(
            #     ItemNode(inVs=[jedi_reference_def.id], outV=reference_result_node.id, document=document_node).serialize()
            # )

        writer.write(ContainsNode(inVs=[x.id for x in contained_ranges], outV=document_node.id).serialize())

    print("module paths:", module_path_to_document_node)
    print("definition names:", names_to_result_sets)
    writer.write(ContainsNode(inVs=document_ids, outV=project_node.id).serialize())


def index_to_file(project_root: Path) -> None:
    with open("dump.lsif", "w") as writer:
        index(project_root, writer)
