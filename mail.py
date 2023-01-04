import smtplib
from email.mime.text import MIMEText

sender = 'termine@pjs-mail.de'
receiver = 'nils.heilemann@gmail.com'

msg = MIMEText('This is a test mail')

msg['Subject'] = 'Test mail'
msg['From'] = 'termine@pjs-mail.de'
msg['To'] = receiver

user = 'termine@pjs-mail.de'
password = 'jb79G7JLep'

# Set up connection to the SMTP server
with smtplib.SMTP("smtp.ionos.de", 587) as server:

    # Log in to the server
    server.login(user, password)

    # Send the email
    server.sendmail(sender, receiver, msg.as_string())
    print("mail successfully sent")