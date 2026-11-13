"""v0.2's runtime tests read one `contract` module; v0.3 splits it by job (R-117, R-120). This gives those tests one
namespace over the new modules, so their assertions move unchanged and show the behaviour is the same."""
import types

from medomni.perception.runtime import aliases, errors, request, response, serve
from medomni.perception.runtime import decoders
from medomni.perception.runtime.decoders import _util, edf, images, tables, wfdb_

contract = types.SimpleNamespace(**{k: v for m in (errors, aliases, request, response, _util, edf, images, tables,
                                                    wfdb_, decoders) for k, v in vars(m).items()
                                    if not k.startswith("__")})

__all__ = ["contract", "serve"]
