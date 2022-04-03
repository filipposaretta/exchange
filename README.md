This is a simple bitcoin exchange platform (not real bitcoin). You can look at the presentation to discover more...

The presentation is here: https://www.canva.com/design/DAE27oGjaKs/DtJXiDasUgf_YerFm4Q1Ew/view?utm_content=DAE27oGjaKs&utm_campaign=designshare&utm_medium=link&utm_source=shareyourdesignpanel

How to Install:

Download the Directory

Download all the requirements with: pip install -r requirements.txt

I have used Python 3.7.9

Create a directory and go inside: mkdir progetto cd progetto

Create a virtual enveinroment: python -m venv name_dir cd name_dir

Activate it: Mac: . bin/activate Windows: . Scripts/activate Opz: if it doesn't work Create a Django project: django-admin.py startproject exchange

Migrate: python manage.py makemigrations app python manage.py migrate

How to use:

Create a superuser (admin): python manage.py createsuperuser
Run the program: python manage.py runserver
Have a nice day,

Filippo
