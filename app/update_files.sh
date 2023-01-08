cd /var/www/PJS/
sudo git pull
sudo sass app/static/scss/main.scss app/static/css/main.css
sudo systemctl reload apache2