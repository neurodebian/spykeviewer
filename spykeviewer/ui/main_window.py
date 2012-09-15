import os
import sys
import json

from PyQt4.QtGui import (QMainWindow, QMessageBox,
                         QApplication, QFileDialog, QInputDialog,
                         QLineEdit, QMenu, QDrag, QPainter, QPen,
                         QPalette, QDesktopServices)
from PyQt4.QtCore import (Qt, pyqtSignature, SIGNAL, QMimeData,
                          QSettings, QCoreApplication)

from spyderlib.widgets.internalshell import InternalShell
from spyderlib.widgets.externalshell.namespacebrowser\
import NamespaceBrowser
from spyderlib.widgets.sourcecode.codeeditor import CodeEditor

from main_ui import Ui_MainWindow
from progress_indicator_dialog import ProgressIndicatorDialog
from ..plugin_framework.data_provider import DataProvider
from ..plugin_framework.analysis_plugin import AnalysisPlugin

#noinspection PyCallByClass,PyTypeChecker,PyArgumentList
class MainWindow(QMainWindow, Ui_MainWindow):
    """ The main window of SpikeViewer
    """

    def __init__(self, parent = None):
        QMainWindow.__init__(self, parent)

        QCoreApplication.setOrganizationName('SpykeUtils')
        QCoreApplication.setApplicationName('Spyke Viewer')

        self.setupUi(self)
        self.dir = os.getcwd()
        self.console = None
        self.progress = ProgressIndicatorDialog(self)
        self.provider_factory = DataProvider
        self.selections = []
        self.provider = None
        self.plugin_paths = []

        # Drag and Drop for selections menu
        self.menuSelections.setAcceptDrops(True)
        self.menuSelections.paintEvent =\
            self.on_menuSelections_paint
        self.menuSelections.mousePressEvent =\
            self.on_menuSelections_mousePressed
        self.menuSelections.mouseMoveEvent =\
            self.on_menuSelections_mouseMoved
        self.menuSelections.dragEnterEvent =\
            self.on_menuSelections_dragEnter
        self.menuSelections.dragMoveEvent =\
            self.on_menuSelections_dragMoved
        self.menuSelections.dropEvent =\
            self.on_menuSelections_drop

        self.seldrag_start_pos = None
        self.seldrag_selection = None
        self.seldrag_target = None
        self.seldrag_target_upper = False

        # Docks
        self.setCentralWidget(None)

        # A lot of docks are only needed for the internal database mode
        self.navigationDBDock.setVisible(False)
        self.filterDBDock.setVisible(False)
        self.spikeSortingDock.setVisible(False)
        self.waveformsDock.setVisible(False)
        self.spikeTrainDock.setVisible(False)

        if not hasattr(self, 'internal_database_mode'):
            self.removeDockWidget(self.navigationDBDock)
            self.removeDockWidget(self.filterDBDock)
            self.removeDockWidget(self.spikeSortingDock)
            self.removeDockWidget(self.waveformsDock)
            self.removeDockWidget(self.spikeTrainDock)

            del self.navigationDBDock
            del self.filterDBDock
            del self.spikeSortingDock
            del self.waveformsDock
            del self.spikeTrainDock

        self.update_view_menu()

        if not hasattr(self, 'internal_database_mode'):
            self.restore_state()

        self.mode_switch()


    def update_view_menu(self):
        self.menuBar.clear()
        self.menuBar.addMenu(self.menuFile)
        self.menuBar.addMenu(self.menuSelections)
        self.menuView = self.createPopupMenu()
        self.menuView.setTitle('View')
        self.menuBar.addMenu(self.menuView)
        self.menuBar.addMenu(self.menuHelp)


    def restore_state(self):
        settings = QSettings()
        if not settings.contains('windowGeometry') or\
           not settings.contains('windowState'):
            self.set_initial_layout()
        else:
            self.restoreGeometry(settings.value('windowGeometry'))
            self.restoreState(settings.value('windowState'))

        if not settings.contains('pluginPaths'):
            if hasattr(sys, 'frozen'):
                module_path = os.path.dirname(sys.executable)
            else:
                file_path = os.path.abspath(os.path.dirname(__file__))
                module_path = os.path.dirname(os.path.dirname(file_path))
            plugin_path = os.path.join(module_path, 'plugins')
            if os.path.isdir(plugin_path):
                self.plugin_paths.append(plugin_path)
        else:
            paths = settings.value('pluginPaths')
            if paths is None:
                self.plugin_paths = []
            else:
                self.plugin_paths = paths

        if not settings.contains('selectionPath'):
            data_path = QDesktopServices.storageLocation(
                QDesktopServices.DataLocation)
            self.selection_path = os.path.join(data_path, 'selections')
        else:
            self.selection_path = settings.value('selectionPath')

        if not settings.contains('dataPath'):
            data_path = QDesktopServices.storageLocation(
                QDesktopServices.DataLocation)
            AnalysisPlugin.data_dir = os.path.join(data_path, 'data')
        else:
            AnalysisPlugin.data_dir = settings.value('dataPath')

        if not settings.contains('remoteScript'):
            if hasattr(sys, 'frozen'):
                path = os.path.dirname(sys.executable)
            else:
                file_path = os.path.abspath(os.path.dirname(__file__))
                path = os.path.dirname(os.path.dirname(file_path))
                path = os.path.join(path, 'bin')
            self.remote_script = os.path.join(path, 'spykeview_analysis')
        else:
            self.remote_script = settings.value('remoteScript')


    def set_initial_layout(self):
        self.setGeometry(self.x(), self.y(), 800, 750)
        self.navigationNeoDock.setVisible(True)

        self.removeDockWidget(self.filterDock)
        self.removeDockWidget(self.analysisDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.filterDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.analysisDock)
        self.tabifyDockWidget(self.filterDock, self.analysisDock)
        self.filterDock.setVisible(True)
        self.analysisDock.setVisible(True)

        self.consoleDock.setVisible(False)
        self.variableExplorerDock.setVisible(False)
        self.historyDock.setVisible(False)
        self.tabifyDockWidget(self.consoleDock, self.variableExplorerDock)
        self.tabifyDockWidget(self.variableExplorerDock, self.historyDock)


    def mode_switch(self):
        if self.is_db_mode():
            self.switch_to_db_mode()
        if self.is_neo_mode():
            self.switch_to_neo_mode()

        if self.console:
            self.console.interpreter.locals['current'] = self.provider


    def switch_to_db_mode(self):
        raise NotImplementedError()


    def switch_to_neo_mode(self):
        raise NotImplementedError()


    def _init_python_tab(self):
        # Console
        ns = {'current': self.provider, 'selections': self.selections}
        cmds = """
from __future__ import division
import scipy as sp
import numpy as np
import matplotlib.pyplot as plt
import guiqwt
import guiqwt.pyplot as guiplt
import guidata
import spykeutils
import spykeviewer
plt.ion()
""".split('\n')
        self.console = InternalShell(self.consoleDock, namespace=ns,
            multithreaded=False, commands=cmds, max_line_count=1000)
        self.consoleDock.setWidget(self.console)
        self.console.clear_terminal()

        # Variable browser
        self.browser = NamespaceBrowser(self.variableExplorerDock)
        self.browser.set_shellwidget(self.console)
        self.browser.setup(check_all=True, exclude_private=True,
            exclude_uppercase=False, exclude_capitalized=False,
            exclude_unsupported=True, excluded_names=[],
            truncate=False, minmax=False, collvalue=False,
            remote_editing=False, inplace=False, autorefresh=False)
        self.variableExplorerDock.setWidget(self.browser)

        # History
        self.history = CodeEditor(self.historyDock)
        self.history.setup_editor(linenumbers=False, language='py',
            scrollflagarea=False)
        self.history.setReadOnly(True)
        self.history.set_text('\n'.join(self.console.history))
        self.history.set_cursor_position('eof')
        self.historyDock.setWidget(self.history)
        self.console.connect(self.console, SIGNAL("refresh()"),
            self._append_python_history)


    def _append_python_history(self):
        self.browser.refresh_table()
        self.history.append('\n' + self.console.history[-1])
        self.history.set_cursor_position('eof')


    def is_neo_mode(self):
        return True


    def is_db_mode(self):
        return False


    @pyqtSignature("")
    def on_actionExit_triggered(self):
        self.close()


    def on_menuHelp_triggered(self):
        QMessageBox.about(self, 'How to navigate plots',
            'Zoom:\tHold right mouse button' +
            '\nTranslate:\tHold middle mouse button' +
            '\nHome:\tClick middle mouse button' +
            '\n\nAxis synchronization does not work with some actions. ' +
            'Zoom or translate changed plot to synchronize.')


    def on_menuSelections_mousePressed(self, event):
        if event.button() == Qt.LeftButton:
            action = self.menuSelections.actionAt(event.pos())
            if action:
                selection = action.data()
                if selection:
                    self.seldrag_start_pos = event.pos()
                    self.seldrag_selection = selection
        else:
            self.seldrag_start_pos = None
            self.seldrag_selection = None
            self.seldrag_target = None
        QMenu.mousePressEvent(self.menuSelections, event)


    def on_menuSelections_mouseMoved(self, event):
        if event.buttons() & Qt.LeftButton and self.seldrag_start_pos:
            if ((event.pos() - self.seldrag_start_pos).manhattanLength() >=
                QApplication.startDragDistance()):
                drag = QDrag(self.menuSelections)
                data = QMimeData()
                data.setText(self.seldrag_selection.name)
                drag.setMimeData(data)
                drag.exec_()
                self.seldrag_start_pos = None
                self.seldrag_selection = None
                self.seldrag_target = None
        QMenu.mouseMoveEvent(self.menuSelections, event)


    def on_menuSelections_paint(self, event):
        QMenu.paintEvent(self.menuSelections, event)
        if self.seldrag_target:
            # Paint line where selection will be dropped
            p = QPainter()
            color = QPalette().color(self.menuSelections.foregroundRole())
            pen = QPen(color, 2, Qt.SolidLine)
            p.begin(self.menuSelections)
            p.setPen(pen)
            rect = self.menuSelections.actionGeometry(self.seldrag_target)
            if self.seldrag_target_upper:
                p.drawLine(rect.topLeft(), rect.topRight())
            else:
                p.drawLine(rect.bottomLeft(), rect.bottomRight())
            p.end()


    def _menuSelections_pos_is_drop_target(self, pos):
        """ Return if selection can be dropped at this position and
            prepare information needed for drawing and dropping
        """
        action = self.menuSelections.actionAt(pos)
        if not action or not action.data():
            self.seldrag_target = None
            return False

        self.seldrag_target = action
        rect = self.menuSelections.actionGeometry(action)
        if pos.y() < rect.top() + rect.height() / 2:
            self.seldrag_target_upper = True
        else:
            self.seldrag_target_upper = False
        return True


    def on_menuSelections_dragEnter(self, event):
        event.setDropAction(Qt.MoveAction)
        if self._menuSelections_pos_is_drop_target(event.pos()):
            event.accept()
        else:
            event.ignore()

        QMenu.dragEnterEvent(self.menuSelections, event)


    def on_menuSelections_dragMoved(self, event):
        event.setDropAction(Qt.MoveAction)
        if self._menuSelections_pos_is_drop_target(event.pos()):
            event.accept()
            self.menuSelections.update()
        else:
            event.ignore()

        QMenu.dragMoveEvent(self.menuSelections, event)


    def on_menuSelections_drop(self, event):
        source = self.seldrag_selection
        target = self.seldrag_target.data()
        if source != target:
            self.selections.remove(source)
            target_index = self.selections.index(target)
            if not self.seldrag_target_upper:
                target_index += 1
            self.selections.insert(target_index, source)
            self.populate_selection_menu()

        QMenu.dropEvent(self.menuSelections, event)


    def populate_selection_menu(self):
        self.menuSelections.clear()
        a = self.menuSelections.addAction('New')
        a.triggered.connect(self.on_selection_new)
        a = self.menuSelections.addAction('Clear')
        a.triggered.connect(self.on_selection_clear)
        self.menuSelections.addSeparator()

        for i, s in enumerate(self.selections):
            m = self.menuSelections.addMenu(s.name)
            m.menuAction().setData(s)

            a = m.addAction('Load')
            self.connect(a, SIGNAL('triggered()'),
                lambda sel=s:self.on_selection_load(sel))

            a = m.addAction('Save')
            self.connect(a, SIGNAL('triggered()'),
                lambda sel=s:self.on_selection_save(sel))

            a = m.addAction('Rename')
            self.connect(a, SIGNAL('triggered()'),
                lambda sel=s:self.on_selection_rename(sel))

            a = m.addAction('Remove')
            self.connect(a, SIGNAL('triggered()'),
                lambda sel=s:self.on_selection_remove(sel))


    def on_selection_load(self, selection):
        self.set_current_selection(selection.data_dict())


    def on_selection_save(self, selection):
        i = self.selections.index(selection)
        self.selections[i] = self.provider_factory(
            self.selections[i].name, self)
        self.populate_selection_menu()

    def on_selection_clear(self):
        if QMessageBox.question(self, 'Confirmation',
            'Do you really want to remove all selections?',
            QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return

        del self.selections[:]
        self.populate_selection_menu()

    def on_selection_rename(self, selection):
        (name, ok) = QInputDialog.getText(self, 'Edit selection name',
            'New name:', QLineEdit.Normal, selection.name)
        if ok and name:
            selection.name = name
            self.populate_selection_menu()


    def on_selection_remove(self, selection):
        if QMessageBox.question(self, 'Confirmation',
            'Do you really want to remove the selection "%s"?' %
            selection.name,
            QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return

        self.selections.remove(selection)
        self.populate_selection_menu()


    def on_selection_new(self):
        self.selections.append(self.provider_factory('Selection %d' %
                                                     (len(self.selections) + 1), self))
        self.populate_selection_menu()


    def serialize_selections(self):
        sl = list() # Selection list, current selection as first item
        sl.append(self.provider_factory('current', self).data_dict())
        for s in self.selections:
            sl.append(s.data_dict())
        return json.dumps(sl, sort_keys=True, indent=2)


    def save_selections_to_file(self, filename):
        f = open(filename, 'w')
        f.write(self.serialize_selections())
        f.close()


    def load_selections_from_file(self, filename):
        try:
            f = open(filename, 'r')
            p = json.load(f)
            # First selection in file is current selection
            self.set_current_selection(p[0])
            for s in p[1:]:
                self.add_selection(s)
            f.close()
            self.populate_selection_menu()
        except Exception, e:
            self.progress.done()
            QMessageBox.critical(self, 'Error loading selection',
                str(e).decode('utf8'))


    def on_menuFile_triggered(self, action):
        if action == self.actionSave_selection:
            d = QFileDialog(self, 'Choose where to save selection',
                self.selection_path)
            d.setAcceptMode(QFileDialog.AcceptSave)
            d.setNameFilter("Selection files (*.sel)")
            d.setDefaultSuffix('sel')
            if d.exec_():
                filename = str(d.selectedFiles()[0])
            else:
                return

            self.save_selections_to_file(filename)
        elif action == self.actionLoad_selection:
            d = QFileDialog(self, 'Choose selection file',
                self.selection_path)
            d.setAcceptMode(QFileDialog.AcceptOpen)
            d.setFileMode(QFileDialog.ExistingFile)
            d.setNameFilter("Selection files (*.sel)")
            if d.exec_():
                filename = str(d.selectedFiles()[0])
            else:
                return

            self.load_selections_from_file(filename)


    def set_current_selection(self, data):
        """ Set the selection of a provider
        """
        if data['type'] == 'DB':
            self.set_db_selection(data)
        elif data['type'] == 'Neo':
            self.set_neo_selection(data)


    def add_selection(self, data):
        """ Add a provider with the given data
        """
        if data['type'] == 'DB':
            self.add_db_selection(data)
        elif data['type'] == 'Neo':
            self.add_neo_selection(data)


    def set_db_selection(self, data):
        pass


    def closeEvent(self, event):
        """ Saves filters and GUI state
        """
        # Ensure that filters folder exists
        if not os.path.exists(self.selection_path):
            try:
                os.makedirs(self.selection_path)
            except OSError:
                QMessageBox.critical(self, 'Error',
                    'Could not create selection directory!')

        self.save_selections_to_file(
            os.path.join(self.selection_path, '.current.sel'))

        # Save GUI configuration (docks and toolbars)
        settings = QSettings()
        settings.setValue('windowGeometry', self.saveGeometry())
        settings.setValue('windowState', self.saveState())

        # Save further configurations
        settings.setValue('pluginPaths', self.plugin_paths)
        settings.setValue('selectionPath', self.selection_path)
        settings.setValue('filterPath', self.filter_path)
        settings.setValue('remoteScript', self.remote_script)

        super(MainWindow, self).closeEvent(event)


    def on_consoleDock_visibilityChanged(self, visible):
        if visible and not self.console:
            self._init_python_tab()


    def on_variableExplorerDock_visibilityChanged(self, visible):
        if visible:
            if not self.console:
                self._init_python_tab()
            self.browser.refresh_table()


    def on_historyDock_visibilityChanged(self, visible):
        if visible:
            if not self.console:
                self._init_python_tab()
            self.history.set_cursor_position('eof')
