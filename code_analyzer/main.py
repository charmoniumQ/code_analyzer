from pathlib import Path
from typing import Mapping, Iterator, Dict, TypeVar, Generic
from tqdm import tqdm
import typer
import enum
import os
import pygraphviz  # type: ignore
import networkx as nx  # type: ignore
import antlr4  # type: ignore
import antlr4_grun
# from icecream import ic
ic = lambda x: (print(x), x)[1]


project_dir = Path(__file__).parent.relative_to(os.getcwd())


class Language(str, enum.Enum):
    MATLAB = "matlab"


def discover_matlab_sources(project: Path) -> Iterator[Path]:
    stack = list(project.iterdir())
    while stack:
        node = stack.pop()
        if node.is_dir():
            stack.extend(list(node.iterdir()))
        elif node.is_file() and node.suffix == ".m":
            yield node


class Function:
    pass


Vertex = TypeVar("Vertex")
Edge = TypeVar("Edge")
class DiGraph(Generic[Vertex, Edge]):
    pass


def render_callgraph(callgraph: DiGraph[Function, Function]) -> None:
    pass


def main(
        project: Path = typer.Argument(
            ...,
            exists=True,
            dir_okay=True,
            file_okay=False,
        ),
        entrypoint: str = typer.Argument(...),
        output: Path = typer.Argument(
            ...,
            exists=False,
            file_okay=True,
            dir_okay=False,
        ),
        language: Language = typer.Option(
            Language.MATLAB,
            case_sensitive=False,
        ),
) -> None:
    project_dir = Path(__file__).parent.parent.relative_to(os.getcwd())
    toplevel_functions: Dict[Function, Function] = {}
    graph = nx.DiGraph()

    sources = list(discover_matlab_sources(project))
    print("Got sources")
    for source in tqdm(sources, total=len(sources)):
        tqdm.write(f"{source.name}")
        ast = antlr4_grun.parse(project_dir / ".." / "antlr-matlab-grammar" / "MATLAB.g4", "matlab_file", source)
        tqdm.write(f"parsed {source.name}")

        class Rule(enum.IntEnum):
            def_function = ast.parser.ruleNames.index("def_function")
            xpr_array_index = ast.parser.ruleNames.index("xpr_array_index")
            xpr_function = ast.parser.ruleNames.index("xpr_function")
            atom_var = ast.parser.ruleNames.index("atom_var")

        functions = [
            child
            for child in ast.children
            if child.getRuleIndex() == Rule.def_function.value
        ]

        for function in functions:
            function_name = [
                child
                for child in function.children
                if hasattr(child, "getRuleIndex") and child.getRuleIndex() == Rule.atom_var
            ][0].getText()
            stack = function.children[:]
            while stack:
                node = stack.pop()
                rule = node.getRuleIndex() if hasattr(node, "getRuleIndex") else -1
                if rule == Rule.xpr_array_index.value or rule == Rule.xpr_function.value:
                    callee = node.children[0]
                    callee_name = callee.getText()
                    graph.add_edge(function_name, callee_name)
                if hasattr(node, "children") and node.children is not None:
                    stack.extend(node.children)
        tqdm.write(f"searched {source.name}")

        graphviz = pygraphviz.AGraph(strict=True, directed=True)
        for src, dst in graph.edges():
            if graph.in_degree(dst) > 1 or graph.out_degree(dst) > 0:
                graphviz.add_edge(src, dst)
            else:
                graphviz.add_node(src)
        dot_path = output.with_suffix(".dot")
        graphviz.write(dot_path)
        graphviz.draw(output, prog="dot")
        tqdm.write(f"graphed {source.name}")


if __name__ == "__main__":
    typer.run(main)
