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

# Lib imports
from env_utils import get_env

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.mail')


def send_email(recipients, subject, text, attachments=None, message_callback=None, **kwargs):
    """
    Sends an email from the recipients email account to a list of recipients with given subject and text.
    :param recipients: A list of emails
    :param subject: A subject string
    :param text: A formatting text of content
    :param attachments: any attachments to add
    :param message_callback: function to pass the message to once complete
    :return: True if message sent, otherwise False
    """
    if not any(recipients):
        log.trace('send_email got no recipients. Skipping.')
        return False

    # extract kwarg options
    retries = kwargs.get('retries', 3)
    server_timeout = kwargs.get('server_timeout', 600)
    use_smtp_ssl = kwargs.pop('use_smtp_ssl', False)

    # credentials and server options
    send_user = kwargs.pop('send_user', None) or get_env('SMTP_USER')
    send_mail = kwargs.pop('send_mail', None) or get_env('SMTP_USER')
    send_pswd = kwargs.pop('send_pswd', None) or get_env('SMTP_PSWD')
    smtp_host = kwargs.pop('smtp_host', None) or get_env('SMTP_HOST')
    smtp_port = kwargs.pop('smtp_port', None) or get_env('SMTP_PORT')
    if not all([send_user, send_mail, send_pswd, smtp_host, smtp_port]):
        raise RuntimeError(
            'Can not send mail without SMTP details (send_user, send_mail, send_pswd, smtp_host, smtp_port)')

    # construct message
    outer = MIMEMultipart()
    outer['Subject'] = subject
    outer['To'] = ', '.join(recipients)
    outer['From'] = send_mail
    outer.attach(MIMEText(text))
    outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'
    outer_no_attachments = outer
    message = outer_no_attachments.as_string()

    # attach files
    if attachments:
        attachments = [attachments] if not isinstance(attachments, list) else attachments
        for fname in attachments:
            if isinstance(fname, tuple):
                fname, aname = fname
            else:
                aname = os.path.split(fname)[1]
            ctype, encoding = mimetypes.guess_type(fname)

            try:
                if ctype is None or encoding is not None:
                    # No guess could be made, or the file is encoded (compressed), so
                    # use a generic bag-of-bits type.
                    ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)
                if maintype == 'text':
                    fp = open(fname)
                    # Note: we should handle calculating the charset
                    msg = MIMEText(fp.read(), _subtype=subtype)
                    fp.close()
                elif maintype == 'image':
                    fp = open(fname, 'rb')
                    msg = MIMEImage(fp.read(), _subtype=subtype)
                    fp.close()
                elif maintype == 'audio':
                    fp = open(fname, 'rb')
                    msg = MIMEAudio(fp.read(), _subtype=subtype)
                    fp.close()
                else:
                    fp = open(fname, 'rb')
                    msg = MIMEBase(maintype, subtype)
                    msg.set_payload(fp.read())
                    fp.close()
                    # Encode the payload using Base64
                    encoders.encode_base64(msg)
                # Set the filename parameter
                msg.add_header('Content-Disposition', 'attachment', filename=aname)
                outer.attach(msg)
            except Exception as exc:
                log.warn('Exception preparing attachment: file={} exc={}'.format(fname, exc.message), exc_info=True)
            else:
                message = outer.as_string()

    # Prepare actual message
    if message_callback and callable(message_callback):
        message_callback(message)
    log.info('Sending email: recipients={} subject={}'.format(recipients, subject))

    while retries > 0:
        retries -= 1
        try:
            if use_smtp_ssl:
                log.trace('send_email: connecting to SMTP_SSL server: timeout={}'.format(server_timeout))
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=server_timeout)
            else:
                log.trace('send_email: connecting to SMTP server: timeout={}'.format(server_timeout))
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=server_timeout)
            log.trace('send_email: sending ehlo')
            server.ehlo()  # may not be needed or supported
            log.trace('send_email: starting TLS')
            server.starttls()  # may not be needed or supported
            log.trace('send_email: logging in')
            server.login(send_user, send_pswd)
        except Exception as exc:
            log.error('Exception connecting to SMTP server: exc={} trace...'.format(exc), exc_info=True)
            continue
        else:
            log.trace('connection to SMTP server succeeded. Sending mail')
            try:
                try:
                    server.sendmail(send_mail, recipients, message)
                except smtplib.SMTPSenderRefused as exc:
                    if 'size limits' in exc.smtp_error:
                        log.warn('Exception sending mail due to size limits - sending without attachments: {}'.format(
                            exc.message), exc_info=True)
                        message = outer_no_attachments.as_string()
                        server.sendmail(send_mail, recipients, message)
                    else:
                        raise
            except Exception as exc:
                log.error('Exception sending email: {}'.format(exc.message), exc_info=True)
                if retries > 0:
                    log.debug('retrying to send mail again: retries_remaining={}'.format(retries))
            else:
                log.trace('mail sent successfully')
                return True
        finally:
            # server.quit()
            server.close()
    else:
        log.error('Failed to send mail after retries')
        return False


__all__ = ['send_email']
