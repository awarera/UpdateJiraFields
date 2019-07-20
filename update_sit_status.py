#!/usr/bin/env python
"""
The purpose of this script is to update a given field status for all Jira
issues that are part of a successful labelled Jenkins release.

.. codeauthor:: Abdulrahman Abdullahi

Usage
=====
.. argparse::
   :prog: update_field_status.py
   :module: update_field_status
   :func: argparser

This script is typically triggered by Jenkins

Environment variables
---------------------
- $JENKINS_URL
- $JIRA_URL
- $JIRA_USER
- $JIRA_PASSWD

"""
import logging
import re
import os.path
import requests
from jira import JIRA
from jira import JIRAError
from landg.batch import Batch


class JiraStatusUpdater(Batch):
    """Main flow control based on the landg Batch framework
    """
    def __init__(self):
        """Setup argparse
        """
        super().__init__()
        self.argument_parser.description = 'Update Jira field status'
        self.argument_parser.add_argument(
            '--jenkins_url', default=os.getenv('JENKINS_URL'),
            help='URL for Jenkins. Default: $JENKINS_URL')
        self.argument_parser.add_argument(
            '--jira_url', default=os.getenv('JIRA_URL'),
            help='Base URL of the Jira server. Default: $JIRA_URL')
        self.argument_parser.add_argument(
            '--jira_user', default=os.getenv('JIRA_USER'),
            help='Jira username. Default: $JIRA_USER')
        self.argument_parser.add_argument(
            '--jira_passwd', default=os.getenv('JIRA_PASSWD'),
            help='Jira password. Default: $JIRA_PASSWD')


    def jira_login(self):
        """Log in to Jira

        :returns:
            decoded JSON structure

        """
        try:
            jira = JIRA(self.args.jira_url, basic_auth=(self.args.jira_user,
                                                        self.args.jira_passwd))
            logging.info('Successfully logged into jira')
            return jira

        except JIRAError as err:
            logging.error(f"Login to JIRA failed because {err}")


    def update_jira_status(self, release_name, customfield_number, new_value):
        """Update a custom field value for all JIRA issues
        that correspond to a given Jenkins release/build.

        :param str release_name:
            Jenkins release that corresponds to a Jira fix_version
        :param str customfield_number:
            Jira customfield number
        :param str new_value:
            New value for the custom field

        """
        logging.info('Searching for Jira issues...')
        issues = self.jira_login().search_issues(
            f'fixVersion={release_name} AND cf[{customfield_number}]="Pending automated test"')
        if issues:
            logging.info(
                f'Updating {len(issues)} Jira issues to Success (automated regression test)')
            for issue in issues:
                issue.update(fields={f'customfield_{customfield_number}': {'value': new_value}})
            logging.info(f'{len(issues)} Jira issues were updated')
        else:
            logging.info(f"No issues found in release: {release_name}")


    def task1_check_jenkins_release(self):
        """ Determine whether the last Jenkins build is a successful labelled release
        and if so, for all Jira issues that correspond to it have the field status
        set from 'Pending automated test' to 'Success (automated regression test)'.

        To find customfield names & their corresponding numbers please vifield:
        http://BASE-JIRA-URL/rest/api/2/issue/ISSUE-NAME/
        Make sure to replace 'BASE-JIRA-URL' & 'ISSUE-NAME' with relevant data.
        E.G http://lawejen001.azure01.csp.local:10667/rest/api/2/issue/ECS2-2087/
        """
        jenkins_data = jenkins_query(self.args.jenkins_url)

        build_display_name = jenkins_data['displayName']
        build_number_pattern = re.compile(r"^#\d*$")
        if build_number_pattern.match(build_display_name):
            logging.info(f"{build_display_name} is an unlabelled release. Nothing to do")
        else:
            if jenkins_data['result'] == 'SUCCESS':
                self.update_jira_status(build_display_name,
                                        10803,
                                        'Success (automated regression test)')
            else:
                logging.error(f'Labelled release: {build_display_name} failed. Nothing to do')


def jenkins_query(url):
    """Query the Jenkins JSON API

    :param url:
        URL of the browser web page to query
    :returns:
        decoded JSON structure

    """
    assert url.endswith('/')
    logging.info(f'Fetching Jenkins data from {url}')
    response = requests.get(f'{url}api/json', timeout=60)
    response.raise_for_status()
    return response.json()


def argparser():
    """Hook for sphinx-argparse to automatically produce
    usage information from argparse
    """
    return JiraStatusUpdater().argument_parser


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    JiraStatusUpdater().main()
