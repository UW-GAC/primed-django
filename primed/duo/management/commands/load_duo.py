import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pronto import Ontology

from ... import models


class Command(BaseCommand):
    help = "Loads the DUO ontology."

    def add_arguments(self, parser):
        parser.add_argument(
            "--duo_file",
            type=str,
            required=False,
            help="Location of DUO owl file (default: primed/duo/fixtures/duo-basic.owl)",
        )
        parser.add_argument(
            "--permissions-code",
            type=str,
            default="DUO:0000001",
            required=False,
            help="Parent term representing the term for data use permission (default: DUO:0000001)",
        )
        parser.add_argument(
            "--modifiers-code",
            type=str,
            default="DUO:0000017",
            required=False,
            help="Parent term representing the term for data use modifiers (default: DUO:0000017)",
        )

    def handle(self, *args, **options):
        # Error if anything is loaded into either model.
        if models.DataUsePermission.objects.exists() or models.DataUseModifier.objects.exists():
            raise CommandError("At least one DataUsePermission or DataUseModifier already exists.")

        duo_file = options["duo_file"]
        if not duo_file:
            # Use the default.
            tmppath = os.path.dirname(os.path.realpath(__file__))
            duo_file = os.path.join(tmppath, os.pardir, os.pardir, "fixtures", "duo-basic.owl")
        self.stdout.write("Loading DUO terms from {}".format(duo_file))

        # Read in the ontology.
        duo = Ontology(duo_file)

        # Check that specified terms are in the file.
        permissions_code = options["permissions_code"]
        if permissions_code not in duo.terms():
            msg = "permissions-code '{}' not in available terms.".format(permissions_code)
            raise CommandError(self.style.ERROR(msg))

        modifiers_code = options["modifiers_code"]
        if modifiers_code not in duo.terms():
            msg = "modifiers-code '{}' not in available terms.".format(modifiers_code)
            raise CommandError(self.style.ERROR(msg))

        with transaction.atomic():
            # Create objects.
            for term in duo[permissions_code].subclasses(with_self=False, distance=1):
                self._create_permission(term, parent=None)

            for term in duo[modifiers_code].subclasses(with_self=False, distance=1):
                self._create_modifier(term, parent=None)

        # Hard code terms for DUP and DUMs
        msg = "{} DataUsePermissions and {} DataUseModifiers loaded.".format(
            models.DataUsePermission.objects.count(),
            models.DataUseModifier.objects.count(),
        )
        self.stdout.write(self.style.SUCCESS(msg))

    def _get_term_abbreviation(self, term):
        """Return the abbreviation for the term."""
        abbreviation = [a.literal for a in term.annotations if "shorthand" in a.property]
        if len(abbreviation) != 1:
            import ipdb

            ipdb.set_trace()
        return abbreviation[0]

    def _get_term_comment(self, term):
        """Return an appropriate comment for the term."""
        if term.comment:
            comment = term.comment
        else:
            comment = ""
        return comment

    def _create_permission(self, term, parent=None):
        obj = models.DataUsePermission(
            identifier=term.id,
            abbreviation=self._get_term_abbreviation(term),
            term=term.name,
            definition=str(term.definition),
            comment=self._get_term_comment(term),
            parent=parent,
        )
        obj.full_clean()
        obj.save()
        for child in term.subclasses(with_self=False, distance=1):
            self._create_permission(child, parent=obj)

    def _create_modifier(self, term, parent=None):
        if term.obsolete:
            return
        obj = models.DataUseModifier(
            identifier=term.id,
            abbreviation=self._get_term_abbreviation(term),
            term=term.name,
            definition=str(term.definition),
            comment=self._get_term_comment(term),
            parent=parent,
        )
        obj.full_clean()
        obj.save()
        for child in term.subclasses(with_self=False, distance=1):
            self._create_modifier(child, parent=obj)
