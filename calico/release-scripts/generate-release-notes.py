#!/usr/bin/env python
import github
from github import Github  # https://github.com/PyGithub/PyGithub
import os
import re
import io
import string
import datetime

# First create a Github instance. Create a token through Github website - provide "repo" auth.
g = Github(os.environ.get('GITHUB_TOKEN'))

# The milestone to generate notes for.
assert os.environ.get('VERSION')
VERSION=os.environ.get('VERSION')
MILESTONE = f"Calico {VERSION}"
RELEASE_STREAM = ".".join(VERSION.split(".")[:2])

# The file where we'll store the release notes.
FILENAME = f"_includes/release-notes/{VERSION}-release-notes.md"

# Repositories we care about. Add repositories here to include them in release
# note generation.
REPOS = [
        "calico",
        "node",
        "felix",
        "typha",
        "libcalico-go",
        "kube-controllers",
        "routereflector",
        "cni-plugin",
        "confd",
        "bird",
        "calico-bgp-daemon",
        "app-policy",
        "pod2daemon",
]

# Returns a dictionary where the keys are repositories, and the values are
# a list of issues in the repository which match the milestone and
# have a `release-note-required` label.
def issues_by_repo():
    all_issues = {}
    org = g.get_organization("projectcalico")
    for repo in org.get_repos():
        if repo.name not in REPOS:
            continue
        print(f"Processing repo {org.login}/{repo.name}")

        # Find the milestone. This finds all open milestones.
        milestones = repo.get_milestones()
        for m in milestones:
            if m.title == MILESTONE:
                # Found the milestone in this repo - look for issues (but only
                # ones that have been closed!)
                # TODO: Assert that the PR has been merged somehow?
                print(f"  found milestone {m.title}")
                try:
                    label = repo.get_label("release-note-required")
                except github.UnknownObjectException:
                    # Label doesn't exist, skip this repo.
                    break
                issues = repo.get_issues(milestone=m, labels=[label], state="closed")
                for i in issues:
                    all_issues.setdefault(repo.name, []).append(i)
    return all_issues

# Takes an issue and returns the appropriate release notes from that
# issue as a list.  If it has a release-note section defined, that is used.
# If not, then it simply returns the title.
def extract_release_notes(issue):
    if matches := re.findall(
        r'```release-note(.*?)```', issue.body, re.DOTALL
    ):
        return [m.strip() for m in matches]
    print(f"WARNING: {issue.number} has no release-note section")
    return [issue.title.strip()]

if __name__ == "__main__":
    # Get the list of issues.
    all_issues = issues_by_repo()

    # Get date in the right format.
    date = datetime.date.today().strftime("%d %b %Y")

    # Write release notes out to a file.
    with io.open(FILENAME, "w", encoding='utf-8') as f:
        f.write(u"%s\n\n" % date)
        f.write(u"#### Headline feature 1\n\n")
        f.write(u"#### Headline feature 2\n\n")
        f.write(u"#### Bug fixes\n\n")
        f.write(u"#### Other changes\n\n")
        for repo, issues in all_issues.items():
            print(f"Writing notes for {repo}")
            for i in issues:
                for note in extract_release_notes(i):
                    f.write(" - %s [%s #%d](%s) (@%s)\n" % (note, repo, i.number, i.html_url, i.user.login))

    print("")
    print(f"Release notes written to {FILENAME}")
    print("Please review for accuracy, and format appropriately before releasing.")
