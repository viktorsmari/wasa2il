# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-01-18 21:10
from __future__ import unicode_literals

from django.db import migrations

from datetime import datetime

'''
IMPORTANT INFORMATION!

Originally, this migration used to simply run .process() on each issue in
order to reprocess them all (for reasons explained elsewhere). This required
the Issue models' process() function. In the original version of this
migration, it was imported like "from issue.models import Issue", which
imported the process-function successfully.

This however, presented the following problem.

When this migration is run, the models have only been migrated up to the
previous migration. But the model in issue.models may have changed (and at the
time of this writing, has changed). At that point, there is an inconsistency
between the migration's understanding of the model and the model as it appears
in issue.models. If we import the code itself, as was done previously, this
inconsistency may lead to errors because the model in the code has begun to
differ from the model as it appeared when this migration was first created.

The solution to this, although ugly, is to copy, verbatum, the needed
functions for reprocessing to take place. They are inserted here only
minimally changed in such a way, that instead of calling f.e. issue.process(),
process(issue) is called. This change has been applied to all the functions in
which it is needed. In order to avoid deviance from the existing code at this
point, the parameter's name, "self" is retained in each case, so as to change
the code as little as possible to just barely do the job of reprocessing
everything.

And what did we learn today, kids? Don't import models directly in migrations!
Use apps.get_model()!
'''

def reprocess_issues(apps, schema_editor):
    Issue = apps.get_model('issue', 'Issue')

    def majority_reached(self):
        result = False

        if self.special_process == 'accepted_at_assembly':
            result = True
        else:
            if self.votecount > 0:
                result = float(self.votecount_yes) / self.votecount > float(self.majority_percentage) / 100

        return result


    # preferred_version() finds the most proper, previous documentcontent to build a new one on.
    # It prefers the latest accepted one, but if it cannot find one, it will default to the first proposed one.
    # If it finds neither a proposed nor accepted one, it will try to find the first rejected one.
    # It will return None if it finds nothing and it's the calling function's responsibility to react accordingly.
    # TODO: Make this faster and cached per request. Preferably still Pythonic. -helgi@binary.is, 2014-07-02
    def preferred_version(self):
        # Latest accepted version...
        accepted_versions = self.documentcontent_set.filter(status='accepted').order_by('-order')
        if accepted_versions.count() > 0:
            return accepted_versions[0]

        # ...and if none are found, find the earliest proposed one...
        proposed_versions = self.documentcontent_set.filter(status='proposed').order_by('order')
        if proposed_versions.count() > 0:
            return proposed_versions[0]

        # ...boo, go for the first rejected one?
        rejected_versions = self.documentcontent_set.filter(status='rejected').order_by('order')
        if rejected_versions.count() > 0:
            return rejected_versions[0]

        # ...finally and desperately search for things with unknown status
        all_versions = self.documentcontent_set.order_by('order')
        if all_versions.count() > 0:
            return all_versions[0]
        else:
            return None

    def issue_state(self):
        # Short-hands.
        now = datetime.now()
        deadline_votes = self.deadline_votes
        deadline_proposals = self.deadline_proposals
        deadline_discussions = self.deadline_discussions

        if deadline_votes < now:
            return 'concluded'
        elif deadline_proposals < now:
            return 'voting'
        elif deadline_discussions < now:
            return 'accepting_proposals'
        else:
            return 'discussion'

    def process(self):

        # We're not interested in issues that don't have documentcontents.
        # They shouldn't actually exist, by the way. They were possible in
        # earlier versions but the system no longer offers creating them
        # except using a documentcontent. These issues should be dealt with
        # somehow, at some point.
        if self.documentcontent == None:
            return False

        # Short-hands.
        documentcontent = self.documentcontent
        document = documentcontent.document

        if issue_state(self) == 'concluded' and not self.is_processed:

            # Figure out the current documentcontent's predecessor.
            # See function for details.
            documentcontent.predecessor = preferred_version(document)

            # Figure out if issue was accepted or rejected.
            if majority_reached(self):
                self.documentcontent.status = 'accepted'

                # Since the new version has been accepted, deprecate
                # previously accepted versions.
                prev_contents = document.documentcontent_set.exclude(
                    id=documentcontent.id
                ).filter(status='accepted')
                for prev_content in prev_contents:
                    prev_content.status = 'deprecated'
                    prev_content.save()

            else:
                self.documentcontent.status = 'rejected'

            self.vote_set.all().delete()

            self.is_processed = True

            documentcontent.save()

            self.save()

        return True


    # The order is actually very important here, because things like
    # predecessors and deprecated issues are determined by sequence.
    issues = Issue.objects.order_by('created')

    for issue in issues:
        issue.is_processed = False
        issue.save()
        process(issue)


def dummy_function(apps, schema_editor):
    # Only here to make reversing migrations possible.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('issue', '0020_remove_vote_power_when_cast'),
    ]

    operations = [
        migrations.RunPython(reprocess_issues, dummy_function)
    ]
