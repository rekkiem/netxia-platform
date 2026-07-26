"""
Configuración raíz de pytest.

Cada microservicio tiene su propio paquete `app/`, y dentro de su
contenedor Docker eso funciona porque PYTHONPATH=/srv apunta solo al
código de ESE servicio. Al correr los tests localmente, todos los
`services/*/app` compiten por el mismo nombre de módulo top-level `app`,
así que no podemos simplemente agregar todos los directorios al
sys.path a la vez.

Solución: `use_service(nombre)` reemplaza, al ENTRAR, cualquier entrada
previa de otro servicio en sys.path y limpia el caché de `app`/`app.*`
para evitar mezclar código de dos microservicios distintos. A propósito
NO se limpia nada al salir del context manager: dentro de un mismo
archivo de test, después del bloque `with use_service(...): from app.x
import y`, el módulo `app` debe seguir resuelto a ESE servicio para que
`unittest.mock.patch("app.modulo.simbolo")` funcione más adelante en el
mismo archivo (patch necesita poder re-resolver el import).
"""
import sys
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES_ROOT = REPO_ROOT / "services"

if str(SERVICES_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICES_ROOT))

_all_service_dirs = {str(p) for p in SERVICES_ROOT.iterdir() if p.is_dir()}


def _clear_app_modules() -> None:
    for name in [n for n in sys.modules if n == "app" or n.startswith("app.")]:
        del sys.modules[name]


@contextmanager
def use_service(service_name: str):
    service_path = str(SERVICES_ROOT / service_name)

    # Remueve cualquier otro directorio de servicio que pudiera estar en
    # sys.path (de una llamada previa a use_service con otro servicio).
    for other_path in _all_service_dirs:
        if other_path != service_path and other_path in sys.path:
            sys.path.remove(other_path)

    if service_path not in sys.path:
        sys.path.insert(0, service_path)

    _clear_app_modules()
    yield
