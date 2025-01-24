#!/bin/bash

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start supervisor (which will start both Django and the email daemon)
echo "Starting services..."
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
