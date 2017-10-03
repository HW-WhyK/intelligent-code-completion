import re
import pytz
from datetime import datetime
from collections import defaultdict
import lxml.html
import scrapelib
from openstates.utils.lxmlize import LXMLMixin
from pupa.scrape import Scraper, Bill, VoteEvent


class NVBillScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone('PST8PDT')
    _classifiers = (
        ('Approved by the Governor', 'executive-signature'),
        ('Bill read. Veto not sustained', 'veto-override-passage'),
        ('Bill read. Veto sustained', 'veto-override-failure'),
        ('Enrolled and delivered to Governor', 'executive-receipt'),
        ('From committee: .+? adopted', 'committee-passage'),
        ('From committee: .+? pass', 'committee-passage'),
        ('Prefiled. Referred', ['introduction', 'referral-committee']),
        ('Read first time. Referred', ['reading-1', 'referral-committee']),
        ('Read first time.', 'reading-1'),
        ('Read second time.', 'reading-2'),
        ('Read third time. Lost', ['failure', 'reading-3']),
        ('Read third time. Passed', ['passage', 'reading-3']),
        ('Read third time.', 'reading-3'),
        ('Rereferred', 'referral-committee'),
        ('Resolution read and adopted', 'passage'),
        ('Vetoed by the Governor', 'executive-veto')
    )

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)
        chambers = [chamber] if chamber else ['upper', 'lower']
        self._seen_votes = set()
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):

        session_slug = self.jurisdiction.session_slugs[session]
        if 'Special' in session_slug:
            year = session_slug[4:8]
        elif int(session_slug[:2]) >= 71:
            year = ((int(session_slug[:2]) - 71) * 2) + 2001
        else:
            return 'No data exists for %s' % session

        self.subject_mapping = defaultdict(list)
        if 'Special' not in session_slug:
            self.scrape_subjects(session_slug, session, year)

        if chamber == 'upper':
            yield from self.scrape_senate_bills(chamber, session_slug, session, year)
        else:
            yield from self.scrape_assem_bills(chamber, session_slug, session, year)

    def scrape_subjects(self, insert, session, year):
        url = 'http://www.leg.state.nv.us/Session/%s/Reports/' \
              'TablesAndIndex/%s_%s-index.html' % (insert, year, session)

        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        # first, a bit about this page:
        # Level0 are the bolded titles
        # Level1,2,3,4 are detailed titles, contain links to bills
        # all links under a Level0 we can consider categorized by it
        # there are random newlines *everywhere* that should get replaced

        subject = None

        for p in doc.xpath('//p'):
            if p.get('class') == 'Level0':
                subject = p.text_content().replace('\r\n', ' ')
            else:
                if subject:
                    for a in p.xpath('.//a'):
                        bill_id = (a.text.replace('\r\n', '') if a.text
                                   else None)
                        self.subject_mapping[bill_id].append(subject)

    def scrape_senate_bills(self, chamber, insert, session, year):
        doc_type = {2: 'bill', 4: 'resolution', 7: 'concurrent resolution',
                    8: 'joint resolution'}

        for docnum, bill_type in doc_type.items():
            parentpage_url = 'http://www.leg.state.nv.us/Session/%s/Reports/' \
                             'HistListBills.cfm?DoctypeID=%s' % (insert, docnum)
            links = self.scrape_links(parentpage_url)
            count = 0
            for link in links:
                count += 1
                page_path = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (insert, link)

                page = self.get(page_path).text
                page = page.replace(u"\xa0", " ")
                root = lxml.html.fromstring(page)

                bill_id = root.xpath('string(/html/body/div[@id="content"]' +
                                     '/table[1]/tr[1]/td[1]/font)')
                title = self.get_node(
                    root,
                    '//div[@id="content"]/table/tr[preceding-sibling::tr/td/'
                    'b[contains(text(), "By:")]]/td/em/text()')

                bill = Bill(bill_id,
                            legislative_session=session,
                            chamber=chamber,
                            title=title,
                            classification=bill_type
                            )
                bill.subject = list(set(self.subject_mapping[bill_id]))

                for table in root.xpath('//div[@id="content"]/table'):
                    if 'Bill Text' in table.text_content():
                        bill_text = table.xpath("string(tr/td[2]/a/@href)")
                        text_url = "http://www.leg.state.nv.us" + bill_text
                        bill.add_version_link(note="Bill Text",
                                              url=text_url,
                                              media_type='application/pdf')

                primary, secondary = self.scrape_sponsors(page)

                for leg in primary:
                    bill.add_sponsorship(name=leg,
                                         classification='primary',
                                         entity_type='person',
                                         primary=True)
                for leg in secondary:
                    bill.add_sponsorship(name=leg,
                                         classification='cosponsor',
                                         entity_type='person',
                                         primary=False)

                minutes_count = 2
                for mr in root.xpath('//table[4]/tr/td[3]/a'):
                    minutes = mr.xpath("string(@href)")
                    minutes_url = "http://www.leg.state.nv.us" + minutes
                    minutes_date_path = "string(//table[4]/tr[%s]/td[2])" % minutes_count
                    minutes_date = mr.xpath(minutes_date_path).split()
                    minutes_date = minutes_date[0] + minutes_date[1] + minutes_date[2] + " Agenda"
                    # bill.add_document(minutes_date, minutes_url)
                    bill.add_document_link(note=minutes_date,
                                           url=minutes_url)
                    minutes_count = minutes_count + 1

                self.scrape_actions(root, bill, "upper")
                yield from self.scrape_votes(page, page_path, bill, insert, year)
                bill.add_source(page_path)
                yield bill

    def scrape_assem_bills(self, chamber, insert, session, year):

        doc_type = {1: 'bill', 3: 'resolution', 5: 'concurrent resolution',
                    6: 'joint resolution', 9: 'petition'}
        for docnum, bill_type in doc_type.items():
            parentpage_url = 'http://www.leg.state.nv.us/Session/%s/' \
                             'Reports/HistListBills.cfm?DoctypeID=%s' % (insert, docnum)
            links = self.scrape_links(parentpage_url)
            count = 0
            for link in links:
                count = count + 1
                page_path = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (insert, link)
                page = self.get(page_path).text
                page = page.replace(u"\xa0", " ")
                root = lxml.html.fromstring(page)
                root.make_links_absolute("http://www.leg.state.nv.us/")

                bill_id = root.xpath('string(/html/body/div[@id="content"]'
                                     '/table[1]/tr[1]/td[1]/font)')
                title = self.get_node(
                    root,
                    '//div[@id="content"]/table/tr[preceding-sibling::tr/td/'
                    'b[contains(text(), "By:")]]/td/em/text()')

                bill = Bill(bill_id, legislative_session=session, chamber=chamber,
                            title=title, classification=bill_type)

                bill.subject = list(set(self.subject_mapping[bill_id]))
                billtext = root.xpath("//b[text()='Bill Text']")[0].getparent().getnext()
                text_urls = billtext.xpath("./a")
                for text_url in text_urls:
                    version_name = text_url.text.strip()
                    version_url = text_url.attrib['href']
                    bill.add_version_link(note=version_name, url=version_url,
                                          media_type='application/pdf')

                primary, secondary = self.scrape_sponsors(page)

                for leg in primary:
                    bill.add_sponsorship(classification='primary',
                                         name=leg, entity_type='person',
                                         primary=True)
                for leg in secondary:
                    bill.add_sponsorship(classification='cosponsor',
                                         name=leg, entity_type='person',
                                         primary=False)

                minutes_count = 2
                for mr in root.xpath('//table[4]/tr/td[3]/a'):
                    minutes = mr.xpath("string(@href)")
                    minutes_url = "http://www.leg.state.nv.us" + minutes
                    minutes_date_path = "string(//table[4]/tr[%s]/td[2])" % minutes_count
                    minutes_date = mr.xpath(minutes_date_path).split()
                    minutes_date = minutes_date[0] + minutes_date[1] + minutes_date[2] + " Minutes"
                    bill.add_document_link(note=minutes_date, url=minutes_url)
                    minutes_count += 1

                self.scrape_actions(root, bill, "lower")
                yield from self.scrape_votes(page, page_path, bill, insert, year)
                bill.add_source(page_path)
                yield bill

    def scrape_links(self, url):
        links = []

        page = self.get(url).text
        root = lxml.html.fromstring(page)
        path = '/html/body/div[@id="ScrollMe"]/table/tr[1]/td[1]/a'
        for mr in root.xpath(path):
            if '*' not in mr.text:
                web_end = mr.xpath('string(@href)')
                links.append(web_end)
        return links

    def scrape_sponsors(self, page):
        primary = []
        sponsors = []

        doc = lxml.html.fromstring(page)
        # These bold tagged elements should contain the primary sponsors.
        b_nodes = self.get_nodes(
            doc,
            '//div[@id="content"]/table/tr/td[contains(./b/text(), "By:")]/b/'
            'text()')

        for b in b_nodes:
            name = b.strip()
            # add these as sponsors (excluding junk text)
            if name not in ('By:', 'Bolded'):
                primary.append(name)

        nb_nodes = self.get_nodes(
            doc,
            '//div[@id="content"]/table/tr/td[contains(./b/text(), "By:")]/text()')

        # tail of last b has remaining sponsors
        for node in nb_nodes:
            if node == ' name indicates primary sponsorship)':
                continue
            names = re.sub('([\(\r\t\n\s])', '', node).split(',')

            for name in names:
                if name:
                    sponsors.append(name.strip())

        return primary, sponsors

    def scrape_actions(self, root, bill, actor):
        path = '/html/body/div[@id="content"]/table/tr/td/p[1]'
        for mr in root.xpath(path):
            date = mr.text_content().strip()
            date = date.split()[0] + " " + date.split()[1] + " " + date.split()[2]
            date = datetime.strptime(date, "%b %d, %Y")
            for el in mr.xpath('../../following-sibling::tr[1]/td/ul/li'):
                action = el.text_content().strip()

                # skip blank actions
                if not action:
                    continue

                action = " ".join(action.split())

                # catch chamber changes
                if action.startswith('In Assembly'):
                    actor = 'lower'
                elif action.startswith('In Senate'):
                    actor = 'upper'
                elif 'Governor' in action:
                    actor = 'executive'

                action_type = None
                for pattern, atype in self._classifiers:
                    if re.match(pattern, action):
                        action_type = atype
                        break

                if "Committee on" in action:
                    committees = re.findall("Committee on ([a-zA-Z, ]*)\.", action)
                    if len(committees) > 0:
                        related_entities = []
                        for committee in committees:
                            related_entities.append({
                                 "type": "committee",
                                 "name": committee
                                 })
                        bill.add_action(description=action,
                                        date=self._tz.localize(date),
                                        chamber=actor,
                                        classification=action_type,
                                        related_entities=related_entities
                                        )
                        continue

                bill.add_action(description=action,
                                date=self._tz.localize(date),
                                chamber=actor,
                                classification=action_type)

    def scrape_votes(self, bill_page, page_url, bill, insert, year):
        root = lxml.html.fromstring(bill_page)
        trs = root.xpath('/html/body/div/table[6]//tr')
        assert len(trs) >= 1, "Didn't find the Final Passage Votes' table"

        for tr in trs[1:]:
            links = tr.xpath('td/a[contains(text(), "Passage")]')
            if len(links) == 0:
                self.warning("Non-passage vote found for {}; ".format(bill.identifier) +
                             "probably a motion for the calendar. It will be skipped.")
            else:
                assert len(links) == 1, \
                    "Too many votes found for XPath query, on bill {}".format(bill.identifier)
                link = links[0]

            motion = link.text
            if 'Assembly' in motion:
                chamber = 'lower'
            else:
                chamber = 'upper'

            votes = {}
            tds = tr.xpath('td')
            for td in tds:
                if td.text:
                    text = td.text.strip()
                    date = re.match('... .*?, ....', text)
                    count = re.match('(?P<category>.*?) (?P<votes>[0-9]+)[,]?', text)
                    if date:
                        vote_date = datetime.strptime(text, '%b %d, %Y')
                    elif count:
                        votes[count.group('category')] = int(count.group('votes'))

            yes = votes['Yea']
            no = votes['Nay']
            excused = votes['Excused']
            not_voting = votes['Not Voting']
            absent = votes['Absent']
            other = excused + not_voting + absent
            passed = yes > no

            vote = VoteEvent(chamber=chamber, start_date=self._tz.localize(vote_date),
                             motion_text=motion, result='pass' if passed else 'fail',
                             classification='passage', bill=bill,
                             )
            vote.set_count('yes', yes)
            vote.set_count('no', no)
            vote.set_count('other', other)
            vote.set_count('not voting', not_voting)
            vote.set_count('absent', absent)
            # try to get vote details
            try:
                vote_url = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (
                    insert, link.get('href'))
                vote.pupa_id = vote_url
                vote.add_source(vote_url)

                if vote_url in self._seen_votes:
                    self.warning('%s is included twice, skipping second', vote_url)
                    continue
                else:
                    self._seen_votes.add(vote_url)

                page = self.get(vote_url).text
                page = page.replace(u"\xa0", " ")
                root = lxml.html.fromstring(page)

                for el in root.xpath('//table[2]/tr'):
                    tds = el.xpath('td')
                    name = tds[1].text_content().strip()
                    vote_result = tds[2].text_content().strip()

                    if vote_result == 'Yea':
                        vote.yes(name)
                    elif vote_result == 'Nay':
                        vote.no(name)
                    else:
                        vote.vote('other', name)
                vote.add_source(page_url)
            except scrapelib.HTTPError:
                self.warning("failed to fetch vote page, adding vote without details")

            yield vote
