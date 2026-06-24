FROM python:3.11

# User setup for Hugging Face Spaces
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy requirements and install
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the app
COPY --chown=user . /app

# Collect static files
RUN python manage.py collectstatic --noinput

# Hugging Face Spaces requires the app to run on port 7860
CMD ["gunicorn", "digital_twin_pro.wsgi:application", "--bind", "0.0.0.0:7860"]
