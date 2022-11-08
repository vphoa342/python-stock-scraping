"""
Adapted from:
https://github.com/google/gmail-oauth2-tools/blob/master/python/oauth2.py
https://developers.google.com/identity/protocols/OAuth2

1. Generate and authorize an OAuth2 (generate_oauth2_token)
2. Generate a new access tokens using a refresh token(refresh_token)
3. Generate an OAuth2 string to use for login (access_token)
"""

import base64
import imaplib
import json
import smtplib
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart

from PyQt5.QtCore import QRunnable, QObject, pyqtSignal, pyqtSlot

import utils

EMAIL_CONFIG = utils.get_email_config()


def generate_oauth2_string(username, access_token, as_base64=False) -> str:
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (username, access_token)
    if as_base64:
        auth_string = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
    return auth_string


def test_imap(user, auth_string) -> None:
    imap_conn = imaplib.IMAP4_SSL('imap.gmail.com')
    imap_conn.debug = 4
    imap_conn.authenticate('XOAUTH2', lambda x: auth_string)
    imap_conn.select('INBOX')


def test_smpt(user, base64_auth_string) -> None:
    smtp_conn = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_conn.set_debuglevel(True)
    smtp_conn.ehlo('test')
    smtp_conn.starttls()
    smtp_conn.docmd('AUTH', 'XOAUTH2 ' + base64_auth_string)


def url_unescape(text) -> str:
    return urllib.parse.unquote(text)


def url_escape(text) -> str:
    return urllib.parse.quote(text, safe='~-._')


def url_format_params(params) -> str:
    param_fragments = []
    for param in sorted(params.items(), key=lambda x: x[0]):
        param_fragments.append('%s=%s' % (param[0], url_escape(param[1])))
    return '&'.join(param_fragments)


oauth2_json = utils.get_oauth2_json()



# SINGLETONS
class EmailMeta(type):
    """
    The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class EmailSignal(QObject):
    email_signal = pyqtSignal(list)


class EmailMachine(QRunnable):
    GOOGLE_CLIENT_ID = oauth2_json["installed"]['client_id']
    GOOGLE_CLIENT_SECRET = oauth2_json["installed"]['client_secret']
    GOOGLE_REFRESH_TOKEN = oauth2_json["installed"]['refresh_token']
    GOOGLE_ACCOUNTS_BASE_URL = 'https://accounts.google.com'
    REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
    mail = EMAIL_CONFIG['FROM_MAIL']
    to_mail = EMAIL_CONFIG['TO_MAIL']
    password = EMAIL_CONFIG['PWD']
    __metaclass__ = EmailMeta

    def __init__(self, stock=None, lo_hi=0, price=0, change_percent=0, change=0):

        super().__init__()
        self.stock = stock
        self.lo_hi = lo_hi
        self.price = price
        self.signal = EmailSignal()
        self.change_percent = change_percent
        self.change = change

    def command_to_url(self, command) -> str:
        return '%s/%s' % (self.GOOGLE_ACCOUNTS_BASE_URL, command)

    def generate_permission_url(self, client_id, scope='https://mail.google.com/') -> str:
        params = {'client_id': client_id, 'redirect_uri': self.REDIRECT_URI, 'scope': scope, 'response_type': 'code'}
        return '%s?%s' % (self.command_to_url('o/oauth2/auth'), url_format_params(params))

    def call_authorize_tokens(self, client_id, client_secret, authorization_code) -> dict:
        params = {'client_id': client_id, 'client_secret': client_secret, 'code': authorization_code,
                  'redirect_uri': self.REDIRECT_URI, 'grant_type': 'authorization_code'}
        request_url = self.command_to_url('o/oauth2/token')
        response = urllib.request.urlopen(request_url, urllib.parse.urlencode(params).encode('UTF-8')).read().decode(
            'UTF-8')
        return json.loads(response)

    def call_refresh_token(self, client_id, client_secret, refresh_token) -> dict:
        params = {'client_id': client_id, 'client_secret': client_secret, 'refresh_token': refresh_token,
                  'grant_type': 'refresh_token'}
        request_url = self.command_to_url('o/oauth2/token')
        response = urllib.request.urlopen(request_url, urllib.parse.urlencode(params).encode('UTF-8')).read().decode(
            'UTF-8')
        return json.loads(response)

    def get_authorization(self, google_client_id, google_client_secret):
        scope = "https://mail.google.com/"
        print('Navigate to the following URL to auth:', self.generate_permission_url(google_client_id, scope))
        authorization_code = input('Enter verification code: ')
        response = self.call_authorize_tokens(google_client_id, google_client_secret, authorization_code)
        return response['refresh_token'], response['access_token'], response['expires_in']

    def refresh_authorization(self, google_client_id, google_client_secret, refresh_token):
        response = self.call_refresh_token(google_client_id, google_client_secret, refresh_token)
        return response['access_token'], response['expires_in']

    def send_mail(self, from_address, to_address, subject, message) -> None:
        access_token, expires_in = self.refresh_authorization(self.GOOGLE_CLIENT_ID, self.GOOGLE_CLIENT_SECRET,
                                                              self.GOOGLE_REFRESH_TOKEN)
        auth_string = generate_oauth2_string(from_address, access_token, as_base64=True)

        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = from_address
        msg['To'] = to_address
        msg.preamble = 'This is a multi-part message in MIME format.'
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo(self.GOOGLE_CLIENT_ID)
        server.starttls()
        server.docmd('AUTH', 'XOAUTH2 ' + auth_string)
        server.sendmail(from_address, to_address, msg.as_string())
        server.quit()

    @pyqtSlot()
    def run(self):
        from_mail = EMAIL_CONFIG['FROM_MAIL']
        to_mail = EMAIL_CONFIG['TO_MAIL']
        lo_hi = "H" if self.lo_hi == 1 else "L"
        if self.stock == "VNINDEX":
            subject = f'{self.stock}: {self.price}, {self.change} ({lo_hi})\n\n...'
        else:
            subject = f'{self.stock}: {self.price}, {self.change_percent}% ({lo_hi})\n\n...'
        try:
            self.send_mail(from_mail, to_mail, subject, "")
            self.signal.email_signal.emit(list([self.stock, 1]))
            print("Email sent")
        except Exception as e:
            print(e)
            self.signal.email_signal.emit(list([self.stock, 0]))
