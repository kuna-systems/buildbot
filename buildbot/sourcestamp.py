# -*- test-case-name: buildbot.test.test_sourcestamp -*-

from zope.interface import implements
from twisted.persisted import styles
from buildbot import util, interfaces

class SourceStamp(util.ComparableMixin, styles.Versioned):
    """This is a tuple of (branch, revision, patchspec, changes).

    C{branch} is always valid, although it may be None to let the Source
    step use its default branch. There are three possibilities for the
    remaining elements:
     - (revision=REV, patchspec=None, changes=None): build REV. If REV is
       None, build the HEAD revision from the given branch. Note that REV
       must always be a string: SVN, Perforce, and other systems which use
       integers should provide a string here, but the Source checkout step
       will integerize it when making comparisons.
     - (revision=REV, patchspec=(LEVEL, DIFF), changes=None): checkout REV,
       then apply a patch to the source, with C{patch -pPATCHLEVEL <DIFF}.
       If REV is None, checkout HEAD and patch it.
     - (revision=None, patchspec=None, changes=[CHANGES]): let the Source
       step check out the latest revision indicated by the given Changes.
       CHANGES is a tuple of L{buildbot.changes.changes.Change} instances,
       and all must be on the same branch.
    """

    persistenceVersion = 1

    # all four of these are publically visible attributes
    branch = None
    revision = None
    patch = None
    changes = ()
    ssid = None # filled in by db.get_sourcestampid()

    compare_attrs = ('branch', 'revision', 'patch', 'changes')

    implements(interfaces.ISourceStamp)

    def __init__(self, branch=None, revision=None, patch=None,
                 changes=None):
        if branch is not None:
            assert isinstance(branch, str), type(branch)
        if revision is not None:
            if isinstance(revision, int):
                revision = str(revision)
            assert isinstance(revision, str), type(revision)
        if patch is not None:
            patch_level = patch[0]
            assert isinstance(patch_level, int), type(patch_level)
            patch_diff = patch[1]
            assert isinstance(patch_diff, str), type(patch_diff)
            if len(patch) > 2:
                patch_subdir = patch[2]
                assert isinstance(patch_subdir, str)
        self.branch = branch
        self.revision = revision
        self.patch = patch
        if changes:
            self.changes = tuple(changes)
            # set branch and revision to most recent change
            self.branch = changes[-1].branch
            if self.branch is not None:
                assert isinstance(self.branch, str), type(self.branch)
            self.revision = str(changes[-1].revision)
            if self.revision is not None:
                assert isinstance(self.revision, str), type(self.revision)

    def canBeMergedWith(self, other):
        if other.branch != self.branch:
            return False # the builds are completely unrelated

        if self.changes and other.changes:
            # TODO: consider not merging these. It's a tradeoff between
            # minimizing the number of builds and obtaining finer-grained
            # results.
            return True
        elif self.changes and not other.changes:
            return False # we're using changes, they aren't
        elif not self.changes and other.changes:
            return False # they're using changes, we aren't

        if self.patch or other.patch:
            return False # you can't merge patched builds with anything
        if self.revision == other.revision:
            # both builds are using the same specific revision, so they can
            # be merged. It might be the case that revision==None, so they're
            # both building HEAD.
            return True

        return False

    def mergeWith(self, others):
        """Generate a SourceStamp for the merger of me and all the other
        BuildRequests. This is called by a Build when it starts, to figure
        out what its sourceStamp should be."""

        # either we're all building the same thing (changes==None), or we're
        # all building changes (which can be merged)
        changes = []
        changes.extend(self.changes)
        for req in others:
            assert self.canBeMergedWith(req) # should have been checked already
            changes.extend(req.changes)
        newsource = SourceStamp(branch=self.branch,
                                revision=self.revision,
                                patch=self.patch,
                                changes=changes)
        return newsource

    def getAbsoluteSourceStamp(self, got_revision):
        return SourceStamp(branch=self.branch, revision=got_revision,
                           patch=self.patch)

    def getText(self):
        # note: this won't work for VC systems with huge 'revision' strings
        if self.revision is None:
            return [ "latest" ]
        text = [ str(self.revision) ]
        if self.branch:
            text.append("in '%s'" % self.branch)
        if self.patch:
            text.append("[patch]")
        return text

    def getHTMLDict(self):
        if self.revision is None:
            return dict(rev='latest')
        d = dict(rev=self.revision)
        if self.branch:
            d['branch'] = self.branch            
        if self.patch:
            d['patch'] = True
        return d

    def asDict(self):
        result = {}
        # Constant
        result['revision'] = self.revision
        # TODO(maruel): Make the patch content a suburl.
        result['patch'] = self.patch
        result['branch'] = self.branch
        result['changes'] = [c.asDict() for c in getattr(self, 'changes', [])]
        return result

    def upgradeToVersion1(self):
        # version 0 was untyped; in version 1 and later, types matter.
        print "upgrading sourcestamp to version 1"
        if self.branch is not None and not isinstance(self.branch, str):
            self.branch = str(self.branch)
        if self.revision is not None and not isinstance(self.revision, str):
            self.revision = str(self.revision)
        if self.patch is not None and not isinstance(self.patch, str):
            self.patch = str(self.patch)

# vim: set ts=4 sts=4 sw=4 et:
