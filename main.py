
import sys
import os

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QToolBar,
    QLineEdit,
    QTabWidget,
    QStatusBar
)
from PySide6.QtGui import QAction
from PySide6.QtWebEngineWidgets import QWebEngineView


HOME_PAGE = os.path.abspath("home.html")


class ZeroBrowser(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ZERO Browser")
        self.resize(1280, 800)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)

        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)

        self.setCentralWidget(self.tabs)

        toolbar = QToolBar("ZERO Navigation")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        back = QAction("←", self)
        back.triggered.connect(
            lambda: self.current_browser().back()
        )
        toolbar.addAction(back)

        forward = QAction("→", self)
        forward.triggered.connect(
            lambda: self.current_browser().forward()
        )
        toolbar.addAction(forward)

        reload = QAction("⟳", self)
        reload.triggered.connect(
            lambda: self.current_browser().reload()
        )
        toolbar.addAction(reload)

        home = QAction("⌂", self)
        home.triggered.connect(self.go_home)
        toolbar.addAction(home)

        self.address = QLineEdit()
        self.address.setPlaceholderText(
            "Search or enter address..."
        )
        self.address.returnPressed.connect(self.navigate)

        toolbar.addWidget(self.address)

        new_tab = QAction("+", self)
        new_tab.triggered.connect(self.add_tab)
        toolbar.addAction(new_tab)

        self.setStatusBar(QStatusBar())

        self.setStyleSheet("""
            QMainWindow {
                background: #050b18;
            }

            QToolBar {
                background: #071225;
                border: none;
                spacing: 8px;
                padding: 8px;
            }

            QToolButton {
                color: #65baff;
                font-size: 20px;
                padding: 6px;
            }

            QLineEdit {
                background: #102442;
                color: white;
                border: 1px solid #2875bd;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }

            QTabWidget::pane {
                border: none;
            }

            QTabBar::tab {
                background: #09172c;
                color: #9bb9dc;
                padding: 10px 20px;
            }

            QTabBar::tab:selected {
                background: #123d70;
                color: white;
            }
        """)

        self.add_tab()

    def current_browser(self):
        return self.tabs.currentWidget()

    def add_tab(self):
        browser = QWebEngineView()

        index = self.tabs.addTab(browser, "ZERO Home")
        self.tabs.setCurrentIndex(index)

        browser.urlChanged.connect(
            lambda url, b=browser:
            self.update_address(url, b)
        )

        browser.titleChanged.connect(
            lambda title, b=browser:
            self.update_title(title, b)
        )

        browser.loadFinished.connect(
            lambda ok: self.statusBar().showMessage(
                "Page loaded" if ok else "Page loading failed",
                3000
            )
        )

        browser.setUrl(QUrl.fromLocalFile(HOME_PAGE))

    def close_tab(self, index):
        if self.tabs.count() == 1:
            return

        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        widget.deleteLater()

    def navigate(self):
        text = self.address.text().strip()

        if not text:
            return

        first_part = text.split("/")[0]

        if "://" in text:
            url = text

        elif "." in first_part:
            url = "https://" + text

        else:
            url = (
                "https://duckduckgo.com/?q="
                + text.replace(" ", "+")
            )

        self.current_browser().setUrl(QUrl(url))

    def go_home(self):
        self.current_browser().setUrl(
            QUrl.fromLocalFile(HOME_PAGE)
        )

    def update_address(self, url, browser):
        if browser != self.current_browser():
            return

        if url.isLocalFile():
            self.address.clear()
            self.address.setPlaceholderText(
                "Search or enter address..."
            )
        else:
            self.address.setText(url.toString())

    def update_title(self, title, browser):
        index = self.tabs.indexOf(browser)

        if index >= 0:
            self.tabs.setTabText(
                index,
                title[:20] or "New Tab"
            )

            if browser == self.current_browser():
                self.setWindowTitle(
                    title + " — ZERO Browser"
                )

    def current_tab_changed(self, index):
        browser = self.current_browser()

        if browser:
            self.update_address(browser.url(), browser)


app = QApplication(sys.argv)
app.setApplicationName("ZERO Browser")

window = ZeroBrowser()
window.show()

sys.exit(app.exec())
