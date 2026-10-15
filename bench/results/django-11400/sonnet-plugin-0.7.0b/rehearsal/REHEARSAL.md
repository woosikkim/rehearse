# Rehearsal: admin related filter ordering
### S1: order_by(*()) on Permission
- saw: Meta.ordering set; order_by(*()).default_ordering False, ordered False vs all().ordered True
- means: empty ordering tuple disables Meta.ordering; fix: only call order_by when ordering non-empty, and pass admin ordering in RelatedOnly
repro: /opt/miniconda3/envs/testbed/bin/python -c 'from django.contrib.auth.models import Permission'
