__version__ = "0.2.0"

import re
from pathlib import Path

import ipxact
from lxml import etree
from xactflow import Exporter

from .common_writer import qn
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

    The output file is named <vendor>_<library>_<name>_<version>.xml into output_dir.
    """

    name = "design"

    def export(self, subject: object, output_dir: Path, **options: object) -> None:
        if not isinstance(subject, ipxact.Design):
            # LinkedDesign support is an agreed-on later addition, not an oversight.
            raise TypeError(f"xactflow-design only supports ipxact.Design, got {type(subject).__name__}")
        output_dir = Path(output_dir)
        path = output_dir / _file_name(subject.vlnv)
        _check_overwrite(path, subject.vlnv)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_design_file(subject, path)


_FILE_NAME_PART = re.compile(r"[A-Za-z0-9._-]+")


def _vlnv_parts(vlnv: ipxact.VLNV) -> list:
    return [vlnv.vendor, vlnv.library, vlnv.name, vlnv.version]


def _file_name(vlnv: ipxact.VLNV) -> str:
    """<vendor>_<library>_<name>_<version>.xml, each part only made of letters, digits, '.', '_' and '-'."""
    parts = _vlnv_parts(vlnv)
    if not all(_FILE_NAME_PART.fullmatch(part) for part in parts):
        raise ValueError(f"VLNV {':'.join(parts)!r} cannot be used as a file name")
    return "_".join(parts) + ".xml"


def _check_overwrite(path: Path, vlnv: ipxact.VLNV) -> None:
    """Refuse to replace an existing file unless it is a design with the same VLNV (a re-export).

    Two VLNVs can still share a file name when a part holds an underscore (a_b + c and a + b_c),
    and the file may not be a design at all.
    """
    if not path.exists():
        return
    try:
        root = etree.parse(str(path)).getroot()
        existing = [root.findtext(qn(tag)) for tag in ("vendor", "library", "name", "version")]
        same = root.tag == qn("design") and existing == _vlnv_parts(vlnv)
    except etree.XMLSyntaxError:
        same = False
    if not same:
        raise FileExistsError(f"{path} already exists and is not the design {':'.join(_vlnv_parts(vlnv))}")
