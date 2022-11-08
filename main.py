import sys

import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThreadPool
from PyQt5.QtGui import QKeySequence, QColor
import numpy as np

import utils
from emailMachine import EmailMachine
from mainWindow import UiMainWindow
from scrapeMachine import Scraper, IndexThread
from tableWidget import TableWidget

STOCKS = utils.get_old_data()
NAME_STOCKS = utils.get_stock_list()
EMAIL_CHECKED = [0 for _ in range(100)]


class MyWindow(UiMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        self.setup_ui()
        self.connect_function()
        self.closeEvent = self.close_event

    def connect_function(self):
        self.add_stock_button.clicked.connect(self.add_stock)
        self.delete_stock_button.clicked.connect(self.delete_stock)
        self.add_wishlist.clicked.connect(self.add_wishlist_func)
        self.remove_wishlist.clicked.connect(self.remove_wishlist_func)
        self.hide_button.clicked.connect(self.hide_column)
        self.super_button.clicked.connect(self.ninja_mode)
        self.wishlist_combo.activated.connect(self.switch_wishlist)
        # self.index_email_checkbox.stateChanged.connect(self.send_email_vnindex)

        # create key shortcut
        self.ninja_mode_shortcut = QtWidgets.QShortcut(
            QKeySequence("Ctrl+S"), self)
        self.ninja_mode_shortcut.activated.connect(self.ninja_mode)

        self.delete_stock_shortcut = QtWidgets.QShortcut(
            QKeySequence("Del"), self)
        self.delete_stock_shortcut.activated.connect(self.delete_stock)

        self.create_threadpool()

    def add_stock(self) -> None:
        global STOCKS
        index = self.stacked_widget.currentIndex()
        new_stock = self.stock_input.text().upper()
        if new_stock == "" or new_stock not in NAME_STOCKS:
            self.stock_input.setText("")
            self.stock_input.setPlaceholderText("Please input stock code")
            return

        if new_stock not in self.stock_view[index].df['secCd'].tolist():
            # add new stock to stock_view[index].df
            new_row = [new_stock, "", "", "", "", ""]
            try:
                self.stock_view[index].df.loc[len(
                    self.stock_view[index].df)] = new_row
            except ValueError:
                print("row mismatched")

            # set empty string for stock input
            self.stock_input.setText("")
        else:
            self.stock_input.setText("")
            self.stock_input.setPlaceholderText("Stock already in list")

    def delete_stock(self) -> None:
        global STOCKS
        # delete stock when select row and press del key
        index = self.stacked_widget.currentIndex()
        row = self.stock_view[index].currentRow()
        if row == -1:
            return
        try:
            self.stock_view[index].removeRow(row)
            self.stock_view[index].df = self.stock_view[index].df.drop(row)

            # re index stock_view[index].df
            self.stock_view[index].df.reset_index(drop=True, inplace=True)
        except Exception as e:
            note = " in delete stock"
            utils.save_error_log(str(e) + note)

        # lack of remove stock by click delete button

    def hide_column(self):
        # HIDE COLUMN 1 6 8 9 10
        list_col_hide = [0, 5, 7, 8, 9]
        index = self.stacked_widget.currentIndex()
        is_visible = self.setting_view[index].isVisible()
        if is_visible:
            for i in list_col_hide:
                self.stock_view[index].setColumnHidden(i, True)
        else:
            for i in list_col_hide:
                self.stock_view[index].setColumnHidden(i, False)

        # hide setting view
        self.setting_view[index].setVisible(not is_visible)

    def close_event(self, event):
        global STOCKS

        print("closing")
        utils.STOP_SIGNAL = True

        # save all values in columns 6 7 8 9
        for index in range(len(STOCKS.keys())):
            # get wishlist combo text base on index
            name = self.wishlist_combo.itemText(index)
            df = self.stock_view[index].df

            # drop columns 1 to 5
            df = df.drop(columns=['basicPrice', 'best1BidQty',
                                  'lastPrice', 'best1OfferQty', 'changePercent'])
            STOCKS[name] = df.to_dict(orient='records')

        # WRITE DATA TO FILE
        utils.save_data_json(STOCKS)

        try:
            self.threadpool.waitForDone(1000)
            print("Finished")
        except Exception:
            pass

        event.accept()

    def ninja_mode(self):

        def create_image():
            self.image = QtWidgets.QLabel(self)
            self.pixmap = QtGui.QPixmap(
                utils.resource_path("images/ninja.png"))
            self.image.setPixmap(self.pixmap)
            self.resize(self.pixmap.width(), self.pixmap.height())
            self.image.setGeometry(QtCore.QRect(
                0, 0, self.pixmap.width(), self.pixmap.height()))
            self.image.mouseDoubleClickEvent = un_ninja_mode

        def un_ninja_mode(event):
            old_width, old_height = self.width(), self.height()
            self.resize(old_width, old_height)
            self.image.setHidden(True)

        if self.image is None:
            create_image()

        if self.image.isHidden():
            self.image.show()

    def add_wishlist_func(self):
        # get name of wishlist
        name = self.name_wishlist_input.text()

        # check if name is empty, set placeholder
        if name == "":
            self.name_wishlist_input.setPlaceholderText("Name is empty")
            return

        if name in STOCKS.keys():
            self.name_wishlist_input.setText("")
            self.name_wishlist_input.setPlaceholderText("Name already exists")
            return

        if name != "" and self.wishlist_combo.findText(name) == -1:
            # create new page
            self.page.append(QtWidgets.QWidget())
            self.page[-1].setObjectName("page")
            self.horizontal_layout_2 = QtWidgets.QHBoxLayout(self.page[-1])
            self.horizontal_layout_2.setObjectName("horizontal_layout_2")

            # add stock view table
            self.stock_view.append(TableWidget(
                df=pd.DataFrame(), parent=self.page[-1]))
            self.stock_view[-1].setObjectName("stock_view")
            self.horizontal_layout_2.addWidget(self.stock_view[-1])

            # add setting view table
            self.setting_view.append(QtWidgets.QTableWidget(
                100, 2, self.page[-1]))

            self.horizontal_layout_2.addWidget(self.setting_view[-1])
            self.horizontal_layout_2.setStretch(0, 7)
            self.horizontal_layout_2.setStretch(1, 3)
            self.stacked_widget.addWidget(self.page[-1])

            self.wishlist_combo.addItem(name)

            # move to new page
            self.wishlist_combo.setCurrentIndex(
                self.wishlist_combo.count() - 1)
            self.stacked_widget.setCurrentIndex(
                self.stacked_widget.count() - 1)

            # add new index to STOCKS
            STOCKS[name] = {}
            self.config_setting_view(index=len(STOCKS.keys()) - 1, name=name)

            # set empty string for input
            self.name_wishlist_input.setText("")

    def remove_wishlist_func(self):
        global STOCKS
        name_wishlist = self.name_wishlist_input.text()
        # remove wishlist base on name
        if name_wishlist != "":
            index = self.wishlist_combo.findText(name_wishlist)
            if index != -1:
                self.wishlist_combo.removeItem(index)
                self.stacked_widget.removeWidget(self.page[index])
                self.page.pop(index)
                self.stock_view.pop(index)
                self.setting_view.pop(index)
                del STOCKS[name_wishlist]
                self.name_wishlist_input.setText("")
        else:
            self.name_wishlist_input.setPlaceholderText("Name is empty")
            return

        self.wishlist_combo.setCurrentIndex(0)
        self.name_wishlist_input.setText("")
        self.name_wishlist_input.setPlaceholderText("")

    def switch_wishlist(self):
        # switch to selected wishlist
        self.stacked_widget.setCurrentIndex(
            self.wishlist_combo.currentIndex())

    # MAIN FUNCTION
    def create_threadpool(self, max_threads=20):
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(max_threads)
        self.scraper = Scraper()
        self.scraper.signals.data.connect(self.update_stock_value)
        self.threadpool.start(self.scraper)

        # setup thread for vnindex
        self.vnindex = IndexThread()
        self.vnindex.signals.vn_signal.connect(self.update_vnindex)
        self.threadpool.start(self.vnindex)

    def update_vnindex(self, data):

        def send_email_vnindex(index, change):
            # email when vnindex is out of range
            if not self.index_email_checkbox.isChecked():
                return
            try:
                vnindex_low = self.get_vnindex_low()
                vnindex_high = self.get_vnindex_high()
                vnindex = float(str(index).replace(",", ""))
                if vnindex < vnindex_low or vnindex > vnindex_high:
                    lo_hi = 0 if vnindex < vnindex_low else 1
                    self.emailer_vnindex = EmailMachine(
                        stock="VNINDEX", lo_hi=lo_hi, price=vnindex, change=change)
                    self.threadpool.start(self.emailer_vnindex)
                    self.index_email_checkbox.setChecked(False)
            except Exception as e:
                note = " in send_email_vnindex"
                utils.save_error_log(str(e) + note)

        try:
            percent_float = abs(float(data.get("percent")))
            if percent_float > 10:
                return
        except Exception as e:
            print(e)
        else:
            change = data.get("change")
            index = data.get("index")
            self.vnindex_price.setText('{} ({})'.format(index, change))
            send_email_vnindex(index, change)

    def coloring_table(self, index, ceiling_price_list, floor_price_list):

        def coloring_stock():
            if not self.color_checkbox.isChecked():
                return
            # color text as #FFBCBC if lastPrice below floorPrice
            for row in range(len(self.stock_view[index].df)):
                last_price = float(
                    self.stock_view[index].df.iloc[row]["lastPrice"])
                floor_price = float(floor_price_list[row])
                ceiling_price = float(ceiling_price_list[row])
                basic_price = float(
                    self.stock_view[index].df.iloc[row]["basicPrice"])
                if last_price == floor_price:
                    self.stock_view[index].item(row, 0).setBackground(
                        QColor("#B0EFEB"))  # cyan
                elif last_price == ceiling_price:
                    self.stock_view[index].item(row, 0).setBackground(
                        QColor("#BEAEE2"))  # purple
                elif basic_price > last_price > floor_price:
                    self.stock_view[index].item(row, 0).setBackground(
                        QColor("#FFBCBC"))  # red
                elif basic_price < last_price < ceiling_price:
                    self.stock_view[index].item(row, 0).setBackground(
                        QColor("#91C788"))  # green
                else:
                    self.stock_view[index].item(row, 0).setBackground(
                        QColor("#FFF9B6"))  # yellow

        def coloring_price_and_quantity():
            for row in range(len(self.stock_view[index].df)):
                # COLOR BASE ON CHANGE
                bid_vol_item = self.stock_view[index].item(row, 2)
                offer_vol_item = self.stock_view[index].item(row, 4)
                current_price_item = self.stock_view[index].item(row, 3)

                # SET COLOR FOR BID 1 VOL
                try:
                    bid_vol = float(
                        str(self.get_bid_vol(index, row)).replace(',', '.')) * 100
                    expected_bid_vol = float(
                        str(self.get_expected_bid_vol(index, row)).replace(',', '.')) * 100
                    if bid_vol < expected_bid_vol:
                        bid_vol_item.setBackground(QColor("#FFBCBC"))  # RED
                except ValueError as e:
                    print(e)
                except Exception as e:
                    print(e)

                # SET COLOR FOR OFFER 1 VOL
                try:
                    offer_vol = float(
                        str(self.get_offer_vol(index, row)).replace(',', '.')) * 100
                    expected_offer_vol = float(
                        str(self.get_expected_offer_vol(index, row)).replace(',', '.')) * 100
                    if offer_vol < expected_offer_vol:
                        offer_vol_item.setBackground(
                            QColor("#FFBCBC"))  # RED
                except ValueError as e:
                    print(e)
                except Exception as e:
                    print(e)

                try:
                    # get current price
                    current_price = float(self.get_current_price(index, row))
                    expected_current_price_low = float(
                        str(self.get_expected_price_low(index, row)).replace(',', '.'))
                    # set color for current price
                    if current_price < expected_current_price_low:
                        current_price_item.setBackground(
                            QColor("#FFBCBC"))  # RED
                except Exception:
                    pass

                try:
                    # get current price
                    current_price = float(self.get_current_price(index, row))
                    expected_current_price_high = float(
                        str(self.get_expected_price_high(index, row)).replace(',', '.'))
                    if current_price > expected_current_price_high:
                        current_price_item.setBackground(
                            QColor("#91C788"))  # GREEN
                except Exception:
                    pass

        # MAIN
        coloring_stock()
        coloring_price_and_quantity()

    def update_stock_value(self, df):
        def email_stock(index):
            def process_after_sent_email(signal):
                row_stock = self.stock_view[index].df[self.stock_view[index].df['secCd']
                                                      == signal[0]].index[0]
                self.setting_view[index].item(row_stock, 1).setText("")
                if signal[1] == 1:
                    # change status to Done and color to green
                    self.setting_view[index].item(row_stock, 1).setText("Done")
                    EMAIL_CHECKED[row_stock] = 0
                elif signal[1] == 0:
                    # change status to Failed and color to red
                    self.setting_view[index].item(
                        row_stock, 1).setText("Failed")
                    EMAIL_CHECKED[row_stock] = 0
                    # uncheck checkbox
                self.setting_view[index].cellWidget(
                    row_stock, 0).setCheckState(0)

            # EMAIL WHEN PRICE IS OUT OF RANGE
            for row in range(len(self.stock_view[index].df)):
                # get current price
                try:
                    current_price = self.get_current_price(index, row)
                    expected_current_price_low = self.get_expected_price_low(
                        index, row)
                    expected_current_price_high = self.get_expected_price_high(
                        index, row)

                    if EMAIL_CHECKED[row] != 2:  # not checked
                        continue

                    if float(current_price) < float(expected_current_price_low):
                        self.emailer = EmailMachine(
                            price=current_price, lo_hi=0, stock=self.get_stock(index, row),
                            change_percent=self.get_changed_percent(index, row))
                        self.emailer.signal.email_signal.connect(
                            process_after_sent_email)
                        self.threadpool.start(self.emailer)
                        EMAIL_CHECKED[row] = 0

                    elif float(current_price) > float(expected_current_price_high):
                        self.emailer = EmailMachine(
                            price=current_price, lo_hi=1, stock=self.get_stock(index, row),
                            change_percent=self.get_changed_percent(index, row))
                        self.emailer.signal.email_signal.connect(
                            process_after_sent_email)
                        self.threadpool.start(self.emailer)
                        EMAIL_CHECKED[row] = 0
                except Exception as e:
                    note = " in email_stock"
                    print(note)
                    utils.save_error_log(str(e) + note)

        index = self.stacked_widget.currentIndex()
        # if empty dataframe, do nothing
        if df.empty:
            return

        # insert data to self.stock_view[index].df
        headers = ['secCd', 'basicPrice', 'best1BidQty',
                   'lastPrice', 'best1OfferQty', 'changePercent']

        self.filter_best_stock(df, headers)

        df = df[df['secCd'].isin(self.stock_view[index].df['secCd'])]

        #         sort
        df = df.set_index('secCd')
        df = df.reindex(index=self.stock_view[index].df['secCd'])
        df = df.reset_index()

        for header in headers:
            self.stock_view[index].df[header] = df[header]

        self.stock_view[index].display_data(0, 5)

        ceiling_price_list = df['ceilingPrice']
        floor_price_list = df['floorPrice']
        self.coloring_table(index, ceiling_price_list, floor_price_list)

        email_stock(index)

        self.stock_view[index].align_data()

    def filter_best_stock(self, df_all_stock, headers):
        """
        find best stock in each portfolios and make them to new page

        args:
            df_all_stock (pd.DataFrame): dataframe from request.json()
            headers (list): header name list of self.df

        returns
            None
        """
        global STOCKS

        # get all stock from porfolio
        stock_list_all_porfolios = np.array([])
        for index, portfolio in STOCKS.items():
            stock_list_in_portfolio = [stock['secCd'] for stock in portfolio]
            stock_list_all_porfolios = np.concatenate(
                (stock_list_all_porfolios, stock_list_in_portfolio))

        # just keep stock in portfolios
        df_all_stock = df_all_stock[df_all_stock['secCd'].isin(
            stock_list_all_porfolios)]

        # sort
        df_all_stock.sort_values('changePercent')
        df_all_stock.reset_index()

        # find TOP 1 Page index
        top_1_index = np.where(np.array(list(STOCKS.keys())) == 'TOP 1')[0][0]

        for header in headers:
            self.stock_view[top_1_index].df[header] = df_all_stock[header]

        self.stock_view[top_1_index].display_data(0, 5)

    def email_checked_event(self, checked, row, col) -> None:
        index = self.stacked_widget.currentIndex()
        current_row = self.setting_view[index].currentRow()
        if current_row == -1:
            return
        EMAIL_CHECKED[current_row] = checked
        if checked == 2:
            self.setting_view[index].item(row, 1).setText("Pending")
        else:
            self.setting_view[index].item(row, 1).setText("Not send")

    # OTHER FUNCTION
    def get_current_price(self, index, row):
        return self.stock_view[index].df.iloc[row, 3]

    def get_expected_price_low(self, index, row):
        price_low = self.stock_view[index].df.iloc[row, 7]
        if price_low == "" or pd.isna(price_low):
            return 0
        return price_low

    def get_expected_price_high(self, index, row):
        price_high = self.stock_view[index].df.iloc[row, 8]
        if price_high == "" or pd.isna(price_high):
            return 9999
        return price_high

    def get_offer_vol(self, index, row) -> str:
        return self.stock_view[index].df.iloc[row, 4]

    def get_bid_vol(self, index, row) -> str:
        return self.stock_view[index].df.iloc[row, 2]

    def get_expected_bid_vol(self, index, row) -> str:
        return self.stock_view[index].df.iloc[row, 6]

    def get_expected_offer_vol(self, index, row) -> str:
        return self.stock_view[index].df.iloc[row, 9]

    def get_stock(self, index, row) -> str:
        return self.stock_view[index].df.iloc[row, 0]

    def get_changed_percent(self, index, row) -> str:
        return self.stock_view[index].df.iloc[row, 5]

    def get_vnindex_low(self):
        vnindex_low = self.index_low_input.text()
        if vnindex_low == "":
            return 0
        return float(str(vnindex_low).replace(",", ""))

    def get_vnindex_high(self):
        vnindex_high = self.index_high_input.text()
        if vnindex_high == "":
            return 9999
        return float(str(vnindex_high).replace(",", ""))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = MyWindow()
    ui.show()
    sys.exit(app.exec_())
