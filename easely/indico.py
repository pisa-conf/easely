# Copyright (C) 2022, luca.baldini@pi.infn.it
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""INDICO interface.

This is using the INDICO API to help accessing the conference content, see
https://docs.getindico.io/en/stable/
"""

import datetime
import json
import os

import pandas as pd
import requests

from pisameet import logger
from pisameet.program import PosterCollectionBase, DATETIME_FORMAT
from pisameet.qrcode_ import generate_qrcode


# pylint: disable=invalid-name



def retrieve_info(url: str, file_path: str , detail: str = 'sessions', overwrite: bool = False):
    """Retrieve the contributions, grouped by session for a given conference,
    following the instructions at
    https://docs.getindico.io/en/stable/http-api/exporters/event/#sessions

    According to the documentation, this setting details to "sessions" includes
    details about the different sessions and groups contributions by sessions.
    The top-level contributions list only contains contributions which are not
    assigned to any session. Subcontributions are included in this details level,
    too.

    Arguments
    ---------
    url : str
        The indico url for the conference, e.g., https://agenda.infn.it/export/event/8397.json

    file_path : str
        The path for the output .json file

    detail : str
        The level of detail for the dump, see
        https://docs.getindico.io/en/stable/http-api/exporters/event

    overwrite : bool
        Overwrite the output file.
    """
    assert file_path.endswith('.json')
    if os.path.exists(file_path) and overwrite is False:
        logger.info('File %s exists, skipping (delete it or set overwrite=False)...', file_path)
        return
    logger.info('Retrieving program from %s...', url)
    resp = requests.get(f'{url}?detail={detail}&pretty=yes')
    data = resp.json()
    logger.info('Saving data to %s...', file_path)
    with open(file_path, 'w') as f:
        json.dump(data, f)
    logger.info('Done.')




class ConferenceInfo(dict):

    """Small convenience class describing the full list of contributions for a
    conference, see https://docs.getindico.io/en/stable/api/contribution/

    The underlying .json file is parsed as a Python dictionary containing the
    following keys at the top level:
    ['ts', 'url', 'additionalInfo', 'count', 'results', '_type']

    (If I understand correctly `count` is typically 1 and indicates the length
    of the `results` field, which is a list whose first element contains
    the actual data.)

    Now, `results[0]` is another dictionary whose keys are
    ['_type', 'id', 'title', 'description', 'startDate', 'timezone', 'endDate',
    'room', 'location', 'address', 'type', 'references', '_fossil', 'categoryId',
    'category', 'note', 'roomFullname', 'url', 'creationDate', 'creator',
    'hasAnyProtection', 'roomMapURL', 'folders', 'chairs', 'material', 'keywords',
    'visibility', 'contributions', 'sessions']

    The last two are the relevant pieces of information, containing the sessions,
    as well as the orphan contributions, if any.

    Each session is a dictionary with the following keys:
    ['_type', '_fossil', 'id', 'conference', 'startDate', 'endDate', 'description',
    'title', 'url', 'contributions', 'note', 'session', 'room', 'roomFullname',
    'location', 'inheritLoc', 'inheritRoom', 'slotTitle', 'address', 'conveners'],
    the most relevant fields being:

    * 'startDate', e.g., "{'date': '2015-05-28', 'time': '15:45:00', 'tz': 'Europe/Rome'}"
    * 'endDate', e.g., "{'date': '2015-05-28', 'time': '19:25:00', 'tz': 'Europe/Rome'}"
    * 'title', e.g., "Front end, Trigger, DAQ and Data Management"
    * 'url', e.g., "https://agenda.infn.it/event/8397/sessions/11528/"
    * 'contributions', listing all the contributions of the session.

    Finally, each entry in the list of contributions has the following keys:
    ['_type', '_fossil', 'id', 'db_id', 'friendly_id', 'title', 'startDate',
    'endDate', 'duration', 'roomFullname', 'room', 'note', 'location', 'type',
    'description', 'folders', 'url', 'material', 'speakers', 'primaryauthors',
    'coauthors', 'keywords', 'track', 'session', 'references', 'board_number']

    Arguments
    ---------
    file_path : str
        The path to the .json file containing all the contributions.
    """

    def __init__(self, file_path, session_dict: dict = None):
        """Constructor.
        """
        super().__init__()
        logger.info('Loading conference contributions from %s...', file_path)
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Parse the json hierarchy.
        results = data['results'][0]
        sessions = results['sessions']
        logger.info('%d session (s) found', len(sessions))
        for session in sessions:
            print(session['id'], session['title'])
        # If we are passing a section dictionary of the form {session_id: session_title},
        # we want to do a few things:
        # * filter the sessions in the input json file and ;
        # * sort the sessions by id in the dictionary;
        # * tweak the session title is necessary.
        if session_dict is not None:
            logger.info('Filtering sessions...')
            for _id, _title in session_dict.items():
                for session in sessions:
                    if session['id'] == _id:
                        session['title'] = _title
                        self[_title] = session
        contributions = results['contributions']
        if len(contributions):
            logger.warning('%d orphan contribution(s) found...', len(contributions))
        else:
            logger.info('No orphan contributions found...')
        #logger.info(f'Program info:\n{self}')

    def contribution_ids(self):
        """Return all the contribution ids.
        """
        logger.info('Retrieving all the contribution identifiers...')
        ids = []
        for session in self.values():
            for contribution in session['contributions']:
                ids.append(int(contribution['id']))
        logger.info('Done, %d contribution(s) found.', len(ids))
        ids.sort()
        return ids

    @staticmethod
    def pretty_print(contribution):
        """Pretty print.
        """
        identifier = contribution['friendly_id']
        try:
            speaker = contribution['speakers'][0]
            full_name = speaker['fullName']
        except IndexError:
            logger.warning('Cannot retrieve speaker for contribution %d', identifier)
            full_name = 'N/A'
        title = contribution['title']
        return f'[{identifier}] {full_name}: "{title}"'

    @staticmethod
    def _format_date(date_dict: str, fmt: str = DATETIME_FORMAT):
        """Format a date in the .json file according to the date format in use
        for the excel configuration file.

        This means turning {'date': '2015-05-28', 'time': '15:45:00', 'tz': 'Europe/Rome'}
        into 28/05/2015 15:45.
        """
        text = f'{date_dict["date"]} {date_dict["time"]}'
        d = datetime.datetime.strptime(text, '%Y-%m-%d %H:%M:%S')
        return d.strftime(fmt)

    def dump_excel(self, file_path):
        """Dump the contribution list as an excel file.
        """
        logger.info('Dumping conference info to %s...', file_path)
        writer = pd.ExcelWriter(file_path, engine='xlsxwriter')

        # Create the master sheet with the session data.
        def _session_data(key, change_hour='13:30:00'):
            """Small nested function to facilitate the session data retrival.
            """
            if key == 'startDate':
                _data = []
                for session in self.values():
                    date_dict = session[key]
                    if int(date_dict['time'].split(':')[0]) < 13:
                        date_dict['time'] = '00:01:00'
                    else:
                        date_dict['time'] = change_hour
            if key == 'endDate':
                _data = []
                for session in self.values():
                    date_dict = session[key]
                    if int(date_dict['time'].split(':')[0]) < 13:
                        date_dict['time'] = change_hour
                    else:
                        date_dict['time'] = '21:00:00'
            if key in ('startDate', 'endDate'):
                return [self._format_date(session[key]) for session in self.values()]
            return [str(session[key]) for session in self.values()]

        data = [_session_data(key) for key in ('id', 'title', 'startDate', 'endDate')]
        df = pd.DataFrame({key: val for key, val in zip(PosterCollectionBase.PROGRAM_COL_NAMES, data)})
        df.to_excel(writer, sheet_name=PosterCollectionBase.PROGRAM_SHEET_NAME, index=False)
        sheet = writer.sheets[PosterCollectionBase.PROGRAM_SHEET_NAME]
        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 100)
        sheet.set_column(2, 3, 20)

        # Create the ancillary sheets with the actual contributions.
        def _warning_message(msg, contribution, max_title_length=30):
            """Small nested function to provide useful diagnostics in case of missing data.
            """
            logger.warning('%s for contribution %s (%s...)', msg, contribution['id'],
                contribution['title'][:max_title_length])

        # Loop over all the contributions in the session and retrieve the data.
        # Note that, rather than doing this by column, we do it by row (i.e., by
        # contribution), the basic idea being that we can provide more granular
        # diagnostics if data are missing, at the expense of code beauty.
        for session in self.values():
            data = [[], [], [], [], [], []]
            for contrib in session['contributions']:
                _id = contrib['id']
                _title = contrib['title']
                _url = contrib['url']
                _db_id = contrib['db_id']
                try:
                    first_speaker = contrib['speakers'][0]
                except IndexError as e:
                    _warning_message('No speaker(s)', contrib)
                    first_speaker = None
                if first_speaker is not None:
                    _first_name = first_speaker['first_name']
                    _last_name = first_speaker['last_name']
                    _affiliation = first_speaker['affiliation']
                    if _first_name == '':
                        _warning_message('No first name', contrib)
                    if _last_name == '':
                        _warning_message('No last name', contrib)
                    if _affiliation == '':
                        _warning_message('No affiliation', contrib)
                else:
                    _first_name, _last_name, _affiliation = 'N/A', 'N/A', 'N/A'
                for col, val in zip(data, (_id, _db_id, _title, _first_name, _last_name, _affiliation)):
                    col.append(val)

            # Placeholder for the screen id.
            screen_id = [i % 20 + 1 for i in range(len(session['contributions']))]
            data.insert(2, screen_id)
            df = pd.DataFrame({key: val for key, val in zip(PosterCollectionBase.SESSION_COL_NAMES, data)})
            sheet_name = str(session['id'])
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            sheet = writer.sheets[sheet_name]
            sheet.set_column(0, 2, 12)
            sheet.set_column(3, 3, 100)
            sheet.set_column(4, 5, 20)
            sheet.set_column(6, 6, 60)
        logger.info('Writing output file...')
        writer.save()
        logger.info('Done.')

    @staticmethod
    def download_urls(contribution, filters=('pdf', 'ppt', 'pptx')):
        """Return the list of all download urls and fellow timestamp for
        a given contribution.

        This is looping over all the folders and all the files in the folders, and
        filtering by file type.

        Arguments
        ---------
        contribution : dict
            The conference contribution.

        filters : tuple of str
            The allowed file types.
        """
        urls = []
        for folder in contribution['folders']:
            for attachment in folder['attachments']:
                url = attachment['download_url']
                if url.split('.')[-1].lower() in filters:
                    timestamp = attachment['modified_dt']
                    urls.append((url, timestamp))
        if len(urls) == 0:
            logger.warning('No attachment for "%s"', contribution["title"])
        return urls

    def download_attachments(self, folder_path: str, separator: str = '-',
        filters=('pdf', 'ppt', 'pptx', 'png', 'jpg', 'jpeg'), dry_run: bool = False):
        """Download all the files attached to the given conference program.
        """
        logger.info('Downloading files...')
        num_downloads = 0
        for session in self.values():
            logger.info('Processing session "%s"', session["title"])
            for contribution in session['contributions']:
                for url, timestamp in self.download_urls(contribution, filters):
                    file_name = f'{int(contribution["id"]):03d}{separator}{os.path.basename(url)}'
                    file_path = os.path.join(folder_path, file_name)
                    tstamp_file_path = f'{file_path}.tstamp'
                    # If we have the file locally, and we have track of the
                    # timestamp, and that matches the one in the .json file,
                    # thers is no point in downloading another identical copy.
                    if os.path.exists(file_path) and os.path.exists(tstamp_file_path) \
                        and open(tstamp_file_path).read() == timestamp:
                        logger.debug('%s up to date, skipping...', file_path)
                        continue
                    # Otherwise we're good to go.
                    logger.info('Downloading %s -> %s...', url, file_path)
                    if not dry_run:
                        response = requests.get(url)
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        num_downloads += 1
                    # And, of course, we need to write the timestamp, as well.
                    logger.info('Writing file timestamp to %s...', file_path)
                    if not dry_run:
                        with open(tstamp_file_path, 'w') as f:
                            f.write(timestamp)
        logger.info(f'{num_downloads} additional file(s) downloaded.')

    def generate_qr_codes(self, folder_path):
        """Generate all the QR codes for the poster contributions.
        """
        for session in self.values():
            for contrib in session['contributions']:
                url = contrib['url']
                file_name = f'{contrib["friendly_id"]:03}.png'
                file_path = os.path.join(folder_path, file_name)
                generate_qrcode(url, file_path)

    def __str__(self):
        """String formatting.
        """
        return '\n'.join([f'- {key} ({len(val["contributions"])} contributions)' \
            for key, val in self.items()])
