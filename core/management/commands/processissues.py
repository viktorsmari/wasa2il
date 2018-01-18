# -*- coding: utf-8 -*-
from sys import stdout, stderr
from datetime import datetime

from django.core.management.base import BaseCommand

from core.models import *

class Command(BaseCommand):

    def handle(self, *args, **options):

        now = datetime.now()

        unprocessed_issues = Issue.objects.filter(is_processed=False).order_by('deadline_votes', 'id')

        for issue in unprocessed_issues:
            issue_name = issue.name.encode('utf-8')

            stdout.write('Processing issue %s...' % issue_name)
            stdout.flush()

            # If this fails, we want to see the errors in the output, so we
            # don't check for errors here.
            issue.process()

            stdout.write(' done\n')
