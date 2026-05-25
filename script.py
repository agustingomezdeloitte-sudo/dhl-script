# ============================================================
#@title DHL EXPORT AUTOMATION - PLAYWRIGHT + CHROMIUM HEADLESS
# GOOGLE COLAB - SIN SELENIUM
#
# ✅ Usa Playwright
# ✅ Usa Chromium headless
# ✅ NO USA SELENIUM
# ✅ Hora local Chile America/Santiago
# ✅ Contraseña automática desde Colab Secrets
# ✅ NO pide contraseña por pantalla
#
# ✅ Países SOLO en:
#    div[role='combobox'][aria-controls=':r8:']
# ✅ Listbox SOLO en:
#    ul[role='listbox'][id=':r8:']
# ✅ Search SOLO en:
#    ul[role='listbox'][id=':r8:'] input[placeholder='Search']
# ✅ Si no encuentra ese selector, falla.
# ✅ NO busca otros combobox.
#
# ✅ BRASIL:
#    MARCAR Brazil
#    DESMARCAR Colombia / Peru / Chile / Ecuador
#
# ✅ OTROS:
#    DESMARCAR Brazil
#    MARCAR Colombia / Peru / Chile / Ecuador
#
# ✅ Export Orders + Export Details
# ✅ Brasil + Otros
# ✅ Logs en vivo
# ✅ Screenshots
# ✅ Status
# ✅ Click robusto en Send Email
# ============================================================

!pip install playwright python-dotenv -q
!playwright install chromium > /dev/null 2>&1
!playwright install-deps > /dev/null 2>&1

import os
import sys
import subprocess
from pathlib import Path
from google.colab import drive

# ============================================================
# CONFIG COLAB
# ============================================================

DRIVE_ROOT = "/content/drive/MyDrive"
BASE_DIR = f"{DRIVE_ROOT}/DHL_ZIPS"
LOG_DIR = f"{DRIVE_ROOT}/DHL_COLAB_LOGS"
SCREENSHOT_DIR = f"{DRIVE_ROOT}/DHL_COLAB_SCREENSHOTS"
STATUS_FILE = f"{LOG_DIR}/status_dhl_bot.txt"

BOT_PATH = f"{BASE_DIR}/bot_dhl_playwright.py"

DHL_USER = "agustingomez.deloitte@latam.com"
CHILE_TZ = "America/Santiago"

print("1️⃣ Conectando Google Drive...")
drive.mount("/content/drive")

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ============================================================
# CREDENCIALES DHL - AUTOMÁTICAS DESDE COLAB SECRETS
# ============================================================

print("\n2️⃣ Credenciales DHL")

DHL_PASS = ""

try:
    from google.colab import userdata
    DHL_PASS = userdata.get("DHL_PASS")
    if DHL_PASS:
        DHL_PASS = str(DHL_PASS).strip()
except Exception:
    DHL_PASS = ""

if not DHL_PASS:
    DHL_PASS = os.getenv("DHL_PASS", "").strip()

if not DHL_PASS:
    raise RuntimeError(
        "No existe DHL_PASS. Crea una Secret en Colab llamada DHL_PASS. "
        "No se pedirá contraseña por pantalla."
    )

print("✅ Contraseña DHL cargada automáticamente desde Secret / variable de entorno")

# ============================================================
# BOT PLAYWRIGHT DHL
# ============================================================

