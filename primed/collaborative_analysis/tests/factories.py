from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceFactory,
)
from factory import LazyAttribute, SubFactory, post_generation
from factory.django import DjangoModelFactory

from primed.users.tests.factories import UserFactory

from .. import models


class CollaborativeAnalysisWorkspaceFactory(DjangoModelFactory):
    class Meta:
        model = models.CollaborativeAnalysisWorkspace
        skip_postgeneration_save = True

    workspace = SubFactory(WorkspaceFactory, workspace_type="collab_analysis")
    custodian = SubFactory(UserFactory)
    analyst_group = SubFactory(
        ManagedGroupFactory,
        name=LazyAttribute(lambda o: "analysts_{}".format(o.factory_parent.workspace.name)),
    )

    @post_generation
    def authorization_domains(self, create, extracted, **kwargs):
        # Add an authorization domain.
        if not create:
            # Simple build, do nothing.
            return

        # Create an authorization domain.
        auth_domain = ManagedGroupFactory.create(name="auth_{}".format(self.workspace.name))
        self.workspace.authorization_domains.add(auth_domain)

    @post_generation
    def source_workspaces(self, create, extracted, **kwargs):
        if not create or not extracted:
            # Simple build, do nothing.
            return

        self.source_workspaces.add(*extracted)
