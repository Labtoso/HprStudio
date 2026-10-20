import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from hyprstudio.qt import QtWidgets  # noqa: E402
from hyprstudio import widgets  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class PopupPick(unittest.TestCase):
    def test_pick_from_search_popup_reaches_the_page(self):
        """Regression 1.25.1: Auswahl im Such-Popup setzte nur die Anzeige, die Schrift wurde nie übernommen."""
        fc = widgets.FontCombo()
        fams = [fc.itemText(i) for i in range(fc.count())]
        fc.fill(fams[0] if fams else "")
        got = []
        fc.chosen.connect(got.append)
        fc.showPopup()
        pop = fc._pop
        target = next(it for it in pop._visible() if pop.list.row(it) > 0 and fc.itemData(pop.list.row(it))[0] == "font")
        pop.list.itemClicked.emit(target)
        self.assertEqual(got, [target.text()])
        self.assertEqual(fc.value, target.text())

    def test_plain_search_combo_emits_activated(self):
        sc = widgets.SearchCombo()
        sc.addItems(["a", "b", "c"])
        seen = []
        sc.activated.connect(seen.append)
        sc.showPopup()
        sc._pop.list.itemClicked.emit(sc._pop.list.item(2))
        self.assertEqual((sc.currentIndex(), seen), (2, [2]))


if __name__ == "__main__":
    unittest.main()
