import sys
import requests
import re
import time
from colorama import Fore
import colorama
colorama.init()

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QLineEdit, QListWidget, QFrame,
    QStackedWidget, QListWidgetItem, QMenu, QComboBox
)

from PyQt6.QtGui import QPixmap, QDesktopServices, QAction, QFont, QIcon
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal


# ---------------- STEAM ID ----------------
def extract_steamid(url):
    match = re.search(r"(\d{17})", url)
    return match.group(1) if match else url


def validate_steam_id_exists(steamid):
    url = f"https://steamcommunity.com/profiles/{steamid}/"
    try:
        r = requests.get(url, timeout=5)
        return "The specified profile could not be found" not in r.text
    except:
        return False


# ---------------- STEAM API ----------------
def get_cs2_inventory(steamid):
    url = f"https://steamcommunity.com/inventory/{steamid}/730/2?l=english&count=10"

    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()

        if not data.get("success"):
            return []

        desc_map = {
            (d["classid"], d["instanceid"]): d
            for d in data.get("descriptions", [])
        }

        items = []

        for asset in data.get("assets", []):
            key = (asset["classid"], asset["instanceid"])
            desc = desc_map.get(key)

            if not desc:
                continue

            name = desc.get("market_hash_name")
            icon = desc.get("icon_url")

            if name and icon:
                img = f"https://community.cloudflare.steamstatic.com/economy/image/{icon}"
                items.append((name, img))

        return items

    except:
        return []


import requests

def get_price(item_name):
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {
        "appid": 730,
        "currency": 3,
        "market_hash_name": item_name
    }

    try:
        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            print(f"[PRICE ERROR] HTTP {r.status_code} for {item_name}")
            print(r.text)
            return "0"

        try:
            data = r.json()
        except Exception as e:
            print(f"[PRICE ERROR] JSON decode failed for {item_name}")
            print("Raw response:", r.text)
            print("Error:", e)
            return "0"

        if not isinstance(data, dict):
            print(f"[PRICE ERROR] Unexpected response type for {item_name}")
            print(data)
            return "0"

        if not data.get("success", False):
            print(f"[PRICE ERROR] Steam API failure for {item_name}")
            print(data.get("error", "No error field"))
            return "0"

        price = data.get("lowest_price") or data.get("median_price")

        if not price:
            print(f"[PRICE WARN] No price returned for {item_name}")
            print(data)
            return "0"

        return price

    except requests.RequestException as e:
        print(f"[NETWORK ERROR] Request failed for {item_name}")
        print(e)
        return "0"

    except Exception as e:
        print(f"[UNKNOWN ERROR] {item_name}")
        print(e)
        return "0"


# ---------------- THREAD WORKER ----------------
class InventoryWorker(QThread):
    done = pyqtSignal(list, float)

    def __init__(self, steamid):
        super().__init__()
        self.steamid = steamid

    def run(self):
        items = get_cs2_inventory(self.steamid)

        result = []
        total = 0.0

        for name, img in items:
            time.sleep(0.1)
            price = get_price(name)

            print(f"Checking price for: {Fore.GREEN}{name}{Fore.RESET}")

            try:
                total += float(price.replace("$", "").replace("€", "").replace(",", "."))
            except:
                pass

            result.append((name, img, price))

        self.done.emit(result, total)


# ---------------- UI ----------------
def create_item_widget(text, image_url):
    widget = QWidget()
    layout = QHBoxLayout(widget)

    img = QLabel()
    img.setFixedSize(64, 48)

    try:
        r = requests.get(image_url, timeout=5)
        pixmap = QPixmap()
        pixmap.loadFromData(r.content)
        img.setPixmap(pixmap.scaled(64, 48, Qt.AspectRatioMode.KeepAspectRatio))
    except:
        pass

    label = QLabel(text)

    layout.addWidget(img)
    layout.addWidget(label)

    return widget


# ---------------- STYLE ----------------
DARK = """
QWidget {
    background-color: #121212;
    color: #eaeaea;
    font-size: 13px;
}

QLineEdit {
    background-color: #1e1e1e;
    border: 1px solid #2a2a2a;
    padding: 8px;
    border-radius: 6px;
}

QListWidget {
    background-color: #161616;
    border: 1px solid #2a2a2a;
}

/* Buttons */
QPushButton {
    background-color: #1f1f1f;
    border: 1px solid #2a2a2a;
    padding: 10px;
    border-radius: 8px;
    text-align: left;
}

QPushButton:hover {
    background-color: #2a2a2a;
}

/* Scrollbar */
QScrollBar:vertical {
    background: #121212;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #3a3a3a;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #555;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ComboBox */
QComboBox {
    background-color: #1e1e1e;
    border: 1px solid #2a2a2a;
    padding: 6px 10px;
    border-radius: 8px;
}

QComboBox:hover {
    border: 1px solid #444;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid #2a2a2a;
    selection-background-color: #3a3a3a;
}
"""

