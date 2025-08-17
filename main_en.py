import sys
import os
import json
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets

CONFIG_FILE = "lumen_config.json"

class ConfigManager:
    def __init__(self):
        self.config = {
            "theme": "white",
            "search_engine": "Google",
            "incognito_color": "gray"
        }
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
            except Exception:
                pass

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def get_theme(self):
        return self.config.get("theme", "white")

    def set_theme(self, theme):
        self.config["theme"] = theme
        self.save()

    def get_search_engine(self):
        return self.config.get("search_engine", "Google")

    def set_search_engine(self, engine):
        self.config["search_engine"] = engine
        self.save()

    def get_incognito_color(self):
        return self.config.get("incognito_color", "gray")

    def set_incognito_color(self, color):
        self.config["incognito_color"] = color
        self.save()

class BrowserTab(QtWebEngineWidgets.QWebEngineView):
    def __init__(self, parent=None, incognito=False, incognito_profile=None):
        super().__init__(parent)
        self.incognito = incognito
        if incognito and incognito_profile:
            page = QtWebEngineWidgets.QWebEnginePage(incognito_profile, self)
            self.setPage(page)
        self.page().profile().setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0 Safari/537.36"
        )
        self.page().profile().setHttpAcceptLanguage("en-US,en;q=0.9")

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config_manager):
        super().__init__()
        self.setWindowTitle("Lumen Browser")
        self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
        self.resize(1200, 800)

        self.config_manager = config_manager
        self.search_engine = self.config_manager.get_search_engine()

        self.engines = {
            "Google": "https://www.google.com/ncr/search?q={}",
            "Bing": "https://www.bing.com/?cc=us&q={}",
            "DuckDuckGo": "https://duckduckgo.com/?kl=us-en&q={}",
            "Brave": "https://search.brave.com/search?q={}"
        }

        self.initial_urls = {
            "Google": "https://www.google.com/ncr",
            "Bing": "https://www.bing.com/?cc=us",
            "DuckDuckGo": "https://duckduckgo.com/?kl=us-en",
            "Brave": "https://search.brave.com"
        }

        self.incognito_profile = QtWebEngineWidgets.QWebEngineProfile()
        self.incognito_profile.setPersistentCookiesPolicy(QtWebEngineWidgets.QWebEngineProfile.NoPersistentCookies)
        self.incognito_profile.setCachePath("")
        self.incognito_profile.setPersistentStoragePath("")

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        self.apply_theme()
        self.init_toolbar()
        self.add_tab(self.initial_urls.get(self.search_engine, self.initial_urls["Google"]))

    def init_toolbar(self):
        navtb = QtWidgets.QToolBar("Navigation")
        self.addToolBar(navtb)

        def make_btn(icon_text, tooltip, callback):
            btn = QtWidgets.QPushButton(icon_text)
            btn.setToolTip(tooltip)
            btn.setFixedSize(25, 25)
            btn.setStyleSheet("margin:0px; padding:0px;")
            btn.clicked.connect(callback)
            return btn

        back_btn = make_btn("⭠", "Back", lambda: self.current_browser().back())
        navtb.addWidget(back_btn)

        forward_btn = make_btn("⭢", "Forward", lambda: self.current_browser().forward())
        navtb.addWidget(forward_btn)

        reload_btn = make_btn("⟳", "Reload", lambda: self.current_browser().reload())
        navtb.addWidget(reload_btn)

        home_btn = make_btn("⌂", "Home Page", self.go_home)
        navtb.addWidget(home_btn)

        navtb.addSeparator()

        self.urlbar = QtWidgets.QLineEdit()
        self.urlbar.setPlaceholderText("Type URL or search term")
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        navtb.addWidget(self.urlbar)

        # Search engine menu
        search_btn = make_btn("🔍", "Select search engine", lambda: None)
        self.search_menu = QtWidgets.QMenu()
        self.update_search_menu()
        search_btn.setMenu(self.search_menu)
        navtb.addWidget(search_btn)

        navtb.addSeparator()

        newtab_btn = make_btn("➕", "New tab", lambda: self.add_tab(self.initial_urls["Google"]))
        navtb.addWidget(newtab_btn)

        incognito_btn = make_btn("🕶", "Open/Close incognito tabs", self.toggle_incognito_tab)
        navtb.addWidget(incognito_btn)

        color_btn = make_btn("🎨", "Customize browser color", lambda: self.show_color_menu())
        navtb.addWidget(color_btn)

        # Cookie button
        cookie_btn = QtWidgets.QPushButton("🍪")
        cookie_btn.setToolTip("Cookies")
        cookie_menu = QtWidgets.QMenu()
        delete_action = QtWidgets.QAction("Delete Cookies", self)
        delete_action.triggered.connect(lambda: self.current_browser().page().profile().cookieStore().deleteAllCookies())
        cookie_menu.addAction(delete_action)
        cookie_btn.setMenu(cookie_menu)
        navtb.addWidget(cookie_btn)

    def toggle_incognito_tab(self):
        has_incognito = any(getattr(self.tabs.widget(i), "incognito", False) for i in range(self.tabs.count()))
        if not has_incognito:
            self.add_tab(self.initial_urls["Google"], incognito=True, title="🕶 Incognito")
        else:
            i = self.tabs.count() - 1
            while i >= 0:
                tab = self.tabs.widget(i)
                if getattr(tab, "incognito", False):
                    self.tabs.removeTab(i)
                i -= 1

    def update_search_menu(self):
        self.search_menu.clear()
        for name in self.engines.keys():
            display_name = name + (" ✅" if name == self.search_engine else "")
            action = QtWidgets.QAction(display_name, self)
            action.triggered.connect(lambda checked, n=name: self.select_search_engine(n))
            self.search_menu.addAction(action)

    def select_search_engine(self, name):
        self.search_engine = name
        self.config_manager.set_search_engine(name)
        self.update_search_menu()
        self.current_browser().setUrl(QtCore.QUrl(self.initial_urls.get(name, self.initial_urls["Google"])))

    def show_color_menu(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Choose your color")
        layout = QtWidgets.QGridLayout()
        colors = {
            "white": "background-color: white;",
            "gray": "background-color: #A9A9A9;",
            "blue": "background-color: #1e3c72; color: white;",
            "orange": "background-color: #ff8c00; color: black;",
            "red": "background-color: #B22222; color: white;"
        }
        row, col = 0, 0
        for theme, style in colors.items():
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(50, 50)
            btn.setStyleSheet(style)
            btn.clicked.connect(lambda _, t=theme: self.set_theme(t, dialog))
            layout.addWidget(btn, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
        dialog.setLayout(layout)
        dialog.exec_()

    def set_theme(self, theme, dialog=None):
        self.config_manager.set_theme(theme)
        self.apply_theme()
        if dialog:
            dialog.accept()

    def add_tab(self, url, incognito=False, title=None):
        browser = BrowserTab(incognito=incognito, incognito_profile=self.incognito_profile)
        browser.setUrl(QtCore.QUrl(url))
        i = self.tabs.addTab(browser, title if title else ("🕶 Incognito" if incognito else "New Tab"))
        self.tabs.setCurrentIndex(i)
        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        browser.loadFinished.connect(lambda _, i=i, browser=browser: self.tabs.setTabText(i, browser.page().title() if not incognito else "🕶 Incognito"))
        if incognito:
            color = self.config_manager.get_incognito_color()
            color_map = {
                "white": "white",
                "gray": "#D3D3D3",
                "blue": "#1e3c72",
                "orange": "#ff8c00",
                "red": "#B22222"
            }
            browser.setStyleSheet(f"background-color: {color_map.get(color, '#D3D3D3')};")
        else:
            self.apply_theme()

    def close_tab(self, i):
        self.tabs.removeTab(i)

    def current_browser(self):
        return self.tabs.currentWidget()

    def go_home(self):
        self.current_browser().setUrl(QtCore.QUrl(self.initial_urls["Google"]))

    def navigate_to_url(self):
        q = self.urlbar.text()
        if "." not in q:
            q = self.engines.get(self.search_engine, self.engines["Google"]).format(q)
        self.current_browser().setUrl(QtCore.QUrl(q))

    def update_urlbar(self, q, browser=None):
        if browser != self.current_browser():
            return
        self.urlbar.setText(q.toString())
        self.urlbar.setCursorPosition(0)

    def apply_theme(self):
        theme = self.config_manager.get_theme()
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if getattr(tab, "incognito", False):
                color = self.config_manager.get_incognito_color()
                color_map = {
                    "white": "white",
                    "gray": "#D3D3D3",
                    "blue": "#1e3c72",
                    "orange": "#ff8c00",
                    "red": "#B22222"
                }
                tab.setStyleSheet(f"background-color: {color_map.get(color, '#D3D3D3')};")
            else:
                if theme == "white":
                    tab.setStyleSheet("background-color: white;")
                elif theme == "gray":
                    tab.setStyleSheet("background-color: #A9A9A9;")
                elif theme == "blue":
                    tab.setStyleSheet("background-color: #1e3c72; color: white;")
                elif theme == "orange":
                    tab.setStyleSheet("background-color: #ff8c00; color: black;")
                elif theme == "red":
                    tab.setStyleSheet("background-color: #B22222; color: white;")
        if theme == "white":
            self.setStyleSheet("background-color: white;")
        elif theme == "gray":
            self.setStyleSheet("background-color: #A9A9A9;")
        elif theme == "blue":
            self.setStyleSheet("background-color: #1e3c72; color: white;")
        elif theme == "orange":
            self.setStyleSheet("background-color: #ff8c00; color: black;")
        elif theme == "red":
            self.setStyleSheet("background-color: #B22222; color: white;")

def main():
    app = QtWidgets.QApplication(sys.argv)
    config_manager = ConfigManager()
    window = MainWindow(config_manager)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
