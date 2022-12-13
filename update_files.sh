cd /var/www/PJS/
sudo git pull
sudo sass static/scss/base.scss static/css/base.css
sudo sass static/scss/optimization.scss static/css/optimization.css
sudo sass static/scss/sidebar.scss static/css/sidebar.css
sudo systemctl reload apache2