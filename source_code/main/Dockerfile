FROM python:3.9
EXPOSE 8000
WORKDIR /app 
COPY requirements.txt /app
RUN pip3 install -r requirements.txt --no-cache-dir
COPY . /app 
COPY ./todoapp /app 
COPY ./todos /app 
COPY ./entrypoint.sh /app 
COPY ./manage.py /app
RUN chmod +x *.sh
CMD ["/app/entrypoint.sh"] 
#CMD ["manage.py", "runserver", "0.0.0.0:8000"]
