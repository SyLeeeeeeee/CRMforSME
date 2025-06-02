import imaplib
import email
from email.header import decode_header
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from accounts.models import Ticket, ExternalEmailLog

User = get_user_model()

class Command(BaseCommand):
    help = "Fetch new email replies and log them to ExternalEmailLog"

    def handle(self, *args, **opts):
        cfg = settings.INBOUND_EMAIL
        m = imaplib.IMAP4_SSL(cfg['HOST'], cfg['PORT']) if cfg['USE_SSL'] \
            else imaplib.IMAP4(cfg['HOST'], cfg['PORT'])
        m.login(cfg['USER'], cfg['PASS'])
        m.select('INBOX')

        # search unseen
        typ, data = m.search(None, '(UNSEEN)')
        for num in data[0].split():
            typ, msg_data = m.fetch(num, '(RFC822)')
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            # decode subject
            subj, enc = decode_header(msg['Subject'])[0]
            if isinstance(subj, bytes):
                subj = subj.decode(enc or 'utf-8', errors='ignore')

            # look for “Ticket #123” in subject
            import re
            mobj = re.search(r'Ticket\s*#(\d+)', subj)
            if not mobj:
                m.store(num, '+FLAGS', '\\Seen')
                continue

            ticket_id = int(mobj.group(1))
            try:
                ticket = Ticket.objects.get(id=ticket_id)
            except Ticket.DoesNotExist:
                m.store(num, '+FLAGS', '\\Seen')
                continue

            # extract plain text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')

            # who sent it?
            sender = email.utils.parseaddr(msg.get('From'))[1]

            # log it
            ExternalEmailLog.objects.create(
                ticket=ticket,
                to=sender,           # original recipient in our mailbox
                cc=None,
                subject=subj,
                message=body,
                sender=None,         # no Django user
                sent_at=timezone.now()
            )

            # mark read
            m.store(num, '+FLAGS', '\\Seen')

        m.close()
        m.logout()
