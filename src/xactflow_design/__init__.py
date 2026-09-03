__version__ = "0.1.0"

from pathlib import Path

import ipxact
from xactflow import Exporter

__all__ = ["DesignExporter", "__version__"]


class DesignExporter(Exporter):
    """Serialize an ipxact.Design into an IEEE 1685-2022 IP-XACT design XML file."""

    name = "design"

    def export(self, subject: object, output_dir: Path, **options: object) -> None:
        raise NotImplementedError
