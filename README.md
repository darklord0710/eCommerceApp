# eCommerceApp
Create virtual environment

	python -m venv venv
Active virtual environment

	venv\Scripts\activate
Install necessary package (setuptools: for No module named pkg_resources Error)

	pip install django, pymysql, cloudinary, pillow, django-ckeditor, djangorestframework, drf-yasg, django-oauth-toolkit, django-cors-headers
Config and Login with Social Accounts

	pip install django-allauth, django_extensions
Create cert and key

	pip install Werkzeug, pyOpenSSL
Config send SMS

	pip install twilio
<p>Create database in mySQL<br/>
Run migrate

	python manage.py migrate
Create superuser
	
	python manage.py createsuperuser
Run server

 	python manage.py runserver
Show all URLs (Optional)

	python manage.py show_urls
Run localhost with HTTPS (Optional)
	
	python manage.py runserver_plus --cert-file cert.pem --key-file key.pem
$${\color{red}FB \space requires \space login \space with \space HTTPS}$$ <br/>
Insecure Login Block Solution:
* Using NgroK
* Using Passport strategy
* Using cert.pem & key.perm

<h1>Documentation</h1>
<h2>Integrate Social Accounts</h2>
<p>https://docs.allauth.org/en/latest/installation/quickstart.html</p>
<p>https://django-extensions.readthedocs.io/en/latest/runserver_plus.html</p>
<h1>Integrate Twilio</h1>
<p>https://www.twilio.com/docs/messaging/quickstart</p>
