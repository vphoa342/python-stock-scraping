import pandas as pd
import requests
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot

import utils


class IndexSignals(QObject):
    vn_signal = pyqtSignal(dict)


class IndexThread(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = IndexSignals()

    @pyqtSlot()
    def run(self):
        link = 'https://banggia.cafef.vn/stockhandler.ashx?index=true'
        while not utils.STOP_SIGNAL:
            try:
                response = requests.get(link).json()
                # response[1] is vnindex
                self.signals.vn_signal.emit(response[1])
            except Exception:
                print('error in vnindex')


class StockSignals(QObject):
    data = pyqtSignal(pd.DataFrame)


class Scraper(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = StockSignals()

    @pyqtSlot()
    def run(self):
        market = [100, 200, 300]
        headers = ['secCd', 'basicPrice', 'ceilingPrice', 'floorPrice', 'best1BidQty',
                   'lastPrice', 'best1OfferQty', 'changePercent']

        # make dynamic comma for volume
        def change_volume(volume):
            volume = str(volume)
            if len(volume) <= 2:
                return volume
            else:
                return volume[:-2] + ',' + volume[-2:]

        while not utils.STOP_SIGNAL:
            df = pd.DataFrame()
            for i in market:
                # link of the website api
                link = f'https://banggia.dag.vn/rest/market/api/initSession?marketIndexCd={i}&secType=0'

                # get response from graphql
                try:
                    response = requests.get(link).json()
                    df = pd.concat([df, pd.DataFrame(response['data'])])
                except Exception as e:
                    print(e)

            # modify df
            try:
                df = df[headers]
                df['best1BidQty'] = df['best1BidQty'].apply(
                    lambda x: change_volume(x))
                df['best1OfferQty'] = df['best1OfferQty'].apply(
                    lambda x: change_volume(x))

                # sort by secCd
                df = df.sort_values(by='secCd')

                df['lastPrice'] = df['lastPrice'].map('{:.2f}'.format)
                df['basicPrice'] = df['basicPrice'].map('{:.2f}'.format)
                df['changePercent'] = df['changePercent'].map('{:.2f}'.format)
            except Exception as e:
                print(e)

            # update dataframe
            self.signals.data.emit(df)

        if utils.STOP_SIGNAL:
            print("Stopped")
