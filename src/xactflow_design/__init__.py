__version__ = "0.1.2"

from pathlib import Path

import ipxact
from xactflow import Exporter

from .design_writer import design_to_bytes, write_design, write_design_file

__all__ = [
    "DesignExporter",
    "__version__",
    "design_to_bytes",
    "write_design",
    "write_design_file",
]


class DesignExporter(Exporter):
    """Serialize an ipxact.Design into an IEEE 1685-2022 IP-XACT design XML file.

    The output file is named after the design's VLNV name into output_dir.
    """

    name = "design"

    def export(self, subject: object, output_dir: Path, **options: object) -> None:
        if not isinstance(subject, ipxact.Design):
            # LinkedDesign support is an agreed-on later addition, not an oversight.
            raise TypeError(f"xactflow-design only supports ipxact.Design, got {type(subject).__name__}")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_design_file(subject, output_dir / f"{subject.vlnv.name}.xml")