codigo_bot = r'''
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ============================================================
# CONFIG
# ============================================================

URL_DASHBOARD = "https://mysctrackandtrace.dhl.com/dashboard"

DHL_USER = os.getenv("DHL_USER", "").strip()
DHL_PASS = os.getenv("DHL_PASS", "").strip()

CHILE_TZ = os.getenv("CHILE_TZ", "America/Santiago")
TZ_CHILE = ZoneInfo(CHILE_TZ)

LOG_DIR = Path(os.getenv("DHL_LOG_DIR", "/content/drive/MyDrive/DHL_COLAB_LOGS"))
SCREENSHOT_DIR = Path(os.getenv("DHL_SCREENSHOT_DIR", "/content/drive/MyDrive/DHL_COLAB_SCREENSHOTS"))
STATUS_FILE = Path(os.getenv("DHL_STATUS_FILE", "/content/drive/MyDrive/DHL_COLAB_LOGS/status_dhl_bot.txt"))

PROFILE_DIR = Path("/content/dhl_playwright_profile")

LOG_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

CORREOS_EXPORT = [
    "agustingomez.deloitte@latam.com",
    "bastian.gonzalez@latam.com",
]

PAISES = {
    "Brazil": [
        "LATAM Airlines DFN Brazil",
        "LATAM Airlines Brazil",
        "Brazil",
        "Brasil",
    ],
    "Colombia": [
        "LATAM Airlines Colombia",
        "Colombia",
    ],
    "Peru": [
        "LATAM Airlines Peru",
        "LATAM Airlines Perú",
        "Peru",
        "Perú",
    ],
    "Chile": [
        "LATAM Airlines Chile",
        "Chile",
    ],
    "Ecuador": [
        "LATAM Airlines Ecuador",
        "Ecuador",
    ],
}

# ============================================================
# SELECTORES ESTRICTOS PAÍSES
# ============================================================

SELECTOR_COMBO_PAISES = "div[role='combobox'][aria-controls=':r8:']"

# IMPORTANTE:
# Antes estaba ul[role='listbox'] global y podía tomar otro listbox.
# Ahora queda amarrado estrictamente al id controlado por aria-controls=':r8:'.
SELECTOR_LISTBOX_PAISES = "ul[role='listbox'][id=':r8:']"
SELECTOR_SEARCH_PAISES = "ul[role='listbox'][id=':r8:'] input[placeholder='Search']"
SELECTOR_OPTIONS_PAISES = "ul[role='listbox'][id=':r8:'] li"

# ============================================================
# LOG / STATUS / SCREENSHOTS
# ============================================================

def ahora_chile():
    return datetime.now(TZ_CHILE)


def log(*args):
    ts = ahora_chile().strftime("%H:%M:%S")
    print(f"[{ts}]", *args, flush=True)


def guardar_status(texto):
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ahora = ahora_chile().strftime("%Y-%m-%d %H:%M:%S")
        STATUS_FILE.write_text(f"{ahora} | {texto}\n", encoding="utf-8")
        log("[STATUS]", texto)
    except Exception as e:
        log("[WARN] No se pudo guardar status:", str(e))


def limpiar_nombre(nombre):
    nombre = str(nombre).strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
    nombre = "".join(c for c in nombre if c.isalnum() or c in "_-")
    return nombre[:90] if nombre else "screenshot"


def screenshot(page, nombre):
    try:
        ts = ahora_chile().strftime("%Y%m%d_%H%M%S")
        ruta = SCREENSHOT_DIR / f"{ts}_{limpiar_nombre(nombre)}.png"
        page.screenshot(path=str(ruta), full_page=True)
        log("[SCREENSHOT]", ruta)
        return ruta
    except Exception as e:
        log("[WARN] Screenshot falló:", str(e))
        return None


def page_has_text(page, textos):
    for txt in textos:
        try:
            if page.locator(f"text={txt}").count() > 0:
                return txt
        except:
            pass
    return None

# ============================================================
# CLICK / FILL ROBUSTOS
# ============================================================

def click_locator_robusto(page, locator, descripcion="elemento", timeout=8000):
    last_error = None

    try:
        locator.scroll_into_view_if_needed(timeout=3000)
    except Exception as e:
        last_error = e

    try:
        locator.click(force=True, timeout=timeout, no_wait_after=True)
        log(f"[CLICK ROBUSTO OK] {descripcion} con force/no_wait_after")
        return True
    except Exception as e:
        last_error = e
        log(f"[CLICK ROBUSTO WARN] force click falló {descripcion}: {e}")

    try:
        locator.evaluate("""
            el => {
                el.scrollIntoView({block:'center', inline:'center'});
                el.click();
            }
        """)
        log(f"[CLICK ROBUSTO OK] {descripcion} con JS click")
        return True
    except Exception as e:
        last_error = e
        log(f"[CLICK ROBUSTO WARN] JS click falló {descripcion}: {e}")

    try:
        locator.evaluate("""
            el => {
                el.scrollIntoView({block:'center', inline:'center'});
                el.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, cancelable:true, view:window}));
                el.dispatchEvent(new MouseEvent('mouseup', {bubbles:true, cancelable:true, view:window}));
                el.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
            }
        """)
        log(f"[CLICK ROBUSTO OK] {descripcion} con mouse events")
        return True
    except Exception as e:
        last_error = e
        log(f"[CLICK ROBUSTO WARN] mouse events falló {descripcion}: {e}")

    try:
        locator.focus(timeout=3000)
        page.keyboard.press("Enter")
        log(f"[CLICK ROBUSTO OK] {descripcion} con Enter")
        return True
    except Exception as e:
        last_error = e
        log(f"[CLICK ROBUSTO FAIL] Enter falló {descripcion}: {e}")

    raise RuntimeError(f"No se pudo hacer click robusto en {descripcion}. Último error: {last_error}")


def click_first_visible(page, selectors, timeout=10000, descripcion="elemento", robusto=False):
    deadline = time.time() + timeout / 1000
    last_error = None

    while time.time() < deadline:
        for sel in selectors:
            try:
                loc = page.locator(sel)
                count = loc.count()

                for i in range(min(count, 20)):
                    item = loc.nth(i)
                    try:
                        if item.is_visible():
                            if robusto:
                                click_locator_robusto(page, item, descripcion=descripcion, timeout=8000)
                            else:
                                item.click(timeout=4000)
                            log(f"[CLICK OK] {descripcion}: {sel}")
                            return True
                    except Exception as e:
                        last_error = e
                        continue
            except Exception as e:
                last_error = e

        page.wait_for_timeout(300)

    raise RuntimeError(f"No se pudo hacer click en {descripcion}. Último error: {last_error}")


def fill_first_visible(page, selectors, texto, timeout=15000, descripcion="input"):
    deadline = time.time() + timeout / 1000
    last_error = None

    while time.time() < deadline:
        for sel in selectors:
            try:
                loc = page.locator(sel)
                count = loc.count()

                for i in range(min(count, 20)):
                    item = loc.nth(i)
                    try:
                        if item.is_visible():
                            item.click(timeout=3000)
                            item.fill("")
                            item.type(texto, delay=30)
                            log(f"[FILL OK] {descripcion}: {sel}")
                            return True
                    except Exception as e:
                        last_error = e
            except Exception as e:
                last_error = e

        page.wait_for_timeout(300)

    raise RuntimeError(f"No se pudo escribir en {descripcion}. Último error: {last_error}")

# ============================================================
# LOGIN
# ============================================================

def login_dhl(page):
    guardar_status("Abriendo DHL")
    page.goto(URL_DASHBOARD, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(5000)
    screenshot(page, "01_abriendo_dhl")

    try:
        other = page.locator("#otherTileText")
        if other.count() > 0 and other.first.is_visible():
            guardar_status("Seleccionando otra cuenta")
            other.first.click(timeout=5000)
            page.wait_for_timeout(2500)
    except:
        pass

    try:
        if page.locator("#i0116").count() > 0 or page.locator("input[type='email']").count() > 0:
            guardar_status("Ingresando usuario")
            fill_first_visible(
                page,
                ["#i0116", "input[type='email']", "input[name='loginfmt']"],
                DHL_USER,
                timeout=25000,
                descripcion="usuario"
            )
            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)
            screenshot(page, "02_usuario")
    except PlaywrightTimeoutError:
        pass

    try:
        if page.locator("#i0118").count() > 0 or page.locator("input[type='password']").count() > 0:
            guardar_status("Ingresando contraseña")
            fill_first_visible(
                page,
                ["#i0118", "input[type='password']", "input[name='passwd']"],
                DHL_PASS,
                timeout=25000,
                descripcion="contraseña"
            )
            page.keyboard.press("Enter")
            page.wait_for_timeout(7000)
            screenshot(page, "03_password")
    except PlaywrightTimeoutError:
        pass

    try:
        if page.locator("#idSIButton9").count() > 0:
            guardar_status("Confirmando mantener sesión")
            page.locator("#idSIButton9").last.click(timeout=8000)
            page.wait_for_timeout(5000)
            screenshot(page, "04_mantener_sesion")
    except:
        pass

    mfa = page_has_text(page, [
        "Microsoft Authenticator",
        "Verify your identity",
        "Approve sign in request",
        "Use your Microsoft Authenticator app",
        "Aprobar solicitud de inicio de sesión",
    ])

    if mfa:
        screenshot(page, "mfa_detectado")
        raise RuntimeError(f"MFA requerido o bloqueo de autenticación: {mfa}")

    guardar_status("Login procesado")

# ============================================================
# DASHBOARD
# ============================================================

def esperar_dashboard(page):
    guardar_status("Validando dashboard DHL")

    for intento in range(1, 7):
        log(f"[DASHBOARD] Intento {intento}/6")
        page.wait_for_timeout(7000)
        screenshot(page, f"dashboard_intento_{intento}")

        try:
            export_orders = page.locator("text=Export Orders").count()
            combo_paises = page.locator(SELECTOR_COMBO_PAISES).count()

            if export_orders > 0 or combo_paises > 0:
                guardar_status("Dashboard DHL cargado correctamente")
                return True
        except:
            pass

        try:
            page.goto(URL_DASHBOARD, wait_until="domcontentloaded", timeout=120000)
        except:
            try:
                page.reload(wait_until="domcontentloaded", timeout=120000)
            except:
                pass

    raise RuntimeError("Dashboard DHL no cargó correctamente")

# ============================================================
# SELECTOR PAÍSES - SOLO EL SELECTOR CORRECTO :r8:
# ============================================================

def abrir_selector_paises(page):
    """
    Abre SOLO el selector de países correcto:

    Combo:
      div[role='combobox'][aria-controls=':r8:']

    Listbox:
      ul[role='listbox'][id=':r8:']

    Search:
      ul[role='listbox'][id=':r8:'] input[placeholder='Search']
    """

    guardar_status("Abriendo selector de países correcto")

    try:
        combo = page.locator(SELECTOR_COMBO_PAISES).first
        combo.wait_for(state="visible", timeout=25000)

        try:
            combo.scroll_into_view_if_needed(timeout=5000)
        except:
            pass

        combo.click(timeout=8000)
        page.wait_for_timeout(900)

        listbox = page.locator(SELECTOR_LISTBOX_PAISES).first
        listbox.wait_for(state="visible", timeout=15000)

        search = page.locator(SELECTOR_SEARCH_PAISES).first
        search.wait_for(state="visible", timeout=15000)
        search.click(timeout=5000)

        page.wait_for_timeout(300)

        log("[SELECTOR] Combo correcto:", SELECTOR_COMBO_PAISES)
        log("[SELECTOR] Listbox correcto:", SELECTOR_LISTBOX_PAISES)
        log("[SELECTOR] Search correcto:", SELECTOR_SEARCH_PAISES)

        screenshot(page, "selector_paises_correcto_abierto")

        return search

    except Exception as e:
        screenshot(page, "error_abriendo_selector_paises_correcto")
        raise RuntimeError(
            "No se pudo abrir el selector correcto de países. "
            "No se intentó ningún otro combobox. "
            f"Combo usado: {SELECTOR_COMBO_PAISES}. "
            f"Listbox usado: {SELECTOR_LISTBOX_PAISES}. "
            f"Search usado: {SELECTOR_SEARCH_PAISES}. "
            f"Error: {e}"
        )


def cerrar_selector_paises(page):
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except:
        pass

    try:
        page.mouse.click(10, 10)
        page.wait_for_timeout(500)
    except:
        pass


def obtener_search_paises(page):
    """
    Revalida SIEMPRE que el input usado sea el Search del listbox correcto :r8:.
    """

    try:
        listbox = page.locator(SELECTOR_LISTBOX_PAISES).first
        listbox.wait_for(state="visible", timeout=10000)

        search = page.locator(SELECTOR_SEARCH_PAISES).first
        search.wait_for(state="visible", timeout=10000)

        return search

    except Exception as e:
        screenshot(page, "error_obteniendo_search_paises")
        raise RuntimeError(
            f"No se encontró el Search correcto de países. "
            f"Listbox usado: {SELECTOR_LISTBOX_PAISES}. "
            f"Search usado: {SELECTOR_SEARCH_PAISES}. "
            f"Error: {e}"
        )


def limpiar_search(page, search=None):
    """
    Limpia SOLO el input Search dentro del listbox correcto :r8:.
    """

    try:
        search_real = obtener_search_paises(page)
        search_real.click(timeout=5000)

        try:
            search_real.fill("")
        except:
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")

        page.wait_for_timeout(250)
        return search_real

    except Exception as e:
        screenshot(page, "error_limpiando_search_paises")
        raise RuntimeError(
            f"No se pudo limpiar el Search correcto de países. "
            f"Selector usado: {SELECTOR_SEARCH_PAISES}. Error: {e}"
        )


def escribir_search(page, search, texto):
    """
    Escribe SOLO en el input Search del listbox correcto :r8:.
    """

    try:
        search_real = limpiar_search(page, search)
        search_real.click(timeout=5000)
        search_real.type(texto, delay=35)
        page.wait_for_timeout(900)

        dump_listbox(page, f"busqueda_{texto}")

        return search_real

    except Exception as e:
        screenshot(page, f"error_escribiendo_search_{texto}")
        raise RuntimeError(
            f"No se pudo escribir '{texto}' en el Search correcto de países. "
            f"Selector usado: {SELECTOR_SEARCH_PAISES}. Error: {e}"
        )


def dump_listbox(page, etiqueta=""):
    try:
        listbox = page.locator(SELECTOR_LISTBOX_PAISES).first
        txt = listbox.inner_text(timeout=3000)
        log(f"[LISTBOX DUMP {etiqueta}]\n{txt[:2000]}")
        return txt
    except Exception as e:
        log(f"[LISTBOX DUMP FAIL] {e}")
        return ""


def encontrar_opcion_visible(page, label_candidates, timeout=10000):
    deadline = time.time() + timeout / 1000

    while time.time() < deadline:
        for label in label_candidates:
            xpaths = [
                f"//ul[@role='listbox' and @id=':r8:']//li[normalize-space()='{label}']",
                f"//ul[@role='listbox' and @id=':r8:']//li[contains(normalize-space(), '{label}')]",
                f"//ul[@role='listbox' and @id=':r8:']//*[contains(@role,'option') and normalize-space()='{label}']",
                f"//ul[@role='listbox' and @id=':r8:']//*[contains(@role,'option') and contains(normalize-space(), '{label}')]",
            ]

            for xp in xpaths:
                try:
                    loc = page.locator(f"xpath={xp}").first
                    if loc.count() > 0 and loc.is_visible():
                        return loc, label
                except:
                    pass

        keywords = []
        for label in label_candidates:
            for token in label.replace("LATAM Airlines", "").replace("DFN", "").split():
                token = token.strip()
                if len(token) >= 3:
                    keywords.append(token.lower())

        try:
            lis = page.locator(SELECTOR_OPTIONS_PAISES)

            for i in range(min(lis.count(), 80)):
                li = lis.nth(i)

                try:
                    if not li.is_visible():
                        continue

                    txt = li.inner_text(timeout=1000).strip()
                    txt_low = txt.lower()

                    if any(k in txt_low for k in keywords):
                        return li, txt

                except:
                    pass

        except:
            pass

        page.wait_for_timeout(300)

    return None, None


def opcion_marcada(option):
    try:
        return option.evaluate("""
            option => {
                const input = option.querySelector('input[type="checkbox"]');

                if (input) {
                    if (input.checked === true) return true;
                    if (input.getAttribute('checked') !== null) return true;
                    if (input.getAttribute('aria-checked') === 'true') return true;
                }

                const checked = option.querySelector(
                    '.MuiCheckbox-root.Mui-checked, ' +
                    '[class*="MuiCheckbox-root"][class*="Mui-checked"], ' +
                    '.Mui-checked, ' +
                    '[class*="Mui-checked"], ' +
                    '[aria-checked="true"]'
                );

                if (checked) return true;
                return false;
            }
        """)
    except:
        return False


def leer_estado_pais(page, search, pais_key, intentos=4):
    candidatos = PAISES[pais_key]
    queries = [pais_key] + candidatos

    for intento in range(1, intentos + 1):
        for q in queries:
            try:
                search = escribir_search(page, search, q)

                option, matched = encontrar_opcion_visible(
                    page,
                    candidatos + [pais_key],
                    timeout=3500
                )

                if option is None:
                    log(f"[PAIS] No encontrado {pais_key} buscando {q}, intento {intento}")
                    continue

                estado = opcion_marcada(option)
                log(f"[PAIS] {pais_key} matched={matched} estado={estado}")
                return estado, option

            except Exception as e:
                log(f"[PAIS WARN] leer estado {pais_key} query={q}: {e}")
                page.wait_for_timeout(500)

    raise RuntimeError(f"No se pudo leer estado del país: {pais_key}")


def click_option_checkbox(option, pais_key):
    targets = [
        ".MuiCheckbox-root",
        "input[type='checkbox']",
    ]

    for sel in targets:
        try:
            t = option.locator(sel).first
            if t.count() > 0 and t.is_visible():
                t.click(force=True, timeout=4000)
                log(f"[PAIS CLICK] checkbox {pais_key}")
                return True
        except:
            pass

    try:
        option.click(force=True, timeout=4000)
        log(f"[PAIS CLICK] option {pais_key}")
        return True
    except Exception as e:
        log(f"[PAIS CLICK FAIL] {pais_key}: {e}")
        return False


def marcar_pais(page, search, pais_key):
    for intento in range(1, 5):
        actual, option = leer_estado_pais(page, search, pais_key)

        if actual is True:
            log(f"[MARCAR SKIP] {pais_key} ya ON")
            return True

        click_option_checkbox(option, pais_key)
        page.wait_for_timeout(900)

        nuevo, _ = leer_estado_pais(page, search, pais_key)

        if nuevo is True:
            log(f"[MARCAR OK] {pais_key}")
            return True

    return False


def desmarcar_pais(page, search, pais_key):
    for intento in range(1, 5):
        actual, option = leer_estado_pais(page, search, pais_key)

        if actual is False:
            log(f"[DESMARCAR SKIP] {pais_key} ya OFF")
            return True

        click_option_checkbox(option, pais_key)
        page.wait_for_timeout(900)

        nuevo, _ = leer_estado_pais(page, search, pais_key)

        if nuevo is False:
            log(f"[DESMARCAR OK] {pais_key}")
            return True

    return False


def preparar_paises(page, modo):
    guardar_status(f"Preparando países {modo}")

    if modo == "BRASIL":
        acciones = [
            ("MARCAR", "Brazil"),
            ("DESMARCAR", "Colombia"),
            ("DESMARCAR", "Peru"),
            ("DESMARCAR", "Chile"),
            ("DESMARCAR", "Ecuador"),
        ]

        esperados = {
            "Brazil": True,
            "Colombia": False,
            "Peru": False,
            "Chile": False,
            "Ecuador": False,
        }

    else:
        acciones = [
            ("DESMARCAR", "Brazil"),
            ("MARCAR", "Colombia"),
            ("MARCAR", "Peru"),
            ("MARCAR", "Chile"),
            ("MARCAR", "Ecuador"),
        ]

        esperados = {
            "Brazil": False,
            "Colombia": True,
            "Peru": True,
            "Chile": True,
            "Ecuador": True,
        }

    for intento_global in range(1, 4):
        guardar_status(f"{modo}: ajuste países intento {intento_global}/3")

        try:
            search = abrir_selector_paises(page)
            screenshot(page, f"selector_paises_{modo}_{intento_global}")

            errores = []

            for accion, pais_key in acciones:
                if accion == "MARCAR":
                    ok = marcar_pais(page, search, pais_key)
                else:
                    ok = desmarcar_pais(page, search, pais_key)

                if not ok:
                    errores.append((accion, pais_key))

            if errores:
                log(f"[{modo}] Errores ajustando países:", errores)
                cerrar_selector_paises(page)
                page.wait_for_timeout(1200)
                continue

            errores_validacion = []

            for pais_key, esperado in esperados.items():
                real, _ = leer_estado_pais(page, search, pais_key)

                if real != esperado:
                    errores_validacion.append((pais_key, esperado, real))

            cerrar_selector_paises(page)

            if not errores_validacion:
                guardar_status(f"{modo}: países configurados correctamente")
                screenshot(page, f"paises_{modo}_ok")
                return True

            log(f"[{modo}] Validación falló:", errores_validacion)
            page.wait_for_timeout(1200)

        except Exception as e:
            log(f"[{modo}] Error preparando países:", str(e))
            screenshot(page, f"error_paises_{modo}_{intento_global}")
            cerrar_selector_paises(page)
            page.wait_for_timeout(1200)

    raise RuntimeError(f"No se pudieron preparar países: {modo}")

# ============================================================
# EXPORT
# ============================================================

def abrir_menu_export(page):
    guardar_status("Abriendo menú Export Orders")

    selectors = [
        "text=Export Orders",
        "button:has-text('Export Orders')",
        "span:has-text('Export Orders')",
    ]

    click_first_visible(page, selectors, timeout=25000, descripcion="Export Orders")
    page.wait_for_timeout(1000)


def seleccionar_tipo_export(page, tipo_export):
    guardar_status(f"Seleccionando {tipo_export}")

    selectors = [
        f"div[title='{tipo_export}']",
        f"text={tipo_export}",
        f"[role='menuitem']:has-text('{tipo_export}')",
        f"button:has-text('{tipo_export}')",
    ]

    click_first_visible(page, selectors, timeout=25000, descripcion=tipo_export)
    page.wait_for_timeout(1200)


def confirmar_yes_si_aparece(page):
    for intento in range(1, 5):
        try:
            input_correo = page.locator("input[placeholder*='Add Email Recipient']").first

            if input_correo.count() > 0 and input_correo.is_visible():
                guardar_status("Modal de correos detectado")
                return True

            yes_selectors = [
                "button:has-text('Yes')",
                "span:has-text('Yes')",
                "text=Yes",
            ]

            for sel in yes_selectors:
                loc = page.locator(sel)
                if loc.count() > 0:
                    for i in range(min(loc.count(), 5)):
                        item = loc.nth(i)
                        try:
                            if item.is_visible():
                                guardar_status("Confirmando export con Yes")
                                click_locator_robusto(page, item, descripcion="Yes", timeout=6000)
                                page.wait_for_timeout(1500)
                                return True
                        except:
                            pass

            page.wait_for_timeout(1000)

        except Exception as e:
            log("[YES WARN]", str(e))
            page.wait_for_timeout(1000)

    return True


def agregar_correos(page):
    guardar_status("Agregando correos")

    email_input = page.locator("input[placeholder*='Add Email Recipient']").first
    email_input.wait_for(state="visible", timeout=30000)

    for correo in CORREOS_EXPORT:
        agregado = False

        for intento in range(1, 5):
            try:
                log(f"[CORREO] Agregando {correo}")

                email_input.click(timeout=5000)
                email_input.fill("")
                email_input.type(correo, delay=25)
                page.wait_for_timeout(500)
                page.keyboard.press("Enter")
                page.wait_for_timeout(900)

                agregado = True
                break

            except Exception as e:
                log(f"[CORREO WARN] {correo}: {e}")
                page.wait_for_timeout(1000)
                email_input = page.locator("input[placeholder*='Add Email Recipient']").first

        if not agregado:
            raise RuntimeError(f"No se pudo agregar correo: {correo}")


def completar_subject(page, asunto):
    guardar_status(f"Completando subject: {asunto}")

    selectors = [
        "#Subject",
        "input#Subject",
        "input[name='Subject']",
        "input[placeholder*='Subject']",
    ]

    fill_first_visible(page, selectors, asunto, timeout=30000, descripcion="Subject")
    page.wait_for_timeout(700)


def modal_correo_visible(page):
    try:
        input_correo = page.locator("input[placeholder*='Add Email Recipient']").first
        return input_correo.count() > 0 and input_correo.is_visible()
    except:
        return False


def enviar_email(page):
    guardar_status("Enviando email export")

    screenshot(page, "antes_send_email")

    selectors = [
        "button:has-text('Send Email')",
        "button:has(span:has-text('Send Email'))",
        "span:has-text('Send Email')",
        "text=Send Email",
    ]

    last_error = None
    clicked = False

    for sel in selectors:
        try:
            loc = page.locator(sel)
            count = loc.count()

            for i in range(min(count, 10)):
                btn = loc.nth(i)
                try:
                    if not btn.is_visible():
                        continue

                    log(f"[SEND EMAIL] Intentando selector={sel} index={i}")
                    click_locator_robusto(page, btn, descripcion="Send Email", timeout=8000)
                    clicked = True
                    break

                except Exception as e:
                    last_error = e
                    log(f"[SEND EMAIL WARN] {sel} index={i}: {e}")

            if clicked:
                break

        except Exception as e:
            last_error = e

    if not clicked:
        raise RuntimeError(f"No se pudo clickear Send Email. Último error: {last_error}")

    for intento in range(1, 11):
        page.wait_for_timeout(1200)

        visible = modal_correo_visible(page)
        log(f"[SEND EMAIL] post-click intento {intento}/10 modal_visible={visible}")

        if not visible:
            guardar_status("Send Email enviado / modal cerrado")
            screenshot(page, "send_email_ok_modal_cerrado")
            return True

        ok_text = page_has_text(page, [
            "Email sent",
            "Email Sent",
            "sent successfully",
            "successfully",
            "Your export request",
            "request has been submitted",
        ])

        if ok_text:
            guardar_status(f"Send Email confirmado: {ok_text}")
            screenshot(page, "send_email_confirmado")
            return True

    screenshot(page, "send_email_modal_sigue_visible")
    raise RuntimeError("Se hizo click en Send Email pero el modal siguió visible después de esperar")


def exportar(page, tipo_export, asunto_texto, pais_texto):
    abrir_menu_export(page)
    seleccionar_tipo_export(page, tipo_export)
    confirmar_yes_si_aparece(page)

    page.wait_for_timeout(1500)
    screenshot(page, f"modal_{tipo_export}_{pais_texto}")

    agregar_correos(page)

    fecha_hoy = ahora_chile().strftime("%d-%m-%Y %H:%M:%S")
    asunto = f"{asunto_texto} {fecha_hoy} {pais_texto}"

    completar_subject(page, asunto)

    try:
        page.mouse.click(10, 10)
        page.wait_for_timeout(300)
    except:
        pass

    guardar_status(f"Enviando {tipo_export} - {pais_texto}")
    enviar_email(page)

    screenshot(page, f"enviado_{tipo_export}_{pais_texto}")

# ============================================================
# FLUJO
# ============================================================

def proceso_brasil(page):
    guardar_status("Iniciando exports Brasil")
    preparar_paises(page, "BRASIL")
    page.wait_for_timeout(1500)

    exportar(page, "Export Orders", "Exports orders", "Brasil")
    exportar(page, "Export Details", "Exports details", "Brasil")

    guardar_status("Exports Brasil enviados")


def proceso_otros(page):
    guardar_status("Iniciando exports Otros")
    preparar_paises(page, "OTROS")
    page.wait_for_timeout(1500)

    exportar(page, "Export Orders", "Exports orders", "Otros")
    exportar(page, "Export Details", "Exports details", "Otros")

    guardar_status("Exports Otros enviados")


def main():
    if not DHL_USER or not DHL_PASS:
        raise RuntimeError("Faltan credenciales DHL_USER / DHL_PASS")

    guardar_status("Iniciando bot DHL Playwright")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            slow_mo=120,
            accept_downloads=True,
            viewport={"width": 1920, "height": 1080},
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-notifications",
                "--disable-popup-blocking",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        page = context.pages[0] if context.pages else context.new_page()

        try:
            login_dhl(page)
            esperar_dashboard(page)

            proceso_brasil(page)
            proceso_otros(page)

            guardar_status("TODOS LOS EXPORTS ENVIADOS CORRECTAMENTE")
            screenshot(page, "finalizado_ok")

        except Exception as e:
            guardar_status(f"ERROR: {str(e)}")
            screenshot(page, "error_final")
            raise

        finally:
            page.wait_for_timeout(3000)
            context.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("[ERROR GENERAL]", str(e))
        traceback.print_exc()
        sys.exit(1)
'''

