import os
import smtplib
import imghdr #for attaching images
from email.message import EmailMessage

EMAIL_ADDRESS = os.environ.get('EMAIL_USER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASS')

msg = EmailMessage()
msg['Subject'] = 'Test EMAIL- images dont work yet Ill figure it out'
msg['From'] = f"Union Poll <poll@unionpoll.com>"
msg['To'] = ['poll@unionpoll.com']

msg.set_content('Testing')

msg.add_alternative("""\
<!DOCTYPE html>
<html>
    <body>
        <h1 style="color:blue;">This is a test html email!</h1>
        <p>Paragraphs go here</p>
    </body>
</html>
""", subtype='html')


with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    smtp.send_message(msg)
