cd /var/www/PJS/
sudo git add *
sudo git stash
sudo git pull
sudo sass app/static/scss/main.scss app/static/css/main.css
cd /var/www/
sudo chmod -R 777 PJS
sudo systemctl reload apache2