# ============================================================
# GUARDAR BOT
# ============================================================

with open(BOT_PATH, "w", encoding="utf-8") as f:
    f.write(codigo_bot)

print(f"\n✅ Bot Playwright DHL creado en:\n{BOT_PATH}")

# ============================================================
# EJECUTAR BOT CON LOG EN VIVO
# ============================================================

print("\n3️⃣ Ejecutando bot DHL Playwright...")
print("Verás el avance en vivo debajo.\n")

env = os.environ.copy()
env["DHL_USER"] = DHL_USER
env["DHL_PASS"] = DHL_PASS
env["DHL_LOG_DIR"] = LOG_DIR
env["DHL_SCREENSHOT_DIR"] = SCREENSHOT_DIR
env["DHL_STATUS_FILE"] = STATUS_FILE
env["CHILE_TZ"] = CHILE_TZ

log_path = f"{LOG_DIR}/log_dhl_playwright_bot_dhl_playwright.txt"

with open(log_path, "w", encoding="utf-8") as log_file:
    process = subprocess.Popen(
        [sys.executable, BOT_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        bufsize=1,
    )

    for line in process.stdout:
        print(line, end="")
        log_file.write(line)
        log_file.flush()

    return_code = process.wait()

print("\n============================================================")
print("RESULTADO FINAL")
print("============================================================")
print("Código de salida:", return_code)
print("Log:", log_path)
print("Status:", STATUS_FILE)
print("Screenshots:", SCREENSHOT_DIR)

if return_code == 0:
    print("✅ Bot DHL Playwright ejecutado correctamente")
else:
    print("❌ Bot DHL Playwright terminó con error")
    raise RuntimeError(f"Bot DHL Playwright falló con código {return_code}")