LIGHT = """
QWidget {
    background-color: #f2f2f2;
    color: #111;
    font-size: 13px;
}

QLineEdit {
    background-color: #ffffff;
    border: 1px solid #ccc;
    padding: 8px;
    border-radius: 6px;
}

QListWidget {
    background-color: #ffffff;
    border: 1px solid #ccc;
}

/* Buttons */
QPushButton {
    background-color: #e6e6e6;
    border: 1px solid #ccc;
    padding: 10px;
    border-radius: 8px;
    text-align: left;
}

QPushButton:hover {
    background-color: #dcdcdc;
}

/* Scrollbar */
QScrollBar:vertical {
    background: #f2f2f2;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #bdbdbd;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #9e9e9e;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ComboBox */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #ccc;
    padding: 6px 10px;
    border-radius: 8px;
}

QComboBox:hover {
    border: 1px solid #999;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #ccc;
    selection-background-color: #dcdcdc;
}
"""


ACTIVE_BTN_DARK = """
QPushButton {
    background-color: #3a3a3a;
    border: 1px solid #555;
    font-weight: bold;
}
"""

ACTIVE_BTN_LIGHT = """
QPushButton {
    background-color: #d0d0d0;
    border: 1px solid #999;
    font-weight: bold;
}
"""


# ---------------- MAIN ----------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Steam Inventory Price Checker")
        self.setGeometry(100, 100, 1100, 650)

        self.items_data = []
        self.current_theme = "Dark"
        self.active_btn = None

        root = QWidget()
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)

        self.sidebar = self.create_sidebar()

        self.stack = QStackedWidget()
        self.page_inventory = self.create_inventory_page()
        self.page_settings = self.create_settings_page()

        self.stack.addWidget(self.page_inventory)
        self.stack.addWidget(self.page_settings)

        layout.addWidget(self.sidebar, 1)
        layout.addWidget(self.stack, 4)

        self.setStyleSheet(DARK)
        self.show_inventory()

    # ---------------- SIDEBAR ----------------
    def create_sidebar(self):
        box = QFrame()
        layout = QVBoxLayout(box)

        title = QLabel("SIPC")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #b0b0b0; border: none;")
        layout.addWidget(separator)

        layout.addWidget(separator)

        self.btn_inventory = QPushButton("Inventory Price Checker")
        self.btn_settings = QPushButton("Settings")

        self.btn_inventory.clicked.connect(self.show_inventory)
        self.btn_settings.clicked.connect(self.show_settings)

        layout.addWidget(self.btn_inventory)
        layout.addStretch()
        layout.addWidget(self.btn_settings)

        return box

    # ---------------- PAGES ----------------
    def create_inventory_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        self.input = QLineEdit()
        self.input.setPlaceholderText("SteamID or URL")

        self.search = QPushButton("Search")
        self.search.clicked.connect(self.load_inventory)

        self.list = QListWidget()
        self.total = QLabel("Total: $0.00")

        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.open_menu)

        layout.addWidget(self.input)
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        layout.addWidget(self.total)

        return page

    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light"])
        self.theme.currentTextChanged.connect(self.change_theme)

        layout.addWidget(QLabel("Settings"))
        layout.addWidget(self.theme)
        layout.addStretch()

        return page

    # ---------------- THREAD LOAD ----------------
    def load_inventory(self):
        steamid = self.input.text()

        if steamid.startswith("http"):
            steamid = extract_steamid(steamid)

        if not validate_steam_id_exists(steamid):
            self.list.clear()
            self.list.addItem("Profile not found")
            return

        self.worker = InventoryWorker(steamid)
        self.worker.done.connect(self.render_inventory)
        self.worker.start()

    def render_inventory(self, items, total):
        self.list.clear()
        self.items_data = []

        for name, img, price in items:
            self.items_data.append(name)

            widget = create_item_widget(f"{name} - {price}", img)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())

            self.list.addItem(item)
            self.list.setItemWidget(item, widget)

        self.total.setText(f"Total: {total:.2f}€")

    # ---------------- MENU ----------------
    def open_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return

        index = self.list.row(item)
        name = self.items_data[index]

        menu = QMenu()

        open_market = QAction("Open Market", self)
        copy_name = QAction("Copy Name", self)

        open_market.triggered.connect(lambda: QDesktopServices.openUrl(
            QUrl(f"https://steamcommunity.com/market/listings/730/{name}")
        ))

        copy_name.triggered.connect(lambda: QApplication.clipboard().setText(name))

        menu.addAction(open_market)
        menu.addAction(copy_name)
        menu.exec(self.list.mapToGlobal(pos))

    # ---------------- NAV ----------------
    def show_inventory(self):
        self.stack.setCurrentWidget(self.page_inventory)
        self.set_active(self.btn_inventory)

    def show_settings(self):
        self.stack.setCurrentWidget(self.page_settings)
        self.set_active(self.btn_settings)

    def set_active(self, btn):
        self.btn_inventory.setStyleSheet("")
        self.btn_settings.setStyleSheet("")

        self.active_btn = btn

        if self.current_theme == "Dark":
            btn.setStyleSheet(ACTIVE_BTN_DARK)
        else:
            btn.setStyleSheet(ACTIVE_BTN_LIGHT)

    # ---------------- THEME ----------------
    def change_theme(self, value):
        self.current_theme = value
        self.setStyleSheet(DARK if value == "Dark" else LIGHT)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    font = QFont("Segoe UI", 12)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

    app.setFont(font)

    #icon = QIcon("icon/SIPC.png")

    #app.setWindowIcon(icon)

    window = MainWindow()
    #window.setWindowIcon(icon)

    window.show()

    sys.exit(app.exec())