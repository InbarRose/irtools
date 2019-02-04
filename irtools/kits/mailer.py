#! /usr/bin/env python

# Standard Imports
import smtplib
import mimetypes
from email import encoders
# from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.kits.mailer')

# TODO: Test this KIT
# === WARNING: THIS KIT IS UNTESTED ===


class MailMessage(object):
    # todo: allow message re-use with just recipients changing. or parts changing and re-create message

    def __init__(self, subject, from_field, to_field, text, **kwargs):
        self.subject = subject
        self.from_field = from_field
        self.to_field = to_field
        self.text = text

        self.attachments = kwargs.pop('attachments', None)
        self.is_html = kwargs.pop('html', False)  # plain or html message

        self._message = self.make_message(self.subject, self.to_field, self.from_field, text,
                                          subtype='html' if self.is_html else 'plain',
                                          attachments=self.attachments)

        super(MailMessage, self).__init__()

    @property
    def message(self):
        return self._message.as_string()

    @staticmethod
    def make_message(subject, recipients, send_mail, text, subtype='plain', attachments=None):
        # construct message
        multipart_msg = MIMEMultipart()
        multipart_msg['Subject'] = subject
        multipart_msg['To'] = ', '.join(recipients)
        multipart_msg['From'] = send_mail
        multipart_msg.attach(MIMEText(text, _subtype=subtype))
        multipart_msg.preamble = 'You will not see this in a MIME-aware mail reader.\n'

        if attachments:
            attachments = [attachments] if not isinstance(attachments, list) else attachments
            for attachment in attachments:
                MailMessage.add_attachment(multipart_msg, attachment)

        return multipart_msg

    @staticmethod
    def add_attachment(multipart_msg, attachment):
        if isinstance(attachment, tuple):
            fname, aname = attachment
        else:
            aname = os.path.split(attachment)[1]
        ctype, encoding = mimetypes.guess_type(attachment)

        try:
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded (compressed), so
                # use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            # todo: optimize below switch cases
            if maintype == 'text':
                fp = open(attachment)
                # Note: we should handle calculating the charset
                msg_atc = MIMEText(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'image':
                fp = open(attachment, 'rb')
                msg_atc = MIMEImage(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'audio':
                fp = open(attachment, 'rb')
                msg_atc = MIMEAudio(fp.read(), _subtype=subtype)
                fp.close()
            else:
                fp = open(attachment, 'rb')
                msg_atc = MIMEBase(maintype, subtype)
                msg_atc.set_payload(fp.read())
                fp.close()
                # Encode the payload using Base64
                encoders.encode_base64(msg_atc)
            # Set the filename parameter
            msg_atc.add_header('Content-Disposition', 'attachment', filename=aname)
            multipart_msg.attach(msg_atc)
        except Exception as exc:
            log.warn('Exception preparing attachment: file={} exc={}'.format(attachment, exc.message), exc_info=True)


class Mailer(object):

    def __init__(self, host, port, username, password, **kwargs):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        self.kwargs = kwargs

        self.server = None

    def send_new_simple_email(self, recipients, subject, text, attachments=None, **kwargs):
        mail_message = MailMessage(subject, self.username, recipients, text, attachments=attachments, **kwargs)
        return self.send_message(recipients, mail_message, **kwargs)

    def send_message(self, recipients, mail_message, **kwargs):
        assert isinstance(mail_message, MailMessage)
        try:
            self.server.sendmail(self.username, recipients, mail_message.message)
        except smtplib.SMTPSenderRefused as exc:
            if 'size limits' in exc.smtp_error:
                log.error('Exception sending mail due to size limits: {}'.format(exc), exc_info=True)
                # todo: in future we could fallback to removing attachments
            raise
        return True  # successfully sent email, return True.

    def connect_to_server(self, **kwargs):
        raise NotImplementedError()

    def disconnect_from_server(self, **kwargs):
        raise NotImplementedError()


class SMTPMailer(Mailer):

    _default_server_timeout = 600

    def __init__(self, host, port, username, password, **kwargs):
        self.smtp_use_ssl = kwargs.pop('smtp_use_ssl', False)
        super(SMTPMailer, self).__init__(host, port, username, password, **kwargs)

    def connect_to_server(self, **kwargs):
        log.debug('connecting to server: server={} port={}'.format(self.server, self.port))
        # get kwargs
        server_timeout = kwargs.pop('server_timeout', self._default_server_timeout)
        # get server class
        _server_cls = smtplib.SMTP_SSL if self.smtp_use_ssl else smtplib.SMTP
        # connect to server
        log.trace('contacting SMTP Server: server={} port={} use_ssl={}'.format(
            self.host, self.port, self.smtp_use_ssl))
        _server_con = _server_cls(self.host, self.port, timeout=server_timeout)
        # send ehlo
        log.trace('sending ehlo: server={} port={}'.format(self.server, self.port))
        _server_con.ehlo()  # may not be needed or supported
        # send start tls
        log.trace('sending start TLS: server={} port={}'.format(self.server, self.port))
        _server_con.starttls()  # may not be needed or supported
        # log in to server
        log.trace(
            'logging in to SMTP Server: server={} port={} username={}'.format(self.server, self.port, self.username))
        _server_con.login(self.username, self.password)
        # success
        self.server = _server_con
        return self.server


class GoogleSMTPMailer(SMTPMailer):

    # default params for google smtp (with ssl)
    _default_port = 465
    _default_hostname = 'smtp.gmail.com'
    _default_use_ssl = True

    def __init__(self, user_email, app_password, **kwargs):
        kwargs.setdefault('host', self._default_hostname)
        kwargs.setdefault('port', self._default_port)
        kwargs.setdefault('username', user_email)
        kwargs.setdefault('password', app_password)
        # extra kwargs
        kwargs.setdefault('smtp_use_ssl', self._default_use_ssl)
        super(GoogleSMTPMailer, self).__init__(**kwargs)

    def connect_to_server(self, **kwargs):
        # like normal SMTP connect but no ehlo or starttls  TODO: optimize this and re-use code
        log.debug('connecting to server: server={} port={}'.format(self.server, self.port))
        # get kwargs
        server_timeout = kwargs.pop('server_timeout', self._default_server_timeout)
        # get server class
        _server_cls = smtplib.SMTP_SSL if self.smtp_use_ssl else smtplib.SMTP
        # connect to server
        log.trace('contacting SMTP Server: server={} port={} use_ssl={}'.format(
            self.host, self.port, self.smtp_use_ssl))
        _server_con = _server_cls(self.host, self.port, timeout=server_timeout)
        # log in to server
        log.trace(
            'logging in to SMTP Server: server={} port={} username={}'.format(self.server, self.port, self.username))
        _server_con.login(self.username, self.password)
        # success
        self.server = _server_con
        return self.server

    def disconnect_from_server(self, **kwargs):
        log.debug('disconnecting from server: server={} port={}'.format(self.server, self.port))
        # server.quit() // old way
        self.server.close()


def send_email(recipients, subject, text, attachments=None, **kwargs):
    """
    Sends an one-off email to recipients with given subject and text uses GoogleSMTPMailer
    For sending bulk emails you should create a Mailer object - connect once, send your emails, then disconnect
    :param recipients: A list of emails
    :param subject: A subject string
    :param text: A formatting text of content
    :param attachments: any attachments to add
    :return: True if message sent, otherwise False
    """
    if not any(recipients):
        log.trace('send_email got no recipients. Skipping.')
        return False

    # extract kwarg options
    retries = kwargs.get('retries', 3)

    # credentials and server options
    send_user = kwargs.pop('send_user', None) or utils.get_env('SMTP_USER')
    send_mail = kwargs.pop('send_mail', None) or utils.get_env('SMTP_USER')
    send_pswd = kwargs.pop('send_pswd', None) or utils.get_env('SMTP_PSWD')
    smtp_host = kwargs.pop('smtp_host', None) or utils.get_env('SMTP_HOST')
    smtp_port = kwargs.pop('smtp_port', None) or utils.get_env('SMTP_PORT')
    if not all([send_user, send_mail, send_pswd, smtp_host, smtp_port]):
        raise RuntimeError(
            'Can not send mail without SMTP details (send_user, send_mail, send_pswd, smtp_host, smtp_port)')

    mail_message = MailMessage(subject, send_mail, recipients, text, attachments=attachments, **kwargs)
    log.info('Sending email: recipients={} subject={}'.format(recipients, subject))

    mailer = GoogleSMTPMailer(send_user, send_pswd, **kwargs)

    while retries > 0:
        retries -= 1
        try:
            mailer.connect_to_server(**kwargs)
        except Exception as exc:
            log.error('Exception connecting to SMTP server: exc={} trace...'.format(exc), exc_info=True)
            continue
        else:
            log.trace('connection to SMTP server succeeded. Sending mail')
            try:
                mailer.send_message(recipients, mail_message, **kwargs)
            except Exception as exc:
                log.error('Exception sending email: {}'.format(exc.message), exc_info=True)
                if retries > 0:
                    log.debug('retrying to send mail again: retries_remaining={}'.format(retries))
            else:
                log.trace('mail sent successfully')
                return True
        finally:
            mailer.disconnect_from_server()
    else:
        log.error('Failed to send mail after retries')
        return False
