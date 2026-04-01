import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seo_project.settings')
django.setup()

from django.core.management import call_command
from django.db import connections

def fix_shard():
    print("Fixing shard_1 migrations...")
    try:
        with connections['shard_1'].cursor() as c:
            c.execute("DELETE FROM django_migrations WHERE app='analyzer';")
        print("Cleared faked migrations for analyzer.")
    except Exception as e:
        print(f"Error clearing: {e}")
        
    print("Running actual migrations for shard_1...")
    call_command('migrate', 'analyzer', database='shard_1')
    print("Done!")

if __name__ == '__main__':
    fix_shard()
