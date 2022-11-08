"""
    create a user_defined class that inherits from the metaclass
    the aim is to create a custom where dataframe can be included flexibly
"""
import pandas as pd
from PyQt5 import QtWidgets, QtCore


def my_format(val: str):
    return f"{float(val):,.2f}"


class TableWidget(QtWidgets.QTableWidget):
    headers = ['secCd', 'basicPrice', 'best1BidQty', 'lastPrice', 'best1OfferQty', 'changePercent',
               'expectedBidQty', 'expectedPriceLow', 'expectedPriceHigh', 'expectedOfferQty', 'targetPercent']

    def __init__(self, df, parent=None):
        QtWidgets.QTableWidget.__init__(self, parent)

        self.df = pd.DataFrame(columns=TableWidget.headers, index=[
            i for i in range(len(df))])

        for header in df.columns:
            self.df[header] = df[header]

        # set table dimension
        self.setColumnCount(len(TableWidget.headers))
        self.setRowCount(100)

        self.setHorizontalHeaderLabels(TableWidget.headers)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        # set row height
        for row in range(self.rowCount()):
            self.setRowHeight(row, 20)

        #  make 0 to 5 columns uneditable
        for row in range(self.rowCount()):
            for col in range(0, 6):
                item = QtWidgets.QTableWidgetItem("")
                item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
                self.setItem(row, col, item)

        # data insertion
        self.display_data()

        self.cellChanged[int, int].connect(self.update_df)

        self.config_table()

    def update_df(self, row, column):
        text = self.item(row, column).text()
        if row < len(self.df):
            self.df.iloc[row, column] = text

    def config_table(self):
        # -------------------CONFIG TABLE FOR STOCK VIEW TAB-------------------
        for col in range(len(self.df)):
            self.setColumnWidth(col, 2)
        self.df['lastPrice'] = self.df['lastPrice'].map('{:.2f}'.format)
        # self.setSortingEnabled(True)

    def display_data(self, start=0, end=10):
        # data insertion
        for row in range(len(self.df)):
            for col in range(start, end + 1):
                item = QtWidgets.QTableWidgetItem()
                if pd.isna(self.df.iloc[row, col]):
                    item.setText("")
                else:
                    item.setText(str(self.df.iloc[row, col]))
                
                if col <= 5:
                    item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
                self.setItem(row, col, item)

    def align_data(self):
        for row in range(len(self.df)):
            # align column 0
            self.item(row, 0).setTextAlignment(int(
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter))

            # align column 1 to 10
            for column in range(1, len(self.df)):
                try:
                    self.item(row, column).setTextAlignment(int(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter))
                except Exception:
                    pass
